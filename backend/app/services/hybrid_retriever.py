import time
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session
from app.services.embedding import embedding_service
from app.services.vector_store import VectorStoreService
from app.core.config import settings

logger = logging.getLogger("smartdocs.retriever")

class HybridRetriever:
    """
    Advanced RAG Retrieval Engine implementing:
    1. Dense Semantic Vector Search (pgvector cosine similarity)
    2. Sparse Lexical Search (PostgreSQL tsvector / keyword matching)
    3. Reciprocal Rank Fusion (RRF) to merge heterogeneous score distributions
    4. Maximal Marginal Relevance (MMR) for context diversity and redundancy elimination
    5. Similarity threshold gating to prevent feeding hallucination-inducing noise to the LLM
    """

    def __init__(self, db: Session):
        self.db = db

    def reciprocal_rank_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        k: int = 60,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Merges ranked results from Dense Vector search and Sparse Lexical search
        using Reciprocal Rank Fusion (RRF):
            Score(d) = sum(1 / (k + rank_i(d)))
        """
        fused_scores = {}
        chunk_map = {}

        # 1. Rank vector results
        for rank, chunk in enumerate(vector_results):
            cid = chunk["id"]
            chunk_map[cid] = chunk
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # 2. Rank keyword results
        for rank, chunk in enumerate(keyword_results):
            cid = chunk["id"]
            if cid not in chunk_map:
                chunk_map[cid] = chunk
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # 3. Sort by fused score
        sorted_cids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)

        final_chunks = []
        for cid in sorted_cids[:top_k]:
            chunk_copy = dict(chunk_map[cid])
            chunk_copy["rrf_score"] = round(fused_scores[cid], 5)
            final_chunks.append(chunk_copy)

        return final_chunks

    def maximal_marginal_relevance(
        self,
        query_vector: List[float],
        candidate_chunks: List[Dict[str, Any]],
        lambda_mult: float = 0.7,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Selects top_k diverse chunks using Maximal Marginal Relevance (MMR):
            MMR = argmax_{d in C \\ S} [ lambda * Sim(d, Q) - (1 - lambda) * max_{s in S} Sim(d, s) ]
        lambda_mult: 1.0 = pure relevance, 0.0 = maximal diversity, 0.7 = standard optimal balance
        """
        if not candidate_chunks:
            return []

        if len(candidate_chunks) <= top_k:
            return candidate_chunks

        # Collect or generate vector embeddings for candidates
        cand_vectors = []
        for c in candidate_chunks:
            if "_vector" in c and c["_vector"] is not None:
                cand_vectors.append(c["_vector"])
            else:
                # Compute embedding on demand if missing
                cand_vectors.append(np.array(embedding_service.get_embedding(c["content"]), dtype=np.float32))

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)

        # Precompute query similarities
        query_sims = []
        for v in cand_vectors:
            v_norm = np.linalg.norm(v)
            sim = np.dot(q_vec, v) / (q_norm * v_norm) if (q_norm > 0 and v_norm > 0) else 0.0
            query_sims.append(float(sim))

        selected_indices = []
        candidate_indices = list(range(len(candidate_chunks)))

        # First selection is the highest similarity chunk
        best_first = int(np.argmax(query_sims))
        selected_indices.append(best_first)
        candidate_indices.remove(best_first)

        while len(selected_indices) < top_k and candidate_indices:
            best_score = -float("inf")
            best_idx = None

            for idx in candidate_indices:
                sim_to_query = query_sims[idx]

                # Max similarity to already selected chunks
                max_sim_to_selected = max(
                    (np.dot(cand_vectors[idx], cand_vectors[s_idx]) /
                     (np.linalg.norm(cand_vectors[idx]) * np.linalg.norm(cand_vectors[s_idx]) + 1e-9))
                    for s_idx in selected_indices
                )

                mmr_score = lambda_mult * sim_to_query - (1.0 - lambda_mult) * max_sim_to_selected

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected_indices.append(best_idx)
                candidate_indices.remove(best_idx)
            else:
                break

        results = []
        for idx in selected_indices:
            chunk = dict(candidate_chunks[idx])
            chunk.pop("_vector", None)
            chunk["mmr_selected"] = True
            results.append(chunk)

        return results

    def retrieve(
        self,
        query: str,
        strategy: str = None,
        top_k: int = None,
        similarity_threshold: float = None,
        mmr_lambda: float = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified retrieval function that handles tuning parameters dynamically.
        Returns:
            - chunks: List of retrieved & ranked chunks
            - metadata: Diagnostics (latency, candidate count, strategy used)
        """
        strategy = strategy or settings.RETRIEVAL_STRATEGY
        top_k = top_k or settings.TOP_K
        similarity_threshold = similarity_threshold if similarity_threshold is not None else settings.SIMILARITY_THRESHOLD
        mmr_lambda = mmr_lambda if mmr_lambda is not None else settings.MMR_LAMBDA

        # If running in offline embedding mode (no real key), adapt threshold
        has_real_key = bool(
            (settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_") and not settings.GEMINI_API_KEY.startswith("mock")) or
            (settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("your_") and not settings.OPENAI_API_KEY.startswith("mock"))
        )
        if not has_real_key and similarity_threshold > 0.20:
            similarity_threshold = 0.10

        start_time = time.time()
        
        # 1. Generate query embedding
        query_vector = embedding_service.get_embedding(query)
        embedding_time = time.time() - start_time

        retrieval_start = time.time()
        chunks = []

        if strategy == "vector":
            # Pure dense vector search
            raw_chunks = VectorStoreService.search_vector(
                self.db, query_vector, top_k=top_k * 2, document_id=document_id
            )
            # Apply similarity threshold cutoff
            chunks = [c for c in raw_chunks if c.get("similarity", 0.0) >= similarity_threshold][:top_k]

        elif strategy == "keyword":
            # Pure lexical keyword search
            raw_chunks = VectorStoreService.search_keyword(
                self.db, query, top_k=top_k, document_id=document_id
            )
            chunks = raw_chunks

        elif strategy == "hybrid":
            # Hybrid: Dense + Sparse with RRF
            cand_limit = max(10, top_k * 3)
            vec_candidates = VectorStoreService.search_vector(
                self.db, query_vector, top_k=cand_limit, document_id=document_id
            )
            key_candidates = VectorStoreService.search_keyword(
                self.db, query, top_k=cand_limit, document_id=document_id
            )

            # RRF Fusion
            fused = self.reciprocal_rank_fusion(
                vec_candidates, key_candidates, k=60, top_k=top_k * 2
            )
            # Filter by threshold if similarity exists
            chunks = [
                c for c in fused
                if "similarity" not in c or c["similarity"] >= similarity_threshold
            ][:top_k]
            if not chunks and fused:
                chunks = fused[:top_k]

        elif strategy == "mmr":
            # Dense search candidate pool followed by MMR diversity re-ranking
            cand_limit = max(15, top_k * 4)
            candidates = VectorStoreService.search_vector(
                self.db, query_vector, top_k=cand_limit, document_id=document_id
            )
            # Filter low similarity before MMR
            filtered = [c for c in candidates if c.get("similarity", 0.0) >= similarity_threshold]
            chunks = self.maximal_marginal_relevance(
                query_vector, filtered, lambda_mult=mmr_lambda, top_k=top_k
            )

        else:
            # Default to vector
            raw_chunks = VectorStoreService.search_vector(
                self.db, query_vector, top_k=top_k, document_id=document_id
            )
            chunks = [c for c in raw_chunks if c.get("similarity", 0.0) >= similarity_threshold]

        total_latency_ms = round((time.time() - start_time) * 1000, 2)

        # Clean any remaining numpy arrays
        for c in chunks:
            c.pop("_vector", None)

        metadata = {
            "strategy": strategy,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "mmr_lambda": mmr_lambda if strategy == "mmr" else None,
            "total_latency_ms": total_latency_ms,
            "embedding_latency_ms": round(embedding_time * 1000, 2),
            "chunks_retrieved": len(chunks)
        }

        return {
            "chunks": chunks,
            "metadata": metadata
        }

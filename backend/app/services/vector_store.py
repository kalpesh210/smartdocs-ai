import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.models import DocumentChunk, Document
from app.db.session import DB_DIALECT
from app.core.config import settings

logger = logging.getLogger("smartdocs.vector_store")

class VectorStoreService:
    """
    High-performance vector store abstraction supporting:
    - PostgreSQL + pgvector (HNSW / IVFFlat cosine search)
    - In-memory / SQLite fallback with NumPy vectorized cosine similarity
    """

    @staticmethod
    def cosine_similarity_np(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Calculates cosine similarity between two 1D vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    @classmethod
    def search_vector(
        cls,
        db: Session,
        query_vector: List[float],
        top_k: int = 10,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes dense vector similarity search.
        Returns list of chunks with calculated similarity score [0.0 to 1.0].
        """
        results = []

        if DB_DIALECT == "postgresql":
            try:
                # pgvector cosine distance operator is <=>
                # Cosine similarity = 1 - cosine_distance
                vector_str = f"[{','.join(str(x) for x in query_vector)}]"
                doc_filter = "AND dc.document_id = :doc_id" if document_id else ""
                
                query_sql = f"""
                    SELECT 
                        dc.id,
                        dc.document_id,
                        d.filename as document_filename,
                        dc.chunk_index,
                        dc.content,
                        dc.page_number,
                        dc.token_count,
                        dc.metadata_json,
                        1 - (dc.embedding <=> :query_vec::vector) as similarity
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE dc.embedding IS NOT NULL {doc_filter}
                    ORDER BY dc.embedding <=> :query_vec::vector ASC
                    LIMIT :top_k;
                """
                params = {"query_vec": vector_str, "top_k": top_k}
                if document_id:
                    params["doc_id"] = document_id

                rows = db.execute(text(query_sql), params).fetchall()
                for row in rows:
                    results.append({
                        "id": row.id,
                        "document_id": row.document_id,
                        "document_filename": row.document_filename,
                        "chunk_index": row.chunk_index,
                        "content": row.content,
                        "page_number": row.page_number,
                        "token_count": row.token_count,
                        "metadata": row.metadata_json or {},
                        "similarity": max(0.0, min(1.0, float(row.similarity)))
                    })
                return results
            except Exception as e:
                logger.warning(f"PostgreSQL pgvector query failed ({e}), falling back to Python-based similarity.")

        # Fallback / SQLite in-memory vectorized search
        query = db.query(DocumentChunk, Document.filename).join(Document, Document.id == DocumentChunk.document_id)
        if document_id:
            query = query.filter(DocumentChunk.document_id == document_id)
        chunks = query.all()

        if not chunks:
            return []

        q_vec = np.array(query_vector, dtype=np.float32)
        scored_chunks = []

        for chunk, filename in chunks:
            if chunk.embedding is None:
                continue
            
            # Handle SQLite stored JSON embedding or list
            c_vec_raw = chunk.embedding
            if isinstance(c_vec_raw, str):
                try:
                    c_vec_raw = json.loads(c_vec_raw)
                except Exception:
                    continue
            
            c_vec = np.array(c_vec_raw, dtype=np.float32)
            if c_vec.shape[0] != q_vec.shape[0]:
                continue

            sim = cls.cosine_similarity_np(q_vec, c_vec)
            scored_chunks.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "document_filename": filename,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata_json or {},
                "similarity": max(0.0, min(1.0, float(sim))),
                "_vector": c_vec
            })

        # Sort descending by similarity
        scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_chunks[:top_k]

    @classmethod
    def search_keyword(
        cls,
        db: Session,
        query_text: str,
        top_k: int = 10,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes lexical/keyword search (PostgreSQL tsvector or SQLite token overlap).
        """
        results = []
        tokens = [t.lower() for t in query_text.split() if len(t) > 2]

        if not tokens:
            return []

        if DB_DIALECT == "postgresql":
            try:
                # PostgreSQL Full-Text Search with ranking
                clean_query = " | ".join(tokens)
                doc_filter = "AND dc.document_id = :doc_id" if document_id else ""
                sql = f"""
                    SELECT 
                        dc.id,
                        dc.document_id,
                        d.filename as document_filename,
                        dc.chunk_index,
                        dc.content,
                        dc.page_number,
                        dc.token_count,
                        dc.metadata_json,
                        ts_rank_cd(to_tsvector('english', dc.content), to_tsquery('english', :query)) as rank
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE to_tsvector('english', dc.content) @@ to_tsquery('english', :query) {doc_filter}
                    ORDER BY rank DESC
                    LIMIT :top_k;
                """
                params = {"query": clean_query, "top_k": top_k}
                if document_id:
                    params["doc_id"] = document_id
                rows = db.execute(text(sql), params).fetchall()
                for row in rows:
                    results.append({
                        "id": row.id,
                        "document_id": row.document_id,
                        "document_filename": row.document_filename,
                        "chunk_index": row.chunk_index,
                        "content": row.content,
                        "page_number": row.page_number,
                        "token_count": row.token_count,
                        "metadata": row.metadata_json or {},
                        "keyword_score": float(row.rank)
                    })
                return results
            except Exception as e:
                logger.warning(f"PostgreSQL tsvector query failed: {e}. Falling back to Python keyword matching.")

        # Fallback / SQLite keyword scoring (term-frequency & coverage)
        query = db.query(DocumentChunk, Document.filename).join(Document, Document.id == DocumentChunk.document_id)
        if document_id:
            query = query.filter(DocumentChunk.document_id == document_id)
        chunks = query.all()

        scored_chunks = []
        token_set = set(tokens)

        for chunk, filename in chunks:
            content_lower = chunk.content.lower()
            match_count = 0
            for t in token_set:
                if t in content_lower:
                    match_count += content_lower.count(t)

            if match_count > 0:
                # Score based on frequency normalized by length
                score = match_count / (math_len := max(1, len(chunk.content) // 100))
                scored_chunks.append({
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_filename": filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata_json or {},
                    "keyword_score": float(score)
                })

        scored_chunks.sort(key=lambda x: x["keyword_score"], reverse=True)
        return scored_chunks[:top_k]

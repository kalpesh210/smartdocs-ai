import re
import logging
from typing import List, Dict, Any
from app.services.embedding import embedding_service
import numpy as np

logger = logging.getLogger("smartdocs.evaluator")

class RAGEvaluator:
    """
    Implements the RAG Triad Evaluation Framework (inspired by RAGAS & TruLens):
    1. Context Relevance: Are the retrieved chunks relevant to the question without excessive noise?
    2. Faithfulness / Groundedness: Is the generated answer 100% supported by context (anti-hallucination check)?
    3. Answer Relevance: Does the generated answer directly address the user query?
    """

    @staticmethod
    def calculate_answer_relevance(question: str, answer: str) -> float:
        """
        Computes cosine similarity between question embedding and answer embedding.
        High score indicates answer is topically focused on the question.
        """
        if not question or not answer:
            return 0.0
        q_emb = np.array(embedding_service.get_embedding(question), dtype=np.float32)
        a_emb = np.array(embedding_service.get_embedding(answer[:500]), dtype=np.float32)

        norm_q = np.linalg.norm(q_emb)
        norm_a = np.linalg.norm(a_emb)
        if norm_q == 0 or norm_a == 0:
            return 0.0
        score = float(np.dot(q_emb, a_emb) / (norm_q * norm_a))
        return round(max(0.0, min(1.0, score)), 3)

    @staticmethod
    def calculate_context_relevance(question: str, retrieved_chunks: List[Dict[str, Any]]) -> float:
        """
        Evaluates the signal-to-noise ratio of the retrieved chunks relative to the question.
        """
        if not retrieved_chunks:
            return 0.0

        q_terms = set(re.findall(r"\w+", question.lower()))
        if not q_terms:
            return 0.0

        scores = []
        for chunk in retrieved_chunks:
            # If similarity is already computed, factor it in
            sim = chunk.get("similarity")
            if sim is not None:
                scores.append(sim)
            else:
                c_terms = set(re.findall(r"\w+", chunk.get("content", "").lower()))
                overlap = len(q_terms & c_terms) / len(q_terms)
                scores.append(overlap)

        avg_score = float(np.mean(scores)) if scores else 0.0
        return round(max(0.0, min(1.0, avg_score)), 3)

    @staticmethod
    def calculate_faithfulness(answer: str, retrieved_chunks: List[Dict[str, Any]]) -> float:
        """
        Estimates groundedness / faithfulness.
        Splits answer into propositional statements/sentences and checks what fraction
        have lexical or semantic backing in the retrieved context chunks.
        """
        if not retrieved_chunks or not answer:
            return 0.0

        sentences = [s.strip() for s in re.split(r"[.\n]", answer) if len(s.strip()) > 15]
        if not sentences:
            return 1.0

        full_context = " ".join([c.get("content", "").lower() for c in retrieved_chunks])

        supported_count = 0
        for sent in sentences:
            sent_words = set(re.findall(r"\w+", sent.lower()))
            # Remove very short stop words
            key_words = {w for w in sent_words if len(w) > 3}
            if not key_words:
                supported_count += 1
                continue

            matches = sum(1 for w in key_words if w in full_context)
            if (matches / len(key_words)) >= 0.5:
                supported_count += 1

        faithfulness = supported_count / len(sentences)
        return round(max(0.0, min(1.0, faithfulness)), 3)

    @classmethod
    def evaluate_triad(
        cls,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Runs the complete RAG Triad assessment."""
        c_rel = cls.calculate_context_relevance(question, retrieved_chunks)
        faith = cls.calculate_faithfulness(answer, retrieved_chunks)
        a_rel = cls.calculate_answer_relevance(question, answer)

        # Composite score
        ragas_score = round((c_rel * 0.35 + faith * 0.40 + a_rel * 0.25), 3)

        return {
            "context_relevance": c_rel,
            "faithfulness": faith,
            "answer_relevance": a_rel,
            "overall_ragas_score": ragas_score,
            "assessment": "Excellent" if ragas_score >= 0.8 else ("Moderate" if ragas_score >= 0.6 else "Needs Tuning")
        }

evaluator = RAGEvaluator()

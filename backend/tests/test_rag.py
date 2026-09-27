import pytest
from app.services.evaluator import RAGEvaluator

def test_rag_evaluator_metrics():
    question = "What is the chunk overlap used in SmartDocs?"
    answer = "SmartDocs AI utilizes a chunk overlap of 80 characters to preserve context across boundaries."
    retrieved_chunks = [
        {
            "id": "c1",
            "content": "SmartDocs AI utilizes a chunk overlap of 80 characters with recursive text splitting to preserve context across boundaries.",
            "similarity": 0.92
        }
    ]

    metrics = RAGEvaluator.evaluate_triad(question, answer, retrieved_chunks)

    assert "context_relevance" in metrics
    assert "faithfulness" in metrics
    assert "answer_relevance" in metrics
    assert "overall_ragas_score" in metrics
    assert metrics["faithfulness"] >= 0.8
    assert metrics["overall_ragas_score"] >= 0.7

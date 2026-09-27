import pytest
import numpy as np
from app.services.vector_store import VectorStoreService
from app.services.hybrid_retriever import HybridRetriever

def test_cosine_similarity():
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([1.0, 0.0, 0.0])
    v3 = np.array([0.0, 1.0, 0.0])

    sim_identical = VectorStoreService.cosine_similarity_np(v1, v2)
    sim_orthogonal = VectorStoreService.cosine_similarity_np(v1, v3)

    assert pytest.approx(sim_identical, 0.001) == 1.0
    assert pytest.approx(sim_orthogonal, 0.001) == 0.0

def test_reciprocal_rank_fusion():
    retriever = HybridRetriever(db=None)

    vec_results = [
        {"id": "doc1", "content": "RAG architecture", "similarity": 0.95},
        {"id": "doc2", "content": "Vector database pgvector", "similarity": 0.88},
        {"id": "doc3", "content": "FastAPI backend", "similarity": 0.75}
    ]

    key_results = [
        {"id": "doc2", "content": "Vector database pgvector", "keyword_score": 10.0},
        {"id": "doc4", "content": "Chunking strategies", "keyword_score": 8.0},
        {"id": "doc1", "content": "RAG architecture", "keyword_score": 5.0}
    ]

    fused = retriever.reciprocal_rank_fusion(vec_results, key_results, k=60, top_k=3)

    assert len(fused) == 3
    top_ids = [c["id"] for c in fused]
    assert "doc1" in top_ids
    assert "doc2" in top_ids
    assert "rrf_score" in fused[0]

def test_mmr_selection():
    retriever = HybridRetriever(db=None)
    # Query spans Topic 1 (x-axis) and Topic 2 (y-axis)
    q_vec = [0.8, 0.6, 0.0]

    # c1 covers Topic 1 well
    # c2 is a duplicate of Topic 1 (high redundancy with c1)
    # c3 covers Topic 2 (diverse, brings orthogonal information to c1)
    candidates = [
        {"id": "c1", "content": "Topic 1 Intro", "_vector": np.array([1.0, 0.0, 0.0])},
        {"id": "c2", "content": "Topic 1 Duplicate", "_vector": np.array([1.0, 0.0, 0.0])},
        {"id": "c3", "content": "Topic 2 Details", "_vector": np.array([0.0, 1.0, 0.0])}
    ]

    # With lambda=0.7 (standard balance), c3 should be selected over redundant c2
    selected = retriever.maximal_marginal_relevance(q_vec, candidates, lambda_mult=0.7, top_k=2)

    assert len(selected) == 2
    selected_ids = [c["id"] for c in selected]
    assert "c1" in selected_ids
    assert "c3" in selected_ids  # MMR successfully penalized redundant c2!

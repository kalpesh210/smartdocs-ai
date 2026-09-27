import pytest
from app.services.chunker import RecursiveChunker

def test_recursive_chunker_basic():
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "Artificial Intelligence (AI) is transforming document search. "
        "Retrieval-Augmented Generation (RAG) combines search retrieval with generative LLMs. "
        "By breaking large PDFs into semantic chunks, vector search retrieves only the relevant passages. "
        "This prevents context saturation and improves factual accuracy."
    )
    pages = [{"page_number": 1, "text": sample_text}]
    chunks = chunker.chunk_document_pages("doc-123", pages)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["document_id"] == "doc-123"
        assert chunk["page_number"] == 1
        assert len(chunk["content"]) > 0
        assert chunk["token_count"] > 0
        assert "metadata" in chunk

def test_recursive_chunker_empty():
    chunker = RecursiveChunker()
    chunks = chunker.chunk_document_pages("doc-empty", [{"page_number": 1, "text": ""}])
    assert len(chunks) == 0

def test_recursive_chunker_overlap():
    chunker = RecursiveChunker(chunk_size=80, chunk_overlap=30)
    text = "Section A covers data pipelines. Section B covers vector databases. Section C covers evaluation metrics."
    pages = [{"page_number": 1, "text": text}]
    chunks = chunker.chunk_document_pages("doc-overlap", pages)
    assert len(chunks) >= 2

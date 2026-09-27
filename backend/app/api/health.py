from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, DB_DIALECT
from app.db.models import Document, DocumentChunk
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check(db: Session = Depends(get_db)):
    """
    Returns system status, active database dialect, vector store status, and document statistics.
    """
    doc_count = db.query(Document).count()
    chunk_count = db.query(DocumentChunk).count()

    vector_extension_active = False
    if DB_DIALECT == "postgresql":
        try:
            res = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';")).fetchone()
            vector_extension_active = bool(res)
        except Exception:
            vector_extension_active = False

    gemini_active = bool(settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_") and not settings.GEMINI_API_KEY.startswith("mock"))
    openai_active = bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("your_") and not settings.OPENAI_API_KEY.startswith("mock"))

    active_provider = "gemini" if gemini_active else ("openai" if openai_active else "offline_extractive")

    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "database_dialect": DB_DIALECT,
        "pgvector_active": vector_extension_active if DB_DIALECT == "postgresql" else False,
        "ai_provider": active_provider,
        "gemini_configured": gemini_active,
        "openai_configured": openai_active,
        "indexed_documents": doc_count,
        "indexed_chunks": chunk_count,
        "default_embedding_model": settings.EMBEDDING_MODEL,
        "default_embedding_dimension": settings.EMBEDDING_DIMENSION,
        "default_llm_model": settings.LLM_MODEL
    }

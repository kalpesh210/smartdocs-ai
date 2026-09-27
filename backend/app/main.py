from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import init_db
from app.api import documents, chat, retrieval, evaluation, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("smartdocs.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables
    logger.info("Initializing SmartDocs AI Database and Vector Extensions...")
    init_db()
    logger.info("SmartDocs AI backend initialized successfully.")
    yield
    # Shutdown
    logger.info("Shutting down SmartDocs AI backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="End-to-End Generative AI RAG Chatbot with FastAPI, PostgreSQL/pgvector, Hybrid Search & MMR Retrieval Tuning.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
api_v1 = settings.API_V1_STR
app.include_router(health.router, prefix=api_v1)
app.include_router(documents.router, prefix=api_v1)
app.include_router(chat.router, prefix=api_v1)
app.include_router(retrieval.router, prefix=api_v1)
app.include_router(evaluation.router, prefix=api_v1)

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "api_docs": "/docs",
        "api_version": "v1"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

import os
from typing import Optional, List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Preload .env file into environment
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartDocs AI - RAG Chatbot"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "smartdocs_db")
    
    # If explicitly set, overrides individual postgres settings
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", None)
    
    # AI Provider Settings (Google AI Studio / Gemini + OpenAI Fallback)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.8-flash")
    
    # RAG Default Hyperparameters (Interview-tuned defaults)
    CHUNK_SIZE: int = 500  # Target chunk size in characters/tokens
    CHUNK_OVERLAP: int = 80  # Overlap between consecutive chunks
    TOP_K: int = 4  # Default number of chunks to feed to LLM
    RETRIEVAL_STRATEGY: str = "hybrid"  # "vector", "keyword", "hybrid", "mmr"
    SIMILARITY_THRESHOLD: float = 0.40  # Minimum cosine similarity cutoff
    MMR_LAMBDA: float = 0.70  # Relevance vs Diversity trade-off
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]

    # Uploads
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

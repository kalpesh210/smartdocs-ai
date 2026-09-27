import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.models import Base

logger = logging.getLogger("smartdocs.db")

def get_database_url() -> str:
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    return (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

def init_engine():
    db_url = get_database_url()
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            # Try enabling pgvector extension
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("Connected to PostgreSQL with pgvector extension enabled.")
            except Exception as e:
                logger.warning(f"Connected to PostgreSQL, but could not enable 'vector' extension: {e}")
        return engine, "postgresql"
    except Exception as e:
        logger.warning(
            f"Could not connect to PostgreSQL at {db_url} ({e}). "
            "Falling back to local SQLite database (smartdocs.db) for development."
        )
        sqlite_url = "sqlite:///./smartdocs.db"
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        return engine, "sqlite"

engine, DB_DIALECT = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database tables initialized on dialect: {DB_DIALECT}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

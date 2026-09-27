import uuid
import datetime
import json
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.types import TypeDecorator
from app.core.config import settings

Base = declarative_base()

class VectorColumn(TypeDecorator):
    """
    Custom SQLAlchemy TypeDecorator that supports pgvector Vector(dim) when on PostgreSQL,
    and falls back to JSON / text storage when on SQLite for seamless local prototyping.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 1536, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                return dialect.type_descriptor(Text())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        # In SQLite/other dialects, serialize list of floats to JSON string
        if isinstance(value, (list, tuple)):
            return json.dumps([float(x) for x in value])
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return []
        return value


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "error_message": self.error_message,
            "chunk_count": self.chunk_count,
            "page_count": self.page_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, default=1)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    
    # Configurable dimension: 768 for Google text-embedding-004, 1536 for OpenAI
    embedding = Column(VectorColumn(dim=settings.EMBEDDING_DIMENSION), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def to_dict(self, include_embedding=False):
        data = {
            "id": self.id,
            "document_id": self.document_id,
            "document_filename": self.document.filename if self.document else None,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "page_number": self.page_number,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "token_count": self.token_count,
            "metadata": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_embedding and self.embedding is not None:
            data["embedding"] = list(self.embedding) if hasattr(self.embedding, "__iter__") else self.embedding
        return data


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    def to_dict(self, include_messages=False):
        data = {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": len(self.messages) if self.messages else 0
        }
        if include_messages and self.messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # List of retrieved chunk excerpts, similarity scores, doc names
    retrieval_metadata = Column(JSON, nullable=True)  # strategy used, latency, query expansion
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "sources": self.sources or [],
            "retrieval_metadata": self.retrieval_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

import uuid
import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Conversation, Message
from app.services.rag_chain import RAGChainService

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger("smartdocs.api.chat")

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    retrieval_strategy: Optional[str] = "hybrid"  # vector, keyword, hybrid, mmr
    top_k: Optional[int] = 4
    similarity_threshold: Optional[float] = 0.40
    mmr_lambda: Optional[float] = 0.70
    document_id: Optional[str] = None

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"

@router.get("/conversations")
def get_conversations(db: Session = Depends(get_db)):
    """Lists all user conversations with message count."""
    convs = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    return [c.to_dict() for c in convs]

@router.post("/conversations")
def create_conversation(req: CreateConversationRequest, db: Session = Depends(get_db)):
    """Creates a new conversation session."""
    conv = Conversation(id=str(uuid.uuid4()), title=req.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv.to_dict()

@router.get("/conversations/{conversation_id}")
def get_conversation_history(conversation_id: str, db: Session = Depends(get_db)):
    """Retrieves full conversation message history."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv.to_dict(include_messages=True)

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Deletes conversation and associated messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted"}

@router.post("/message")
def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Synchronous Chat endpoint.
    Performs context-aware RAG, logs messages to conversation history, and returns answer + citations.
    """
    # 1. Resolve or create conversation
    conv_id = req.conversation_id
    if not conv_id:
        # Create conversation automatically titled with first query
        conv_title = req.message[:40] + ("..." if len(req.message) > 40 else "")
        conv = Conversation(id=str(uuid.uuid4()), title=conv_title)
        db.add(conv)
        db.commit()
        conv_id = conv.id
    else:
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if not conv:
            conv = Conversation(id=conv_id, title=req.message[:40])
            db.add(conv)
            db.commit()

    # 2. Fetch recent conversation history
    recent_msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at.asc()).all()
    history = [{"role": m.role, "content": m.content} for m in recent_msgs]

    # 3. Save User Message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=req.message
    )
    db.add(user_msg)
    db.commit()

    # 4. Generate RAG Response
    rag = RAGChainService(db)
    rag_result = rag.generate_response(
        question=req.message,
        history=history,
        retrieval_strategy=req.retrieval_strategy,
        top_k=req.top_k,
        similarity_threshold=req.similarity_threshold,
        mmr_lambda=req.mmr_lambda,
        document_id=req.document_id
    )

    # 5. Save Assistant Message
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="assistant",
        content=rag_result["answer"],
        sources=rag_result["sources"],
        retrieval_metadata=rag_result["retrieval_metadata"]
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "conversation_id": conv_id,
        "message": assistant_msg.to_dict(),
        "answer": rag_result["answer"],
        "sources": rag_result["sources"],
        "retrieval_metadata": rag_result["retrieval_metadata"]
    }

@router.post("/stream")
async def send_message_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Server-Sent Events (SSE) Streaming Chat endpoint.
    Streams token deltas in real-time, followed by source citations.
    """
    conv_id = req.conversation_id
    if not conv_id:
        conv = Conversation(id=str(uuid.uuid4()), title=req.message[:40])
        db.add(conv)
        db.commit()
        conv_id = conv.id

    recent_msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at.asc()).all()
    history = [{"role": m.role, "content": m.content} for m in recent_msgs]

    # Save User message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=req.message
    )
    db.add(user_msg)
    db.commit()

    rag = RAGChainService(db)

    async def event_generator():
        # Stream events from RAG chain
        async for chunk in rag.generate_response_stream(
            question=req.message,
            history=history,
            retrieval_strategy=req.retrieval_strategy,
            top_k=req.top_k,
            similarity_threshold=req.similarity_threshold,
            mmr_lambda=req.mmr_lambda,
            document_id=req.document_id
        ):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")

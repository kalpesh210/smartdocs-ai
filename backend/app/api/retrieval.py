import time
import logging
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.hybrid_retriever import HybridRetriever

router = APIRouter(prefix="/retrieval", tags=["Retrieval Tuning"])
logger = logging.getLogger("smartdocs.api.retrieval")

class RetrievalTestRequest(BaseModel):
    query: str
    strategy: Optional[str] = "hybrid"  # vector, keyword, hybrid, mmr, compare_all
    top_k: Optional[int] = 4
    similarity_threshold: Optional[float] = 0.40
    mmr_lambda: Optional[float] = 0.70
    document_id: Optional[str] = None

@router.post("/test")
def test_retrieval(req: RetrievalTestRequest, db: Session = Depends(get_db)):
    """
    Dedicated endpoint for testing and tuning retrieval strategies.
    If strategy == 'compare_all', executes vector, keyword, hybrid, and mmr
    in parallel and returns a side-by-side diagnostic comparison!
    """
    retriever = HybridRetriever(db)

    if req.strategy == "compare_all":
        # Compare all strategies side by side
        strategies = ["vector", "keyword", "hybrid", "mmr"]
        comparisons = {}

        for strat in strategies:
            res = retriever.retrieve(
                query=req.query,
                strategy=strat,
                top_k=req.top_k,
                similarity_threshold=req.similarity_threshold,
                mmr_lambda=req.mmr_lambda,
                document_id=req.document_id
            )
            comparisons[strat] = res

        return {
            "query": req.query,
            "mode": "comparison",
            "results": comparisons
        }

    # Single strategy execution
    result = retriever.retrieve(
        query=req.query,
        strategy=req.strategy,
        top_k=req.top_k,
        similarity_threshold=req.similarity_threshold,
        mmr_lambda=req.mmr_lambda,
        document_id=req.document_id
    )

    return {
        "query": req.query,
        "strategy": req.strategy,
        "results": result
    }

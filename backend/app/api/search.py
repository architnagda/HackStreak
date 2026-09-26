import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import SearchQueryRequest, SearchResultItem
from app.api.deps import get_current_user
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=List[SearchResultItem])
def search_documents(
    payload: SearchQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Direct semantic retrieval endpoint across all (or specific) user documents.
    Returns ranked chunks with page provenance, section, text snippet, and similarity score.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )

    doc_filter = [payload.document_id] if payload.document_id else None
    results = embedding_service.query_similar(
        user_id=current_user.id,
        query=query,
        top_k=payload.top_k,
        document_ids=doc_filter
    )

    return results

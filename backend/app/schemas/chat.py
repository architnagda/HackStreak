from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SourceResponse(BaseModel):
    id: Optional[int] = None
    document_id: Optional[int] = None
    document_name: str
    page_number: int
    section: Optional[str] = None
    evidence_snippet: str
    relevance_score: Optional[float] = None

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime
    sources: List[SourceResponse] = []

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

class ConversationListItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True

class ChatQueryRequest(BaseModel):
    conversation_id: Optional[int] = None
    question: str
    document_ids: Optional[List[int]] = None

class ChatQueryResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: List[SourceResponse] = []
    has_insufficient_evidence: bool = False
    has_conflicting_info: bool = False

class SearchQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    document_id: Optional[int] = None

class SearchResultItem(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    section: Optional[str] = None
    content: str
    relevance_score: float

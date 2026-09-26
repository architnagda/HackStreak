import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.conversation import Conversation, Message, Source
from app.schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    ConversationListItem,
    ConversationResponse,
    SourceResponse,
    MessageResponse
)
from app.api.deps import get_current_user
from app.services.embedding_service import embedding_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

@router.post("/chat", response_model=ChatQueryResponse)
def chat_with_documents(
    payload: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Core conversational RAG endpoint:
    1. Validates document ownership if document_ids are provided.
    2. Loads or initializes conversation session.
    3. Retrieves top semantic context chunks from ChromaDB for the user (with optional document filtering).
    4. Runs grounded reasoning with Google Gemini (with citation tracking and selected-mode awareness).
    5. Records conversation turns and source citations in MySQL.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    # 1. Validate Document Ownership (Security Enforcement)
    selected_doc_ids: Optional[List[int]] = None
    if payload.document_ids is not None and len(payload.document_ids) > 0:
        unique_ids = list({int(d) for d in payload.document_ids})
        owned_rows = db.query(Document.id).filter(
            Document.id.in_(unique_ids),
            Document.user_id == current_user.id
        ).all()
        owned_ids = {r[0] for r in owned_rows}

        if len(owned_ids) != len(unique_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: One or more selected documents do not exist or do not belong to you."
            )
        selected_doc_ids = unique_ids

    # Temporary Debug Logging for Traceability
    print("========================================")
    print("QUESTION:", question)
    print("SELECTED DOCUMENT IDS:", selected_doc_ids)
    print("RETRIEVAL FILTER:", f"document_ids={selected_doc_ids}")
    print("========================================")

    # 2. Manage Conversation Session
    conversation = None
    if payload.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == payload.conversation_id,
            Conversation.user_id == current_user.id
        ).first()

    if not conversation:
        title_snippet = question[:40] + ("..." if len(question) > 40 else "")
        conversation = Conversation(
            user_id=current_user.id,
            title=title_snippet
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 3. Extract Conversation History
    history_messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at.asc()).all()

    formatted_history = [
        {"role": m.role, "content": m.content}
        for m in history_messages
    ]

    # 4. Formulate Search Query for Retrieval
    search_query = question
    q_lower = question.lower()
    has_explicit_doc = any(ext in q_lower for ext in [".pdf", ".docx", ".png", ".jpg", ".txt"])

    if not has_explicit_doc and formatted_history and len(formatted_history) >= 2:
        last_user_query = None
        for m in reversed(formatted_history):
            if m["role"] == "user":
                last_user_query = m["content"]
                break

        pronoun_cues = [" it ", " its ", " this ", " that ", " these ", " those ", " they ", " them ", " the document ", " the file ", " same document "]
        phrase_cues = ["what about", "how about", "when was it", "why did it", "tell me more", "and what", "and how"]
        
        is_contextual_followup = (
            any(cue in f" {q_lower} " for cue in pronoun_cues) or 
            any(q_lower.startswith(p) for p in phrase_cues) or
            len(question.split()) <= 3
        )
        
        if is_contextual_followup and last_user_query and last_user_query != question:
            search_query = f"{last_user_query} {question}"

    # 5. Retrieve Top Relevant Document Chunks (Filtered or All Documents)
    retrieved_chunks = embedding_service.query_similar(
        user_id=current_user.id,
        query=search_query,
        top_k=5,
        document_ids=selected_doc_ids
    )

    print(f"RETRIEVED CHUNKS ({len(retrieved_chunks)}):")
    for rc in retrieved_chunks:
        print(f"  - doc_id={rc.get('document_id')} | filename={rc.get('filename')} | page={rc.get('page_number')} | score={rc.get('relevance_score')}")

    # 6. Generate Grounded Gemini / Extractive Response
    rag_result = rag_service.generate_response(
        query=question,
        retrieved_chunks=retrieved_chunks,
        conversation_history=formatted_history,
        is_selected_mode=bool(selected_doc_ids),
        search_query=search_query
    )

    answer_text = rag_result["answer"]
    is_insufficient = rag_result.get("insufficient_evidence", False)
    is_conflict = rag_result.get("conflicts_detected", False)
    sources_data = rag_result.get("sources", [])

    print(f"RAG RESULT SOURCES ({len(sources_data)}):")
    for s in sources_data:
        print(f"  - doc_id={s.get('document_id')} | filename={s.get('document_name')} | page={s.get('page_number')}")


    # 5. Persist User Message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=question
    )
    db.add(user_msg)
    db.flush()

    # 6. Persist Assistant Message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text
    )
    db.add(assistant_msg)
    db.flush()

    # 7. Persist Source Citations
    saved_sources = []
    for s in sources_data:
        src_obj = Source(
            message_id=assistant_msg.id,
            document_id=s.get("document_id"),
            document_name=s.get("document_name", "Document"),
            page_number=s.get("page_number", 1),
            section=s.get("section"),
            evidence_snippet=s.get("evidence_snippet", ""),
            relevance_score=s.get("relevance_score")
        )
        db.add(src_obj)
        saved_sources.append(src_obj)

    db.commit()
    db.refresh(assistant_msg)

    # Format return response
    return ChatQueryResponse(
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        answer=answer_text,
        sources=[
            SourceResponse(
                id=s.id if hasattr(s, "id") else None,
                document_id=s.document_id if hasattr(s, "document_id") else s.get("document_id"),
                document_name=s.document_name if hasattr(s, "document_name") else s.get("document_name"),
                page_number=s.page_number if hasattr(s, "page_number") else s.get("page_number", 1),
                section=s.section if hasattr(s, "section") else s.get("section"),
                evidence_snippet=s.evidence_snippet if hasattr(s, "evidence_snippet") else s.get("evidence_snippet", ""),
                relevance_score=s.relevance_score if hasattr(s, "relevance_score") else s.get("relevance_score")
            )
            for s in saved_sources
        ],
        has_insufficient_evidence=is_insufficient,
        has_conflicting_info=is_conflict
    )


@router.get("/conversations", response_model=List[ConversationListItem])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all conversation sessions for the current user.
    """
    convs = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()

    items = []
    for c in convs:
        msg_count = len(c.messages)
        items.append(
            ConversationListItem(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=msg_count
            )
        )
    return items


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation_history(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves full message history and attached citations for a given conversation.
    """
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    return conv


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a conversation session and all its message history.
    """
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully."}

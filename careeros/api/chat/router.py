"""Chat API router — context-aware career assistant chat."""
import uuid
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from careeros.api.chat.schemas import (
    CreateChatSessionRequest, SendMessageRequest,
    MessageResponse, ChatSessionResponse,
)
from careeros.database.models.chat_session import ChatSession, ChatMessage
from careeros.dependencies import CurrentUser, DB
from careeros.llm.client import get_llm_client
from careeros.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(request: CreateChatSessionRequest, current_user: CurrentUser, db: DB):
    session = ChatSession(
        user_id=current_user.id,
        context_type=request.context_type,
        generation_session_id=uuid.UUID(request.generation_session_id) if request.generation_session_id else None,
    )
    db.add(session)
    await db.flush()
    return ChatSessionResponse(
        id=str(session.id),
        context_type=session.context_type,
        generation_session_id=str(session.generation_session_id) if session.generation_session_id else None,
        created_at=str(session.created_at),
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(session_id: uuid.UUID, request: SendMessageRequest, current_user: CurrentUser, db: DB):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    # Store user message
    user_msg = ChatMessage(
        chat_session_id=session_id,
        role="user",
        content=request.content,
    )
    db.add(user_msg)
    await db.flush()

    # Load recent history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history = list(reversed(history_result.scalars().all()))

    # Build prompt with context
    messages_text = "\n".join([f"{m.role}: {m.content}" for m in history[-5:]])
    system = (
        f"You are CareerOS, a career assistant. "
        f"Context: {chat_session.context_type}. "
        "Help the user with their job search, resume, and career questions. "
        "Be concise, specific, and actionable."
    )

    llm = get_llm_client()
    response_text = llm.complete(
        prompt=messages_text,
        model=settings.haiku_model,
        max_tokens=1024,
        system=system,
    )

    # Store assistant response
    assistant_msg = ChatMessage(
        chat_session_id=session_id,
        role="assistant",
        content=response_text,
    )
    db.add(assistant_msg)
    await db.flush()

    return MessageResponse(
        id=str(assistant_msg.id),
        role="assistant",
        content=response_text,
        created_at=str(assistant_msg.created_at),
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(session_id: uuid.UUID, current_user: CurrentUser, db: DB, limit: int = 50):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return [
        MessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            created_at=str(m.created_at),
        )
        for m in result.scalars().all()
    ]

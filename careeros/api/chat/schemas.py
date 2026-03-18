"""Chat API schemas."""
from pydantic import BaseModel


class CreateChatSessionRequest(BaseModel):
    context_type: str
    generation_session_id: str | None = None


class SendMessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatSessionResponse(BaseModel):
    id: str
    context_type: str
    generation_session_id: str | None
    created_at: str

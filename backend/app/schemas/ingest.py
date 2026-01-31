from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ChannelType(str, Enum):
    CHAT = "chat"
    EMAIL = "email"
    CALL = "call"


class ConversationCreate(BaseModel):
    customer_id: str = Field(..., description="Unique customer identifier")
    channel: ChannelType = Field(..., description="Communication channel")
    content: str = Field(..., description="Conversation content/transcript")
    agent_id: Optional[str] = Field(None, description="Support agent identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ConversationResponse(BaseModel):
    id: str
    customer_id: str
    channel: ChannelType
    content: str
    extracted_context: Dict[str, Any]
    sentiment: str
    intent: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TranscribeRequest(BaseModel):
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio")
    language: str = Field(default="en", description="Audio language")


class TranscribeResponse(BaseModel):
    transcript: str
    confidence: float
    duration_seconds: float
    language: str

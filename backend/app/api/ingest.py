from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import base64

from app.schemas.ingest import (
    ConversationCreate, 
    ConversationResponse, 
    TranscribeRequest, 
    TranscribeResponse
)
from app.services.ai_service import ai_service
from app.services.customer import customer_service

router = APIRouter()


@router.post("/conversation", response_model=ConversationResponse)
async def ingest_conversation(conversation: ConversationCreate):
    """
    Ingest a new customer interaction (chat, email, or call transcript).
    Extracts context, sentiment, and intent automatically.
    """
    # Extract context using AI
    extracted_context = await ai_service.extract_context(conversation.content)
    sentiment = await ai_service.analyze_sentiment(conversation.content)
    intent = await ai_service.detect_intent(conversation.content)
    
    # Store conversation
    conversation_data = {
        "customer_id": conversation.customer_id,
        "channel": conversation.channel.value,
        "content": conversation.content,
        "agent_id": conversation.agent_id,
        "extracted_context": extracted_context,
        "sentiment": sentiment,
        "intent": intent,
        "metadata": conversation.metadata
    }
    
    stored_conversation = await customer_service.add_conversation(conversation_data)
    
    return ConversationResponse(
        id=stored_conversation["id"],
        customer_id=stored_conversation["customer_id"],
        channel=conversation.channel,
        content=stored_conversation["content"],
        extracted_context=extracted_context,
        sentiment=sentiment,
        intent=intent,
        created_at=stored_conversation["created_at"]
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe audio to text. Accepts audio URL or base64-encoded audio.
    """
    if not request.audio_url and not request.audio_base64:
        raise HTTPException(
            status_code=400, 
            detail="Either audio_url or audio_base64 must be provided"
        )
    
    # Get audio data
    if request.audio_base64:
        audio_data = base64.b64decode(request.audio_base64)
    else:
        # In production, fetch from URL
        audio_data = b""
    
    # Transcribe
    result = await ai_service.transcribe_audio(audio_data, request.language)
    
    return TranscribeResponse(
        transcript=result["transcript"],
        confidence=result["confidence"],
        duration_seconds=result["duration_seconds"],
        language=result["language"]
    )


@router.post("/transcribe/upload", response_model=TranscribeResponse)
async def transcribe_audio_upload(file: UploadFile = File(...), language: str = "en"):
    """
    Transcribe uploaded audio file to text.
    """
    audio_data = await file.read()
    
    result = await ai_service.transcribe_audio(audio_data, language)
    
    return TranscribeResponse(
        transcript=result["transcript"],
        confidence=result["confidence"],
        duration_seconds=result["duration_seconds"],
        language=result["language"]
    )


@router.post("/conversation/upload", response_model=ConversationResponse)
async def ingest_conversation_file(
    customer_id: str = Form(..., description="Unique customer identifier"),
    channel: str = Form("chat", description="Communication channel"),
    file: UploadFile = File(...),
):
    """
    Ingest a new customer interaction from an uploaded text file.
    Extracts context, sentiment, and intent automatically.
    """
    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files are supported for conversation upload"
        )
    
    # Read file content
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Could not decode file content. Please ensure it is a valid UTF-8 text file."
        )
    
    # Extract context using AI
    extracted_context = await ai_service.extract_context(content)
    sentiment = await ai_service.analyze_sentiment(content)
    intent = await ai_service.detect_intent(content)
    
    # Store conversation
    conversation_data = {
        "customer_id": customer_id,
        "channel": channel,
        "content": content,
        "agent_id": None,
        "extracted_context": extracted_context,
        "sentiment": sentiment,
        "intent": intent,
        "metadata": {"filename": file.filename}
    }
    
    stored_conversation = await customer_service.add_conversation(conversation_data)
    
    return ConversationResponse(
        id=stored_conversation["id"],
        customer_id=stored_conversation["customer_id"],
        channel=channel,
        content=stored_conversation["content"],
        extracted_context=extracted_context,
        sentiment=sentiment,
        intent=intent,
        created_at=stored_conversation["created_at"]
    )

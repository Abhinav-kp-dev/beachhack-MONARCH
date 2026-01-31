"""
Data models for the Context-Aware Customer Intelligence System

AUTHORITY SEPARATION ENFORCED:
1. Evidence - Raw data (audit only)
2. Extracted Facts - Transient (LLM output)
3. Customer State - Authoritative (single source of truth)
4. Search Index - Display only (never merged into state)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


# ============================================
# 1. EVIDENCE (Raw Data - Audit Only)
# ============================================

class ConversationEvidence(BaseModel):
    """Raw conversation data - evidence only, never used by rules"""
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    customer_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    channel: str  # chat, email, call
    raw_text: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# 2. EXTRACTED FACTS (Transient - LLM Output)
# ============================================

class ConfidenceScore(BaseModel):
    """Confidence score for extracted facts"""
    value: str  # The extracted fact/value
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level (0.0-1.0)")
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }


class ClassifiedPreference(BaseModel):
    """Structured preference with category classification"""
    category: str = Field(description="Category: color, vehicle_type, brand, budget, seating_capacity, transmission, fuel_type, features, timeline, location, etc.")
    value: str = Field(description="The preference value")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level (0.0-1.0)")
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }


class ExtractedContext(BaseModel):
    """
    Transient facts extracted by LLM - NOT stored as-is.
    Must be validated before updating state.
    LLM NEVER reads database - only processes raw text.
    All extracted fields now include confidence scores and structured classification.
    """
    preferences: List[ClassifiedPreference] = Field(default_factory=list, description="Classified preferences with confidence")
    issues: List[ConfidenceScore] = Field(default_factory=list, description="Explicit problems with confidence")
    commitments: List[ConfidenceScore] = Field(default_factory=list, description="Explicit agreements with confidence")
    signals: Dict[str, str] = Field(
        default_factory=dict,
        description="Non-actionable signals: sentiment, urgency, intent (descriptive only)"
    )
    
    # REMOVED: next_best_action (LLM must not recommend actions)
    # REMOVED: summary (no AI-generated operational summaries)
    # REMOVED: inferences (only explicit facts allowed)


# ============================================
# 3. CUSTOMER STATE (Authoritative - Single Source of Truth)
# ============================================

class IssueRecord(BaseModel):
    """Structured issue tracking with full traceability"""
    description: str
    conversation_id: Optional[str] = None  # Track which conversation reported this
    count: int = 1  # How many times mentioned
    status: str = "open"  # open, resolved (use lowercase consistently)
    reported_at: datetime = Field(default_factory=datetime.now)  # When issue was first reported
    resolved_at: Optional[datetime] = None  # When issue was resolved
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CustomerProfile(BaseModel):
    """
    Single source of truth - explicit facts only.
    NO AI-generated summaries, NO inferences, NO predictions.
    Enhanced with context reliability tracking.
    """
    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Confirmed facts only
    # NEW: Structured preferences by category
    preferences: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Classified preferences by category (e.g., {'color': ['black', 'white'], 'vehicle_type': ['suv']})"
    )
    issues: List[IssueRecord] = Field(default_factory=list, description="Tracked issues")
    commitments: List[str] = Field(default_factory=list, description="Confirmed commitments")
    
    # NEW: Confidence tracking for each field
    confidence_scores: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "preferences": {},  # {category: {value: confidence_score}}
            "issues": {},       # {issue_description: confidence_score}
            "commitments": {}   # {commitment: confidence_score}
        },
        description="Confidence scores (0.0-1.0) for each extracted fact"
    )
    
    # Context reliability metadata (tracks how reliable each piece of context is)
    context_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "preference_scores": {},  # {preference: confirmation_count}
            "total_updates": 0,
            "last_updated_conversation": None,
            "avg_confidence": {}  # Average confidence per field type
        },
        description="Metadata for tracking context reliability and confirmation counts"
    )
    
    # Metadata (not inferences)
    interaction_count: int = Field(default=0, description="Total number of conversations/interactions")
    last_interaction: Optional[datetime] = None
    last_sentiment: Optional[str] = None  # Last signal only (not trend)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # REMOVED: history_summary (AI-generated - violates authority)
    # REMOVED: sentiment_trend (inference - non-auditable)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# 4. SEARCH INDEX METADATA (Separate - Display Only)
# ============================================

class SearchIndexEntry(BaseModel):
    """Metadata for FAISS search index - never merged into state"""
    conversation_id: str
    customer_id: str
    embedding_index: int  # Position in FAISS index
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# ACTION LOGGING (Deterministic Rules Only)
# ============================================

class Action(BaseModel):
    """
    Deterministic action log - from rules only, never from LLM.
    All actions must have provenance (which rule triggered them).
    """
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    type: str  # ticket, lead, reminder
    customer_id: str
    conversation_id: Optional[str] = None
    status: str = "pending"  # pending, completed, cancelled
    priority: str = "medium"  # low, medium, high
    details: Dict[str, Any] = Field(default_factory=dict)
    rule_id: Optional[str] = None  # Provenance: which rule created this
    rule_reason: Optional[str] = None  # Human-readable explanation
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# STATE CHANGE AUDIT LOG
# ============================================

class StateChangeLog(BaseModel):
    """Audit log for all state changes - full traceability"""
    log_id: str = Field(default_factory=lambda: str(uuid4()))
    customer_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    change_type: str  # CREATED, UPDATED, ISSUE_RESOLVED, etc.
    fields_changed: List[str] = Field(default_factory=list)  # List of fields that changed
    old_values: Dict[str, Any] = Field(default_factory=dict)  # Previous values
    new_values: Dict[str, Any] = Field(default_factory=dict)  # New values
    reason: str  # Human-readable reason for change
    source_conversation_id: Optional[str] = None  # Which conversation triggered this
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# API REQUEST/RESPONSE MODELS
# ============================================

class ConversationInput(BaseModel):
    """Input for new conversation"""
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    channel: str  # chat, email, call
    text: str


class TranscribeInput(BaseModel):
    """Input for audio transcription"""
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None


class ActionTriggerInput(BaseModel):
    """Manual action trigger by agent"""
    action_type: str  # ticket, lead, reminder
    customer_id: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ContextResponse(BaseModel):
    """Response for context retrieval - clear authority separation"""
    customer_state: CustomerProfile
    evidence_conversations: List[ConversationEvidence]
    pending_actions: List[Action]
    display_summary: Dict[str, Any]  # UI-assembled, no AI
    search_results: Optional[List[Dict[str, Any]]] = None  # Optional, clearly separated
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Backward compatibility aliases (deprecated)
Conversation = ConversationEvidence  # For existing code

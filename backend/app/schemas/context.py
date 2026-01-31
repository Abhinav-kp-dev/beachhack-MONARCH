from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CustomerContext(BaseModel):
    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # Conversation history summary
    total_interactions: int = 0
    last_interaction: Optional[datetime] = None
    preferred_channel: Optional[str] = None
    
    # Extracted insights
    topics_discussed: List[str] = Field(default_factory=list)
    sentiment_history: List[Dict[str, Any]] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Action items
    pending_issues: List[Dict[str, Any]] = Field(default_factory=list)
    resolved_issues: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Long-term memory
    key_memories: List[str] = Field(default_factory=list)
    relationship_score: float = Field(default=0.0, ge=0.0, le=100.0)
    unified_summary: Optional[str] = None
    
    # Insights & Actions
    suggested_questions: List[str] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Premium Features
    health_score: float = Field(default=50.0, ge=0.0, le=100.0, description="Customer health score 0-100")
    health_status: str = Field(default="unknown", description="healthy, at_risk, critical, or unknown")
    next_best_action: Optional[Dict[str, Any]] = Field(default=None, description="AI-recommended next action")
    risk_alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Active risk alerts")
    commitment_status: Optional[Dict[str, Any]] = Field(default=None, description="Commitment tracking stats")


class ContextUpdateRequest(BaseModel):
    customer_id: str
    update_type: str = Field(..., description="Type of context update")
    data: Dict[str, Any] = Field(..., description="Update data")


class ActionTriggerRequest(BaseModel):
    action_type: str = Field(..., description="Type of action to trigger")
    customer_id: str = Field(..., description="Customer ID")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ActionTriggerResponse(BaseModel):
    success: bool
    action_id: str
    message: str
    result: Optional[Dict[str, Any]] = None

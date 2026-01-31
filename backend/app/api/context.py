from fastapi import APIRouter, HTTPException
from app.schemas.context import CustomerContext, ContextUpdateRequest
from app.services.customer import customer_service

router = APIRouter()


@router.get("/customer/{customer_id}/context", response_model=CustomerContext)
async def get_customer_context(customer_id: str):
    """
    Retrieve full context for a customer including:
    - Conversation history summary
    - Extracted insights (topics, sentiment, pain points)
    - Pending and resolved issues
    - Key memories and relationship score
    """
    context = await customer_service.get_customer_context(customer_id)
    
    return CustomerContext(
        customer_id=context.get("customer_id", customer_id),
        name=context.get("name"),
        email=context.get("email"),
        phone=context.get("phone"),
        total_interactions=context.get("total_interactions", 0),
        last_interaction=context.get("last_interaction"),
        preferred_channel=context.get("preferred_channel"),
        topics_discussed=context.get("topics_discussed", []),
        sentiment_history=context.get("sentiment_history", []),
        pain_points=context.get("pain_points", []),
        preferences=context.get("preferences", {}),
        pending_issues=context.get("pending_issues", []),
        resolved_issues=context.get("resolved_issues", []),
        key_memories=context.get("key_memories", []),
        relationship_score=context.get("relationship_score", 0.0)
    )


@router.post("/customer/{customer_id}/context")
async def update_customer_context(customer_id: str, update: ContextUpdateRequest):
    """
    Update customer context with new information.
    """
    if update.update_type == "memory":
        memory = update.data.get("memory", "")
        result = await customer_service.update_customer_memory(customer_id, memory)
        return {"success": True, "customer_id": customer_id, "updated": result}
    
    result = await customer_service.create_or_update_customer(customer_id, update.data)
    return {"success": True, "customer_id": customer_id, "updated": result}

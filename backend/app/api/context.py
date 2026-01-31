from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.context import CustomerContext, ContextUpdateRequest
from app.services.customer import customer_service

router = APIRouter()



@router.get("/customers", response_model=List[CustomerContext])
async def list_customers(limit: int = 100):
    """List all customers"""
    customers = await customer_service.list_customers(limit)
    return [
        CustomerContext(
            customer_id=c.get("customer_id"),
            name=c.get("name"),
            email=c.get("email"),
            phone=c.get("phone"),
            total_interactions=c.get("total_interactions", 0),
            last_interaction=c.get("last_interaction"),
            preferred_channel=c.get("preferred_channel"),
            topics_discussed=c.get("topics_discussed", []),
            sentiment_history=c.get("sentiment_history", []),
            pain_points=c.get("pain_points", []),
            preferences={
                k: v.get("value") 
                for k, v in c.get("context", {}).get("entities", {}).items()
                if isinstance(v, dict) and v.get("confirmed")
            },
            pending_issues=c.get("pending_issues", []),
            resolved_issues=c.get("resolved_issues", []),
            key_memories=c.get("key_memories", []),
            relationship_score=c.get("relationship_score", 0.0),
            unified_summary=c.get("unified_summary")
        ) for c in customers
    ]


@router.get("/customer/{customer_id}/context", response_model=CustomerContext)
async def get_customer_context(customer_id: str):
    """
    Retrieve full context for a customer including:
    - Conversation history summary
    - Extracted insights (topics, sentiment, pain points)
    - Pending and resolved issues
    - Key memories and relationship score
    - PREMIUM: Health score, risk alerts, next best action, commitment tracking
    """
    context = await customer_service.get_customer_context(customer_id)
    
    # Calculate premium features
    customer = await customer_service.get_customer(customer_id)
    if customer:
        health_score, health_status = customer_service.calculate_health_score(customer)
        risk_alerts = customer_service.detect_risk_alerts(customer)
        commitment_status = customer_service.analyze_commitments(customer)
        next_best_action = customer_service.generate_next_best_action(customer, risk_alerts)
    else:
        health_score, health_status = 50.0, "unknown"
        risk_alerts = []
        commitment_status = None
        next_best_action = None
    
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
        preferences={
            k: v.get("value") 
            for k, v in context.get("context", {}).get("entities", {}).items()
            if isinstance(v, dict) and v.get("confirmed")
        },
        pending_issues=context.get("pending_issues", []),
        resolved_issues=context.get("resolved_issues", []),
        key_memories=context.get("key_memories", []),
        relationship_score=context.get("relationship_score", 0.0),
        unified_summary=context.get("unified_summary"),
        suggested_questions=context.get("suggested_questions", []),
        recommendations=context.get("recommendations", []),
        # Premium features
        health_score=health_score,
        health_status=health_status,
        risk_alerts=risk_alerts,
        next_best_action=next_best_action,
        commitment_status=commitment_status
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

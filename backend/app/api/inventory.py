from fastapi import APIRouter
from app.schemas.context import ActionTriggerRequest, ActionTriggerResponse
from app.services.trigger import trigger_service

router = APIRouter()


@router.post("/action/trigger", response_model=ActionTriggerResponse)
async def trigger_action(request: ActionTriggerRequest):
    """
    Execute an automated action based on customer context.
    
    Supported action types:
    - send_email: Send templated email to customer
    - create_ticket: Create support ticket
    - escalate: Escalate to higher tier support
    - send_notification: Send push/SMS notification
    - update_crm: Update CRM records
    - schedule_callback: Schedule callback with customer
    """
    result = await trigger_service.execute_action(
        action_type=request.action_type,
        customer_id=request.customer_id,
        parameters=request.parameters
    )
    
    return ActionTriggerResponse(
        success=result["success"],
        action_id=result["action_id"] or "",
        message=result["message"],
        result=result["result"]
    )

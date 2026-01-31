"""
Action service for managing automated actions

AUTHORITY SEPARATION ENFORCED:
- Actions triggered by DETERMINISTIC RULES ONLY (never from LLM)
- Input: Customer state only (never LLM output directly, never embeddings)
- Output: Actions with full provenance (rule_id, reason)
- All actions are auditable, repeatable, and explainable
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from tinydb import TinyDB, Query
from models import Action, CustomerProfile, IssueRecord
import config

logger = logging.getLogger(__name__)


# ============================================
# DETERMINISTIC RULE ENGINE
# ============================================

class ActionRules:
    """
    Deterministic rule engine for action recommendations.
    Each rule has a unique ID and human-readable explanation.
    Rules operate on customer STATE only (never LLM output, never embeddings).
    """
    
    @staticmethod
    def evaluate(customer_state: CustomerProfile) -> Optional[Dict[str, Any]]:
        """
        Evaluate all rules against customer state.
        Returns first matching rule with full provenance.
        
        Args:
            customer_state: Authoritative customer state only
            
        Returns:
            Dict with {action_type, rule_id, reason, priority} or None
        """
        
        # RULE R001: Unresolved issues → high-priority ticket
        open_issues = [issue for issue in customer_state.issues if issue.status == "open"]
        if len(open_issues) > 0:
            issue = open_issues[0]  # Take first open issue
            return {
                "action_type": "ticket",
                "rule_id": "R001_UNRESOLVED_ISSUE",
                "reason": f"Unresolved issue: {issue.description}",
                "priority": "high" if issue.count > 1 else "medium",
                "details": {
                    "issue": issue.description,
                    "mention_count": issue.count,
                    "ticket_type": "support"
                }
            }
        
        # RULE R002: Purchase intent + preferences → high-priority lead
        purchase_keywords = ["purchase", "buy", "interested in", "looking for", "need to order"]
        has_purchase_intent = any(
            keyword in pref.lower() 
            for pref in customer_state.preferences 
            for keyword in purchase_keywords
        )
        if has_purchase_intent and len(customer_state.preferences) > 0:
            return {
                "action_type": "lead",
                "rule_id": "R002_PURCHASE_INTENT",
                "reason": f"Purchase intent detected with {len(customer_state.preferences)} preferences",
                "priority": "high",
                "details": {
                    "opportunity": "Product interest identified",
                    "preferences": customer_state.preferences,
                    "lead_type": "sales",
                    "stage": "new"
                }
            }
        
        # RULE R003: Commitment with follow-up indicators → reminder
        followup_keywords = ["follow up", "callback", "get back", "reach out", "contact"]
        has_followup = any(
            keyword in commitment.lower()
            for commitment in customer_state.commitments
            for keyword in followup_keywords
        )
        if has_followup:
            commitment = next(
                (c for c in customer_state.commitments if any(k in c.lower() for k in followup_keywords)),
                None
            )
            return {
                "action_type": "reminder",
                "rule_id": "R003_COMMITMENT_FOLLOWUP",
                "reason": f"Follow-up commitment detected: {commitment}",
                "priority": "medium",
                "details": {
                    "task": commitment,
                    "reminder_type": "followup"
                }
            }
        
        # RULE R004: Budget-sensitive preferences → medium-priority lead
        budget_keywords = ["budget", "price", "cost", "afford", "lakh", "thousand"]
        has_budget_mention = any(
            keyword in pref.lower()
            for pref in customer_state.preferences
            for keyword in budget_keywords
        )
        if has_budget_mention and len(customer_state.preferences) >= 2:
            return {
                "action_type": "lead",
                "rule_id": "R004_BUDGET_INQUIRY",
                "reason": f"Budget-conscious inquiry with {len(customer_state.preferences)} preferences",
                "priority": "medium",
                "details": {
                    "opportunity": "Price-sensitive customer",
                    "preferences": customer_state.preferences,
                    "lead_type": "sales",
                    "stage": "qualification"
                }
            }
        
        # RULE R005: Multiple preferences without issues → lead
        if len(customer_state.preferences) >= 3 and len(open_issues) == 0:
            return {
                "action_type": "lead",
                "rule_id": "R005_MULTI_PREFERENCE",
                "reason": f"{len(customer_state.preferences)} explicit preferences recorded",
                "priority": "medium",
                "details": {
                    "opportunity": "Detailed requirements captured",
                    "preferences": customer_state.preferences,
                    "lead_type": "sales",
                    "stage": "interested"
                }
            }
        
        # No rule matched
        return None
    
    @staticmethod
    def generate_recommendations(customer_state: CustomerProfile) -> List[Dict[str, Any]]:
        """
        RULE R006: Generate personalized product/service recommendations
        Based on customer preferences and conversation history
        
        Args:
            customer_state: Authoritative customer state
            
        Returns:
            List of recommendation dicts with product/service suggestions
        """
        recommendations = []
        prefs_text = " ".join(customer_state.preferences).lower()
        
        # Vehicle recommendations (for auto dealership scenario)
        if any(keyword in prefs_text for keyword in ["car", "vehicle", "suv", "sedan", "hatchback"]):
            if "suv" in prefs_text:
                recommendations.append({
                    "category": "Vehicle Type",
                    "recommendation": "Toyota RAV4, Honda CR-V, Mazda CX-5",
                    "reason": "Based on SUV preference",
                    "confidence": "high"
                })
            if "sedan" in prefs_text:
                recommendations.append({
                    "category": "Vehicle Type",
                    "recommendation": "Honda Accord, Toyota Camry, Hyundai Sonata",
                    "reason": "Based on sedan preference",
                    "confidence": "high"
                })
            if "hatchback" in prefs_text:
                recommendations.append({
                    "category": "Vehicle Type",
                    "recommendation": "Honda Fit, Toyota Yaris, Mazda 3",
                    "reason": "Based on hatchback preference",
                    "confidence": "high"
                })
        
        # Budget-based recommendations
        if "budget" in prefs_text or "price" in prefs_text:
            if any(num in prefs_text for num in ["30000", "30k", "35000", "35k"]):
                recommendations.append({
                    "category": "Budget Range",
                    "recommendation": "Showing vehicles under $35,000",
                    "reason": "Budget constraint identified",
                    "confidence": "high"
                })
            if any(num in prefs_text for num in ["50000", "50k", "60000", "60k"]):
                recommendations.append({
                    "category": "Budget Range",
                    "recommendation": "Premium models available: Lexus, Audi, BMW",
                    "reason": "Higher budget range",
                    "confidence": "high"
                })
        
        # Feature-based recommendations
        if "7 seat" in prefs_text or "seven seat" in prefs_text or "family" in prefs_text:
            recommendations.append({
                "category": "Features",
                "recommendation": "Toyota Highlander, Honda Pilot (7-8 seater SUVs)",
                "reason": "Family size requirements",
                "confidence": "high"
            })
        
        if "fuel efficiency" in prefs_text or "mileage" in prefs_text or "hybrid" in prefs_text:
            recommendations.append({
                "category": "Features",
                "recommendation": "Hybrid models: Toyota Prius, Honda Insight, Hyundai Ioniq",
                "reason": "Fuel efficiency priority",
                "confidence": "high"
            })
        
        if "safety" in prefs_text or "iihs" in prefs_text:
            recommendations.append({
                "category": "Features",
                "recommendation": "Top safety picks: Mazda CX-5, Subaru Outback, Honda CR-V",
                "reason": "Safety-conscious buyer",
                "confidence": "high"
            })
        
        # Color preferences
        if any(color in prefs_text for color in ["black", "white", "red", "blue", "silver"]):
            color = next((c for c in ["black", "white", "red", "blue", "silver"] if c in prefs_text), "")
            recommendations.append({
                "category": "Color",
                "recommendation": f"Available in {color.capitalize()}",
                "reason": f"Color preference: {color}",
                "confidence": "medium"
            })
        
        # Generic recommendation if no specific matches
        if not recommendations and len(customer_state.preferences) > 0:
            recommendations.append({
                "category": "General",
                "recommendation": "Based on your preferences, our sales team can provide personalized options",
                "reason": "Custom requirements detected",
                "confidence": "medium"
            })
        
        return recommendations

# ============================================
# ACTION SERVICE (CRUD Operations)
# ============================================

class ActionService:
    """Service for managing and executing actions"""
    
    def __init__(self):
        self.db = TinyDB(config.ACTIONS_DB)
        self.rules = ActionRules()
        logger.info(f"Initialized ActionService with database: {config.ACTIONS_DB}")
    
    def create_action(self, 
                     action_type: str,
                     customer_id: str,
                     conversation_id: Optional[str] = None,
                     priority: str = "medium",
                     details: Dict[str, Any] = None,
                     rule_id: Optional[str] = None,
                     rule_reason: Optional[str] = None) -> Action:
        """
        Create a new action with full provenance
        
        Args:
            action_type: Type of action (ticket, lead, reminder)
            customer_id: Associated customer ID
            conversation_id: Optional associated conversation
            priority: Action priority (low, medium, high)
            details: Additional action details
            rule_id: Which rule triggered this action (for auditability)
            rule_reason: Human-readable explanation
            
        Returns:
            Created Action object
        """
        action = Action(
            type=action_type,
            customer_id=customer_id,
            conversation_id=conversation_id,
            priority=priority,
            details=details or {},
            rule_id=rule_id,
            rule_reason=rule_reason
        )
        
        # Save to database
        action_dict = action.model_dump()
        action_dict['created_at'] = action.created_at.isoformat()
        if action.completed_at:
            action_dict['completed_at'] = action.completed_at.isoformat()
        
        self.db.insert(action_dict)
        logger.info(f"Created {action_type} action: {action.action_id} for customer {customer_id} | Rule: {rule_id}")
        
        return action
    
    def create_ticket(self, customer_id: str, issue: str, priority: str = "medium", 
                     conversation_id: Optional[str] = None) -> Action:
        """
        Create a support ticket
        
        Args:
            customer_id: Customer ID
            issue: Issue description
            priority: Ticket priority
            conversation_id: Associated conversation
            
        Returns:
            Created Action
        """
        details = {
            "issue": issue,
            "ticket_type": "support",
            "description": f"Support ticket for: {issue}"
        }
        
        return self.create_action(
            action_type="ticket",
            customer_id=customer_id,
            conversation_id=conversation_id,
            priority=priority,
            details=details
        )
    
    def create_lead(self, customer_id: str, opportunity: str, value: Optional[float] = None,
                   conversation_id: Optional[str] = None) -> Action:
        """
        Create a sales lead
        
        Args:
            customer_id: Customer ID
            opportunity: Opportunity description
            value: Estimated value
            conversation_id: Associated conversation
            
        Returns:
            Created Action
        """
        details = {
            "opportunity": opportunity,
            "estimated_value": value,
            "lead_type": "sales",
            "stage": "new"
        }
        
        return self.create_action(
            action_type="lead",
            customer_id=customer_id,
            conversation_id=conversation_id,
            priority="high",
            details=details
        )
    
    def create_reminder(self, customer_id: str, task: str, due_date: Optional[str] = None,
                       conversation_id: Optional[str] = None) -> Action:
        """
        Create a follow-up reminder
        
        Args:
            customer_id: Customer ID
            task: Task description
            due_date: Due date string
            conversation_id: Associated conversation
            
        Returns:
            Created Action
        """
        details = {
            "task": task,
            "due_date": due_date,
            "reminder_type": "followup"
        }
        
        return self.create_action(
            action_type="reminder",
            customer_id=customer_id,
            conversation_id=conversation_id,
            priority="medium",
            details=details
        )
    
    def get_action(self, action_id: str) -> Optional[Action]:
        """
        Retrieve action by ID
        
        Args:
            action_id: Action identifier
            
        Returns:
            Action object or None
        """
        ActionQuery = Query()
        results = self.db.search(ActionQuery.action_id == action_id)
        
        if not results:
            return None
        
        action_data = results[0]
        action_data['created_at'] = datetime.fromisoformat(action_data['created_at'])
        if action_data.get('completed_at'):
            action_data['completed_at'] = datetime.fromisoformat(action_data['completed_at'])
        
        return Action(**action_data)
    
    def get_customer_actions(self, customer_id: str, status: Optional[str] = None) -> List[Action]:
        """
        Get all actions for a customer
        
        Args:
            customer_id: Customer identifier
            status: Optional filter by status (pending, completed, cancelled)
            
        Returns:
            List of Action objects
        """
        ActionQuery = Query()
        
        if status:
            results = self.db.search(
                (ActionQuery.customer_id == customer_id) &
                (ActionQuery.status == status)
            )
        else:
            results = self.db.search(ActionQuery.customer_id == customer_id)
        
        # Sort by created_at descending
        results = sorted(results, key=lambda x: x.get('created_at', ''), reverse=True)
        
        actions = []
        for action_data in results:
            action_data['created_at'] = datetime.fromisoformat(action_data['created_at'])
            if action_data.get('completed_at'):
                action_data['completed_at'] = datetime.fromisoformat(action_data['completed_at'])
            actions.append(Action(**action_data))
        
        return actions
    
    def update_action_status(self, action_id: str, status: str) -> Optional[Action]:
        """
        Update action status
        
        Args:
            action_id: Action identifier
            status: New status (pending, completed, cancelled)
            
        Returns:
            Updated Action or None
        """
        action = self.get_action(action_id)
        if not action:
            logger.warning(f"Action {action_id} not found")
            return None
        
        action.status = status
        if status == "completed":
            action.completed_at = datetime.now()
        
        # Save to database
        ActionQuery = Query()
        action_dict = action.model_dump()
        action_dict['created_at'] = action.created_at.isoformat()
        if action.completed_at:
            action_dict['completed_at'] = action.completed_at.isoformat()
        
        self.db.update(action_dict, ActionQuery.action_id == action_id)
        logger.info(f"Updated action {action_id} status to {status}")
        
        return action
    
    def get_pending_actions(self, limit: int = 50) -> List[Action]:
        """
        Get all pending actions across all customers
        
        Args:
            limit: Maximum number of actions to return
            
        Returns:
            List of pending Action objects
        """
        ActionQuery = Query()
        results = self.db.search(ActionQuery.status == "pending")
        
        # Sort by priority and created_at
        priority_order = {"high": 0, "medium": 1, "low": 2}
        results = sorted(
            results,
            key=lambda x: (priority_order.get(x.get('priority', 'medium'), 1), x.get('created_at', '')),
            reverse=False
        )
        results = results[:limit]
        
        actions = []
        for action_data in results:
            # Handle datetime conversion - check if already datetime object
            if isinstance(action_data.get('created_at'), str):
                action_data['created_at'] = datetime.fromisoformat(action_data['created_at'])
            elif not isinstance(action_data.get('created_at'), datetime):
                action_data['created_at'] = datetime.now()
            
            if action_data.get('completed_at'):
                if isinstance(action_data['completed_at'], str):
                    action_data['completed_at'] = datetime.fromisoformat(action_data['completed_at'])
                elif not isinstance(action_data['completed_at'], datetime):
                    action_data['completed_at'] = None
            
            actions.append(Action(**action_data))
        
        return actions
    
    def recommend_action(self, customer_state: CustomerProfile) -> Dict[str, Any]:
        """
        Recommend action using DETERMINISTIC RULES ONLY.
        Input: Customer state ONLY (never LLM output, never embeddings)
        Output: Action recommendation with full provenance (always returns a dict)
        
        Args:
            customer_state: Authoritative customer state
            
        Returns:
            Dict with action details and provenance (never None)
        """
        recommendation = self.rules.evaluate(customer_state)
        
        if recommendation:
            logger.info(f"Rule {recommendation['rule_id']} triggered for customer {customer_state.customer_id}: {recommendation['reason']}")
            return recommendation
        else:
            logger.debug(f"No action rule matched for customer {customer_state.customer_id}")
            # Return default 'none' action when no rules match
            return {
                "action_type": "none",
                "rule_id": "R000_NO_ACTION",
                "reason": "No action required at this time",
                "priority": "low",
                "details": {
                    "note": "Customer state does not match any action rules"
                }
            }


# Singleton instance
_action_service = None

def get_action_service() -> ActionService:
    """Get or create singleton instance of ActionService"""
    global _action_service
    if _action_service is None:
        _action_service = ActionService()
    return _action_service

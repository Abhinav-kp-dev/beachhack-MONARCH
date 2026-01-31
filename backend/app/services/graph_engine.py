from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import copy


class StateTransition(str, Enum):
    """Types of state transitions"""
    REPLACE = "REPLACE"          # Replace existing value with new value
    ARCHIVE = "ARCHIVE"          # Archive old value before replacing
    PENDING = "PENDING"          # Move to pending for review
    IGNORE = "IGNORE"            # Ignore the proposed change
    CONFIRM = "CONFIRM"          # Confirm a pending item
    ADD = "ADD"                  # Add new entity/field
    RESOLVE = "RESOLVE"          # Mark issue as resolved
    

class ConfidenceThreshold:
    """
    Confidence threshold constants - now configurable via settings.
    
    Tune these based on your LLM's actual confidence distributions.
    Monitor your LLM's outputs and adjust thresholds accordingly.
    """
    
    @staticmethod
    def get_high() -> float:
        """Get HIGH confidence threshold from settings"""
        from app.core.config import settings
        return settings.CONFIDENCE_HIGH
    
    @staticmethod
    def get_medium() -> float:
        """Get MEDIUM confidence threshold from settings"""
        from app.core.config import settings
        return settings.CONFIDENCE_MEDIUM
    
    # Legacy constants for backward compatibility
    HIGH = 0.80
    MEDIUM = 0.55
    LOW = 0.0


class TransitionDecision:
    """Represents a single state transition decision"""
    
    def __init__(
        self,
        field: str,
        action: StateTransition,
        old_value: Any = None,
        new_value: Any = None,
        confidence: float = 0.0,
        reason: str = ""
    ):
        self.field = field
        self.action = action
        self.old_value = old_value
        self.new_value = new_value
        self.confidence = confidence
        self.reason = reason
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "field": self.field,
            "action": self.action.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp
        }


class GraphEngine:
    """
    Deterministic graph-based state transition engine for customer profiles.
    
    This engine implements a state machine that:
    1. Evaluates proposed changes from LLM against current state
    2. Makes deterministic decisions based on confidence thresholds
    3. Preserves historical data through archival
    4. Logs all transitions with explanations
    
    The LLM NEVER directly modifies the profile - all changes go through this engine.
    
    Confidence thresholds are configurable via settings for tuning.
    """
    
    def __init__(self):
        # Use configurable thresholds from settings
        self.high_threshold = ConfidenceThreshold.get_high()
        self.medium_threshold = ConfidenceThreshold.get_medium()
    
    async def evaluate_transitions(
        self,
        current_state: Dict[str, Any],
        proposed_state: Dict[str, Any]
    ) -> List[TransitionDecision]:
        """
        Evaluate all proposed changes and return transition decisions.
        
        Args:
            current_state: Current customer context (from MongoDB)
            proposed_state: LLM-extracted proposals with confidence scores
            
        Returns:
            List of TransitionDecision objects
        """
        decisions = []
        
        # Evaluate intent transition
        if "intent" in proposed_state:
            intent_decision = self._evaluate_intent_transition(
                current_state.get("intent"),
                proposed_state["intent"]
            )
            if intent_decision:
                decisions.append(intent_decision)
        
        # Evaluate entity transitions
        if "entities" in proposed_state:
            entity_decisions = self._evaluate_entity_transitions(
                current_state.get("entities", {}),
                proposed_state["entities"]
            )
            decisions.extend(entity_decisions)
        
        # Evaluate topic transitions
        if "topics" in proposed_state:
            topic_decisions = self._evaluate_topic_transitions(
                current_state.get("topics", {}),
                proposed_state["topics"]
            )
            decisions.extend(topic_decisions)
        
        return decisions
    
    def _evaluate_intent_transition(
        self,
        current_intent: Optional[Dict[str, Any]],
        proposed_intent: Dict[str, Any]
    ) -> Optional[TransitionDecision]:
        """
        Evaluate intent transition.
        
        Rules:
        - Replace if: value changed AND confidence >= HIGH
        - Pending if: value changed AND confidence >= MEDIUM
        - Ignore otherwise
        """
        proposed_value = proposed_intent.get("value")
        proposed_confidence = proposed_intent.get("confidence", 0.0)
        
        # No current intent - add if high confidence
        if not current_intent:
            if proposed_confidence >= self.high_threshold:
                return TransitionDecision(
                    field="context.intent",
                    action=StateTransition.ADD,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason=f"New intent with high confidence ({proposed_confidence:.2f})"
                )
            elif proposed_confidence >= self.medium_threshold:
                return TransitionDecision(
                    field="context.intent",
                    action=StateTransition.PENDING,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason=f"New intent with medium confidence ({proposed_confidence:.2f})"
                )
            else:
                return TransitionDecision(
                    field="context.intent",
                    action=StateTransition.IGNORE,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason=f"Low confidence ({proposed_confidence:.2f})"
                )
        
        current_value = current_intent.get("value")
        
        # Same value - ignore
        if current_value == proposed_value:
            return TransitionDecision(
                field="context.intent",
                action=StateTransition.IGNORE,
                old_value=current_value,
                new_value=proposed_value,
                confidence=proposed_confidence,
                reason="Value unchanged"
            )
        
        # Different value - check confidence
        if proposed_confidence >= self.high_threshold:
            return TransitionDecision(
                field="context.intent",
                action=StateTransition.REPLACE,
                old_value=current_value,
                new_value=proposed_value,
                confidence=proposed_confidence,
                reason=f"Value changed with high confidence ({proposed_confidence:.2f})"
            )
        elif proposed_confidence >= self.medium_threshold:
            return TransitionDecision(
                field="context.intent",
                action=StateTransition.PENDING,
                old_value=current_value,
                new_value=proposed_value,
                confidence=proposed_confidence,
                reason=f"Value changed with medium confidence ({proposed_confidence:.2f})"
            )
        else:
            return TransitionDecision(
                field="context.intent",
                action=StateTransition.IGNORE,
                old_value=current_value,
                new_value=proposed_value,
                confidence=proposed_confidence,
                reason=f"Low confidence ({proposed_confidence:.2f})"
            )
    
    def _evaluate_entity_transitions(
        self,
        current_entities: Dict[str, Any],
        proposed_entities: Dict[str, Any]
    ) -> List[TransitionDecision]:
        """
        Evaluate entity transitions.
        
        Rules for each entity key:
        - New entity + HIGH confidence → ADD
        - Same value → IGNORE
        - Different value + HIGH confidence → REPLACE + ARCHIVE old
        - Different value + MEDIUM confidence → PENDING
        - LOW confidence → IGNORE
        """
        decisions = []
        
        for entity_key, proposed_data in proposed_entities.items():
            # Handle both dict format and simple values
            if isinstance(proposed_data, dict):
                proposed_value = proposed_data.get("value")
                proposed_confidence = proposed_data.get("confidence", 0.0)
            else:
                # Simple value without confidence - treat as low confidence
                proposed_value = proposed_data
                proposed_confidence = 0.0
            
            field = f"context.entities.{entity_key}"
            current_entity = current_entities.get(entity_key)
            
            # No current entity - add if high confidence
            if not current_entity:
                if proposed_confidence >= self.high_threshold:
                    decisions.append(TransitionDecision(
                        field=field,
                        action=StateTransition.ADD,
                        new_value=proposed_value,
                        confidence=proposed_confidence,
                        reason=f"New entity with high confidence ({proposed_confidence:.2f})"
                    ))
                elif proposed_confidence >= self.medium_threshold:
                    decisions.append(TransitionDecision(
                        field=field,
                        action=StateTransition.PENDING,
                        new_value=proposed_value,
                        confidence=proposed_confidence,
                        reason=f"New entity with medium confidence ({proposed_confidence:.2f})"
                    ))
                else:
                    decisions.append(TransitionDecision(
                        field=field,
                        action=StateTransition.IGNORE,
                        new_value=proposed_value,
                        confidence=proposed_confidence,
                        reason=f"Low confidence ({proposed_confidence:.2f})"
                    ))
                continue
            
            current_value = current_entity.get("value") if isinstance(current_entity, dict) else current_entity
            
            # Same value - ignore
            if current_value == proposed_value:
                decisions.append(TransitionDecision(
                    field=field,
                    action=StateTransition.IGNORE,
                    old_value=current_value,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason="Value unchanged"
                ))
                continue
            
            # Different value - check confidence
            if proposed_confidence >= self.high_threshold:
                decisions.append(TransitionDecision(
                    field=field,
                    action=StateTransition.ARCHIVE,  # Archive old before replacing
                    old_value=current_value,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason=f"Value changed with high confidence ({proposed_confidence:.2f}), archiving old value"
                ))
            elif proposed_confidence >= self.medium_threshold:
                decisions.append(TransitionDecision(
                    field=field,
                    action=StateTransition.PENDING,
                    old_value=current_value,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason=f"Value changed with medium confidence ({proposed_confidence:.2f})"
                ))
            else:
                decisions.append(TransitionDecision(
                    field=field,
                    action=StateTransition.IGNORE,
                    old_value=current_value,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason=f"Low confidence ({proposed_confidence:.2f})"
                ))
        
        return decisions
    
    def _evaluate_topic_transitions(
        self,
        current_topics: Dict[str, Any],
        proposed_topics: Dict[str, Any]
    ) -> List[TransitionDecision]:
        """
        Evaluate topic transitions.
        
        Similar logic to entities but topics are typically additive.
        """
        decisions = []
        
        for topic_key, proposed_data in proposed_topics.items():
            if isinstance(proposed_data, dict):
                proposed_value = proposed_data.get("value", topic_key)
                proposed_confidence = proposed_data.get("confidence", 0.0)
            else:
                proposed_value = topic_key
                proposed_confidence = 0.0
            
            field = f"context.topics.{topic_key}"
            current_topic = current_topics.get(topic_key)
            
            # No current topic - add if high confidence
            if not current_topic:
                if proposed_confidence >= self.high_threshold:
                    decisions.append(TransitionDecision(
                        field=field,
                        action=StateTransition.ADD,
                        new_value=proposed_value,
                        confidence=proposed_confidence,
                        reason=f"New topic with high confidence ({proposed_confidence:.2f})"
                    ))
                elif proposed_confidence >= self.medium_threshold:
                    decisions.append(TransitionDecision(
                        field=field,
                        action=StateTransition.PENDING,
                        new_value=proposed_value,
                        confidence=proposed_confidence,
                        reason=f"New topic with medium confidence ({proposed_confidence:.2f})"
                    ))
                else:
                    decisions.append(TransitionDecision(
                        field=field,
                        action=StateTransition.IGNORE,
                        new_value=proposed_value,
                        confidence=proposed_confidence,
                        reason=f"Low confidence ({proposed_confidence:.2f})"
                    ))
            else:
                # Topic already exists - ignore
                decisions.append(TransitionDecision(
                    field=field,
                    action=StateTransition.IGNORE,
                    new_value=proposed_value,
                    confidence=proposed_confidence,
                    reason="Topic already exists"
                ))
        
        return decisions
    
    def prepare_mongodb_updates(
        self,
        decisions: List[TransitionDecision]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Convert transition decisions into MongoDB update operations.
        
        Returns:
            Tuple of (update_operations, pending_items)
        """
        set_ops = {}
        push_ops = {}
        pending_items = []
        
        for decision in decisions:
            if decision.action == StateTransition.IGNORE:
                # No database operation needed
                continue
            
            elif decision.action in [StateTransition.ADD, StateTransition.REPLACE]:
                # Set the new value
                set_ops[decision.field] = {
                    "value": decision.new_value,
                    "confidence": decision.confidence,
                    "confirmed": True,
                    "updated_at": decision.timestamp
                }
            
            elif decision.action == StateTransition.ARCHIVE:
                # Archive old value and set new value
                set_ops[decision.field] = {
                    "value": decision.new_value,
                    "confidence": decision.confidence,
                    "confirmed": True,
                    "updated_at": decision.timestamp
                }
                
                # Add old value to archived_values array
                archive_field = f"{decision.field}.archived_values"
                if archive_field not in push_ops:
                    push_ops[archive_field] = []
                
                push_ops[archive_field].append({
                    "value": decision.old_value,
                    "confidence": decision.confidence,
                    "replaced_at": decision.timestamp
                })
            
            elif decision.action == StateTransition.PENDING:
                # Set as unconfirmed in context
                set_ops[decision.field] = {
                    "value": decision.new_value,
                    "confidence": decision.confidence,
                    "confirmed": False,
                    "updated_at": decision.timestamp
                }
                
                # Add to pending_inference
                pending_items.append({
                    "field": decision.field,
                    "proposed_value": decision.new_value,
                    "confidence": decision.confidence,
                    "status": "needs_review",
                    "detected_at": decision.timestamp,
                    "reason": decision.reason
                })
        
        # Build MongoDB update document
        update_ops = {}
        if set_ops:
            update_ops["$set"] = set_ops
        
        # Handle push operations for archived values
        for field, values in push_ops.items():
            if "$push" not in update_ops:
                update_ops["$push"] = {}
            
            # For archived_values, we need to push to the array
            # MongoDB path: context.entities.budget.archived_values
            # But we set the parent object, so we need to handle this carefully
            # We'll use $push with $each for arrays
            if field.endswith(".archived_values"):
                parent_field = field.replace(".archived_values", "")
                # Initialize archived_values if not exists
                if parent_field not in set_ops:
                    set_ops[parent_field] = {}
                if "archived_values" not in set_ops[parent_field]:
                    set_ops[parent_field]["archived_values"] = []
                
                # Add to the archived_values array
                set_ops[parent_field]["archived_values"].extend(values)
        
        return update_ops, pending_items
    
    def get_final_state(
        self,
        current_state: Dict[str, Any],
        decisions: List[TransitionDecision]
    ) -> Dict[str, Any]:
        """
        Calculate the final state after applying all transitions.
        
        This is used to pass to the LLM for summary generation.
        """
        final_state = copy.deepcopy(current_state)
        
        for decision in decisions:
            if decision.action in [StateTransition.ADD, StateTransition.REPLACE, StateTransition.ARCHIVE]:
                # Update the value in final state
                parts = decision.field.split(".")
                
                # Navigate to the parent
                current = final_state
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the final value
                current[parts[-1]] = {
                    "value": decision.new_value,
                    "confidence": decision.confidence,
                    "confirmed": True
                }
        
        return final_state


# Singleton instance
graph_engine = GraphEngine()

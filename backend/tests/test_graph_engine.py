"""
Test suite for Graph Engine

Tests the deterministic state transition logic for customer profile updates.
"""

import pytest
from app.services.graph_engine import (
    GraphEngine,
    StateTransition,
    ConfidenceThreshold,
    TransitionDecision
)


@pytest.fixture
def graph_engine():
    """Create a graph engine instance"""
    return GraphEngine()


class TestIntentTransitions:
    """Test intent transition logic"""
    
    @pytest.mark.asyncio
    async def test_new_intent_high_confidence(self, graph_engine):
        """Test: New intent with high confidence → ADD"""
        current_state = {}
        proposed_state = {
            "intent": {"value": "support_request", "confidence": 0.95}
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        assert len(decisions) == 1
        assert decisions[0].action == StateTransition.ADD
        assert decisions[0].new_value == "support_request"
        assert decisions[0].confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_new_intent_medium_confidence(self, graph_engine):
        """Test: New intent with medium confidence → PENDING"""
        current_state = {}
        proposed_state = {
            "intent": {"value": "purchase_inquiry", "confidence": 0.65}
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        assert len(decisions) == 1
        assert decisions[0].action == StateTransition.PENDING
        assert decisions[0].new_value == "purchase_inquiry"
    
    @pytest.mark.asyncio
    async def test_new_intent_low_confidence(self, graph_engine):
        """Test: New intent with low confidence → IGNORE"""
        current_state = {}
        proposed_state = {
            "intent": {"value": "general", "confidence": 0.45}
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        assert len(decisions) == 1
        assert decisions[0].action == StateTransition.IGNORE
    
    @pytest.mark.asyncio
    async def test_same_intent_unchanged(self, graph_engine):
        """Test: Same intent value → IGNORE"""
        current_state = {
            "intent": {"value": "support_request", "confidence": 0.90, "confirmed": True}
        }
        proposed_state = {
            "intent": {"value": "support_request", "confidence": 0.85}
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        assert len(decisions) == 1
        assert decisions[0].action == StateTransition.IGNORE
        assert decisions[0].reason == "Value unchanged"
    
    @pytest.mark.asyncio
    async def test_intent_change_high_confidence(self, graph_engine):
        """Test: Intent changed with high confidence → REPLACE"""
        current_state = {
            "intent": {"value": "support_request", "confidence": 0.90, "confirmed": True}
        }
        proposed_state = {
            "intent": {"value": "cancellation", "confidence": 0.88}
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        assert len(decisions) == 1
        assert decisions[0].action == StateTransition.REPLACE
        assert decisions[0].old_value == "support_request"
        assert decisions[0].new_value == "cancellation"


class TestEntityTransitions:
    """Test entity transition logic"""
    
    @pytest.mark.asyncio
    async def test_new_entity_high_confidence(self, graph_engine):
        """Test: New entity with high confidence → ADD"""
        current_state = {"entities": {}}
        proposed_state = {
            "entities": {
                "budget": {"value": "50000", "confidence": 0.85}
            }
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        entity_decisions = [d for d in decisions if "entities" in d.field]
        assert len(entity_decisions) == 1
        assert entity_decisions[0].action == StateTransition.ADD
        assert entity_decisions[0].new_value == "50000"
    
    @pytest.mark.asyncio
    async def test_entity_change_archive_old(self, graph_engine):
        """Test: Entity changed with high confidence → ARCHIVE old + REPLACE"""
        current_state = {
            "entities": {
                "budget": {"value": "30000", "confidence": 0.90, "confirmed": True}
            }
        }
        proposed_state = {
            "entities": {
                "budget": {"value": "50000", "confidence": 0.85}
            }
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        entity_decisions = [d for d in decisions if "entities" in d.field]
        assert len(entity_decisions) == 1
        assert entity_decisions[0].action == StateTransition.ARCHIVE
        assert entity_decisions[0].old_value == "30000"
        assert entity_decisions[0].new_value == "50000"
    
    @pytest.mark.asyncio
    async def test_entity_same_value_ignore(self, graph_engine):
        """Test: Entity with same value → IGNORE"""
        current_state = {
            "entities": {
                "budget": {"value": "50000", "confidence": 0.90, "confirmed": True}
            }
        }
        proposed_state = {
            "entities": {
                "budget": {"value": "50000", "confidence": 0.85}
            }
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        entity_decisions = [d for d in decisions if "entities" in d.field]
        assert len(entity_decisions) == 1
        assert entity_decisions[0].action == StateTransition.IGNORE
        assert entity_decisions[0].reason == "Value unchanged"
    
    @pytest.mark.asyncio
    async def test_entity_change_medium_confidence_pending(self, graph_engine):
        """Test: Entity changed with medium confidence → PENDING"""
        current_state = {
            "entities": {
                "budget": {"value": "30000", "confidence": 0.90, "confirmed": True}
            }
        }
        proposed_state = {
            "entities": {
                "budget": {"value": "50000", "confidence": 0.65}
            }
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        entity_decisions = [d for d in decisions if "entities" in d.field]
        assert len(entity_decisions) == 1
        assert entity_decisions[0].action == StateTransition.PENDING


class TestTopicTransitions:
    """Test topic transition logic"""
    
    @pytest.mark.asyncio
    async def test_new_topic_high_confidence(self, graph_engine):
        """Test: New topic with high confidence → ADD"""
        current_state = {"topics": {}}
        proposed_state = {
            "topics": {
                "billing": {"value": "billing", "confidence": 0.85}
            }
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        topic_decisions = [d for d in decisions if "topics" in d.field]
        assert len(topic_decisions) == 1
        assert topic_decisions[0].action == StateTransition.ADD
    
    @pytest.mark.asyncio
    async def test_existing_topic_ignore(self, graph_engine):
        """Test: Topic already exists → IGNORE"""
        current_state = {
            "topics": {
                "billing": {"value": "billing", "confidence": 0.90, "confirmed": True}
            }
        }
        proposed_state = {
            "topics": {
                "billing": {"value": "billing", "confidence": 0.85}
            }
        }
        
        decisions = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        topic_decisions = [d for d in decisions if "topics" in d.field]
        assert len(topic_decisions) == 1
        assert topic_decisions[0].action == StateTransition.IGNORE
        assert topic_decisions[0].reason == "Topic already exists"


class TestDeterminism:
    """Test that transitions are deterministic"""
    
    @pytest.mark.asyncio
    async def test_same_input_same_output(self, graph_engine):
        """Test: Same input produces identical transitions"""
        current_state = {
            "intent": {"value": "support_request", "confidence": 0.90},
            "entities": {
                "budget": {"value": "30000", "confidence": 0.85}
            }
        }
        proposed_state = {
            "intent": {"value": "purchase_inquiry", "confidence": 0.92},
            "entities": {
                "budget": {"value": "50000", "confidence": 0.88}
            }
        }
        
        # Run multiple times
        decisions1 = await graph_engine.evaluate_transitions(current_state, proposed_state)
        decisions2 = await graph_engine.evaluate_transitions(current_state, proposed_state)
        decisions3 = await graph_engine.evaluate_transitions(current_state, proposed_state)
        
        # All should be identical
        assert len(decisions1) == len(decisions2) == len(decisions3)
        
        for d1, d2, d3 in zip(decisions1, decisions2, decisions3):
            assert d1.action == d2.action == d3.action
            assert d1.field == d2.field == d3.field
            assert d1.new_value == d2.new_value == d3.new_value


class TestMongoDBOperations:
    """Test MongoDB update operation preparation"""
    
    def test_prepare_add_operation(self, graph_engine):
        """Test: ADD transition creates correct MongoDB operation"""
        decisions = [
            TransitionDecision(
                field="context.intent",
                action=StateTransition.ADD,
                new_value="support_request",
                confidence=0.95,
                reason="New intent with high confidence"
            )
        ]
        
        update_ops, pending_items = graph_engine.prepare_mongodb_updates(decisions)
        
        assert "$set" in update_ops
        assert "context.intent" in update_ops["$set"]
        assert update_ops["$set"]["context.intent"]["value"] == "support_request"
        assert update_ops["$set"]["context.intent"]["confirmed"] is True
    
    def test_prepare_pending_operation(self, graph_engine):
        """Test: PENDING transition creates pending item"""
        decisions = [
            TransitionDecision(
                field="context.entities.budget",
                action=StateTransition.PENDING,
                new_value="50000",
                confidence=0.65,
                reason="Medium confidence"
            )
        ]
        
        update_ops, pending_items = graph_engine.prepare_mongodb_updates(decisions)
        
        assert len(pending_items) == 1
        assert pending_items[0]["field"] == "context.entities.budget"
        assert pending_items[0]["proposed_value"] == "50000"
        assert pending_items[0]["status"] == "needs_review"
    
    def test_prepare_ignore_operation(self, graph_engine):
        """Test: IGNORE transition creates no operations"""
        decisions = [
            TransitionDecision(
                field="context.intent",
                action=StateTransition.IGNORE,
                old_value="support_request",
                new_value="support_request",
                confidence=0.85,
                reason="Value unchanged"
            )
        ]
        
        update_ops, pending_items = graph_engine.prepare_mongodb_updates(decisions)
        
        assert len(update_ops) == 0
        assert len(pending_items) == 0


class TestFinalState:
    """Test final state calculation"""
    
    def test_get_final_state_with_changes(self, graph_engine):
        """Test: Final state reflects applied transitions"""
        current_state = {
            "context": {
                "intent": {"value": "support_request", "confidence": 0.90}
            }
        }
        
        decisions = [
            TransitionDecision(
                field="context.intent",
                action=StateTransition.REPLACE,
                old_value="support_request",
                new_value="cancellation",
                confidence=0.92,
                reason="High confidence change"
            ),
            TransitionDecision(
                field="context.entities.budget",
                action=StateTransition.ADD,
                new_value="50000",
                confidence=0.85,
                reason="New entity"
            )
        ]
        
        final_state = graph_engine.get_final_state(current_state, decisions)
        
        assert final_state["context"]["intent"]["value"] == "cancellation"
        assert final_state["context"]["entities"]["budget"]["value"] == "50000"

"""
Integration test for the graph-driven customer memory system.

Tests the full pipeline: conversation ingestion → graph evaluation → profile update
"""

import pytest
from datetime import datetime
from app.services.customer import customer_service
from app.services.ai_service import ai_service


@pytest.mark.asyncio
class TestGraphIntegration:
    """Integration tests for graph-driven pipeline"""
    
    async def test_first_interaction_creates_summary(self):
        """
        Test Case 1: First interaction → summary created
        
        Given: New customer (no existing context)
        When: First conversation ingested
        Then:
            - unified_summary created
            - context.intent set (if high confidence)
            - interaction_history has 1 entry
        """
        customer_id = f"test_customer_{datetime.utcnow().timestamp()}"
        
        # Simulate first conversation
        conversation_data = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "I need help with my billing issue",
            "extracted_context": {
                "topics": {
                    "billing": {"value": "billing", "confidence": 0.85}
                },
                "entities": {}
            },
            "sentiment": "neutral",
            "intent": {"value": "support_request", "confidence": 0.95}
        }
        
        # Ingest conversation
        result = await customer_service.add_conversation(conversation_data)
        
        # Verify customer profile
        customer = await customer_service.get_customer(customer_id)
        
        assert customer is not None
        assert customer["unified_summary"] != ""
        assert len(customer["interaction_history"]) == 1
        
        # Verify context was set
        context = customer.get("context", {})
        assert "intent" in context
        assert context["intent"]["value"] == "support_request"
        assert context["intent"]["confirmed"] is True
        
        # Verify transition logging
        interaction = customer["interaction_history"][0]
        assert "transitions_applied" in interaction
        assert len(interaction["transitions_applied"]) > 0
    
    async def test_preference_update_preserves_old(self):
        """
        Test Case 2: Preference update → old preserved in history, new in profile
        
        Given: Customer with budget = "30k"
        When: New conversation extracts budget = "50k" (high confidence)
        Then:
            - context.entities.budget.value = "50k"
            - context.entities.budget.archived_values contains "30k"
            - interaction_history logs ARCHIVE transition
        """
        customer_id = f"test_customer_{datetime.utcnow().timestamp()}"
        
        # First conversation - set initial budget
        conversation1 = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "My budget is 30k",
            "extracted_context": {
                "entities": {
                    "budget": {"value": "30k", "confidence": 0.90}
                }
            },
            "sentiment": "neutral",
            "intent": {"value": "information_request", "confidence": 0.85}
        }
        
        await customer_service.add_conversation(conversation1)
        
        # Second conversation - update budget
        conversation2 = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "Actually, my budget is now 50k",
            "extracted_context": {
                "entities": {
                    "budget": {"value": "50k", "confidence": 0.88}
                }
            },
            "sentiment": "neutral",
            "intent": {"value": "information_request", "confidence": 0.85}
        }
        
        await customer_service.add_conversation(conversation2)
        
        # Verify customer profile
        customer = await customer_service.get_customer(customer_id)
        
        # Current value should be 50k
        budget_entity = customer["context"]["entities"]["budget"]
        assert budget_entity["value"] == "50k"
        
        # Old value should be archived
        assert "archived_values" in budget_entity
        assert len(budget_entity["archived_values"]) > 0
        assert budget_entity["archived_values"][0]["value"] == "30k"
        
        # Verify transition was logged
        latest_interaction = customer["interaction_history"][-1]
        transitions = latest_interaction["transitions_applied"]
        archive_transition = next(
            (t for t in transitions if t["action"] == "ARCHIVE"),
            None
        )
        assert archive_transition is not None
        assert archive_transition["old_value"] == "30k"
        assert archive_transition["new_value"] == "50k"
    
    async def test_multiple_topics_no_duplication(self):
        """
        Test Case 3: Multiple topics → no duplication
        
        Given: Customer discussed "billing" and "shipping"
        When: Same topics discussed again
        Then:
            - context.topics unchanged (IGNORE transition)
            - No duplicate entries
        """
        customer_id = f"test_customer_{datetime.utcnow().timestamp()}"
        
        # First conversation - discuss billing and shipping
        conversation1 = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "I have billing and shipping issues",
            "extracted_context": {
                "topics": {
                    "billing": {"value": "billing", "confidence": 0.85},
                    "shipping": {"value": "shipping", "confidence": 0.82}
                }
            },
            "sentiment": "negative",
            "intent": {"value": "support_request", "confidence": 0.95}
        }
        
        await customer_service.add_conversation(conversation1)
        
        # Second conversation - same topics
        conversation2 = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "Still having billing and shipping problems",
            "extracted_context": {
                "topics": {
                    "billing": {"value": "billing", "confidence": 0.88},
                    "shipping": {"value": "shipping", "confidence": 0.85}
                }
            },
            "sentiment": "negative",
            "intent": {"value": "support_request", "confidence": 0.92}
        }
        
        await customer_service.add_conversation(conversation2)
        
        # Verify customer profile
        customer = await customer_service.get_customer(customer_id)
        
        # Topics should exist but not be duplicated
        topics = customer["context"]["topics"]
        assert "billing" in topics
        assert "shipping" in topics
        
        # Verify IGNORE transitions were logged
        latest_interaction = customer["interaction_history"][-1]
        transitions = latest_interaction["transitions_applied"]
        ignore_transitions = [t for t in transitions if t["action"] == "IGNORE"]
        assert len(ignore_transitions) >= 2  # Both topics should be ignored
    
    async def test_repeated_info_no_change(self):
        """
        Test Case 4: Repeated same info → no change
        
        Given: Customer with intent = "support_request"
        When: New conversation with same intent (high confidence)
        Then:
            - context.intent unchanged
            - No transition logged (or IGNORE transition)
            - unified_summary not regenerated unnecessarily
        """
        customer_id = f"test_customer_{datetime.utcnow().timestamp()}"
        
        # First conversation
        conversation1 = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "I need support",
            "extracted_context": {},
            "sentiment": "neutral",
            "intent": {"value": "support_request", "confidence": 0.95}
        }
        
        await customer_service.add_conversation(conversation1)
        customer1 = await customer_service.get_customer(customer_id)
        summary1 = customer1["unified_summary"]
        
        # Second conversation - same intent
        conversation2 = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "I still need help",
            "extracted_context": {},
            "sentiment": "neutral",
            "intent": {"value": "support_request", "confidence": 0.92}
        }
        
        await customer_service.add_conversation(conversation2)
        customer2 = await customer_service.get_customer(customer_id)
        
        # Intent should be unchanged
        assert customer2["context"]["intent"]["value"] == "support_request"
        
        # Verify IGNORE transition
        latest_interaction = customer2["interaction_history"][-1]
        transitions = latest_interaction["transitions_applied"]
        intent_transition = next(
            (t for t in transitions if "intent" in t["field"]),
            None
        )
        assert intent_transition is not None
        assert intent_transition["action"] == "IGNORE"
        assert intent_transition["reason"] == "Value unchanged"
    
    async def test_confidence_thresholds(self):
        """
        Test Case 5: Confidence thresholds work correctly
        
        Test HIGH (≥0.80): Auto-accept
        Test MEDIUM (≥0.55): Pending
        Test LOW (<0.55): Ignore
        """
        customer_id = f"test_customer_{datetime.utcnow().timestamp()}"
        
        # High confidence - should be accepted
        conversation_high = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "Test high confidence",
            "extracted_context": {
                "entities": {
                    "high_conf_entity": {"value": "accepted", "confidence": 0.85}
                }
            },
            "sentiment": "neutral",
            "intent": {"value": "test", "confidence": 0.90}
        }
        
        await customer_service.add_conversation(conversation_high)
        customer = await customer_service.get_customer(customer_id)
        
        # High confidence entity should be confirmed
        high_entity = customer["context"]["entities"]["high_conf_entity"]
        assert high_entity["value"] == "accepted"
        assert high_entity["confirmed"] is True
        
        # Medium confidence - should be pending
        conversation_medium = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "Test medium confidence",
            "extracted_context": {
                "entities": {
                    "medium_conf_entity": {"value": "pending", "confidence": 0.65}
                }
            },
            "sentiment": "neutral",
            "intent": {"value": "test", "confidence": 0.90}
        }
        
        await customer_service.add_conversation(conversation_medium)
        customer = await customer_service.get_customer(customer_id)
        
        # Medium confidence entity should be unconfirmed
        medium_entity = customer["context"]["entities"]["medium_conf_entity"]
        assert medium_entity["value"] == "pending"
        assert medium_entity["confirmed"] is False
        
        # Should also be in pending_inference
        pending = customer.get("pending_inference", [])
        assert len(pending) > 0
        assert any(p["field"] == "context.entities.medium_conf_entity" for p in pending)
        
        # Low confidence - should be ignored
        conversation_low = {
            "customer_id": customer_id,
            "channel": "chat",
            "content": "Test low confidence",
            "extracted_context": {
                "entities": {
                    "low_conf_entity": {"value": "ignored", "confidence": 0.45}
                }
            },
            "sentiment": "neutral",
            "intent": {"value": "test", "confidence": 0.90}
        }
        
        await customer_service.add_conversation(conversation_low)
        customer = await customer_service.get_customer(customer_id)
        
        # Low confidence entity should NOT be in context
        assert "low_conf_entity" not in customer["context"].get("entities", {})

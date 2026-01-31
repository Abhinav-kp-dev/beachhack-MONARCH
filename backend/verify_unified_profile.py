import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime
import uuid

# Mock the database to avoid needing MongoDB running locally if possible, 
# but CustomerService uses 'get_mongodb'. 
# If MongoDB is running (which .env implies), we can use it.
# If not, we should mock the whole DB layer.
# Given the user has a "backend" folder, likely MongoDB is expected.
# We will try to use the real logic but mock the AI Service to ensure deterministic input.

from app.services.customer import customer_service
from app.services.ai_service import ai_service

async def test_unified_profile():
    customer_id = f"test_user_{uuid.uuid4().hex[:8]}"
    print(f"Testing with Customer ID: {customer_id}")
    
    # 1. Create customer
    await customer_service.create_or_update_customer(customer_id, {"name": "Test User"})
    
    # 2. Simulate Conversation
    # We mock extract_context to return generic data
    mock_context = {
        "topics": {"tech": {"value": "tech", "confidence": 0.9}},
        "entities": {
            "device_type": {"value": "smart thermostat", "confidence": 0.95, "confirmed": True},
            "budget": {"value": "200", "confidence": 0.9, "confirmed": True}
        },
        "action_items": [],
        "questions": []
    }
    
    # We strip the "confirmed" flags for the input of graph engine usually?
    # Actually graph engine takes proposals.
    # LLM usually returns just values.
    llm_output_mock = {
        "extracted_context": {
            "entity_device_type": {"value": "smart thermostat", "confidence": 0.95},
            "entity_budget": {"value": "200", "confidence": 0.9}
        },
        "intent": {"value": "purchase", "confidence": 0.9},
        "content": "I want to buy a smart thermostat for around 200."
    }
    
    # Wait, the add_conversation flow calls:
    # 1. conversation_data (input) has "extracted_context" ? 
    # Let's check schemas/ingest.py: ConversationResponse has it.
    # But add_conversation takes conversation_data dict.
    # The frontend or API caller usually calls AI service first?
    # In 'app/api/ingest.py', let's check who calls extract_context.
    # If the backend does it, we need to mock where it's called.
    
    # Assuming we pass the extracted context IN
    conversation_data = {
        "customer_id": customer_id,
        "channel": "chat",
        "content": "I want to buy a smart thermostat.",
        "intent": {"value": "purchase", "confidence": 0.9},
        "extracted_context": {
            "entities": {
                "device_type": {"value": "smart thermostat", "confidence": 0.95},
                "budget": {"value": "200", "confidence": 0.9}
            }
        }
    }
    
    print("Adding conversation...")
    # This triggers graph engine -> apply_graph_transitions
    await customer_service.add_conversation(conversation_data)
    
    # 3. Verify Profile
    customer = await customer_service.get_customer(customer_id)
    print("\nCustomer Profile:")
    import json
    # Use default=str for datetime
    print(json.dumps(customer.get("profile", {}), indent=2, default=str))
    
    profile = customer.get("profile", {})
    attrs = profile.get("attributes", {})
    
    # Assertions
    assert "device_type" in attrs, "Should have device_type in profile attributes"
    assert attrs["device_type"]["value"] == "smart thermostat", "Value mismatch"
    assert attrs["device_type"]["source"] == "graph_inference", "Source mistmatch"
    
    assert "vehicle_type" not in attrs, "Should NOT have vehicle_type"
    
    print("\nSUCCESS: Unified profile updated dynamically with non-automotive data!")

if __name__ == "__main__":
    asyncio.run(test_unified_profile())

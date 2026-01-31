import asyncio
import uuid
import json
from app.services.ai_service import ai_service
from app.services.customer import customer_service

async def process_conversation():
    # Read the conversation file
    with open("../test_convo.txt", "r") as f:
        content = f.read()
    
    print("--- Conversation Content ---")
    print(content[:100] + "...")
    print("----------------------------\n")
    
    customer_id = "education_prospect_45e943"
    print(f"Processing for Customer ID: {customer_id}")
    
    # 1. Extract Context (Simulate Ingest API)
    print("Extracting context via LLM...")
    extracted_context = await ai_service.extract_context(content)
    
    # 2. Detect Intent
    print("Detecting intent...")
    intent = await ai_service.detect_intent(content)
    
    # 3. Construct Payload
    conversation_data = {
        "customer_id": customer_id,
        "channel": "chat",
        "content": content,
        "intent": intent,
        "extracted_context": extracted_context,
        "metadata": {"source": "test_script"}
    }
    
    # 4. Add Conversation (triggers Graph Engine -> Profile Update)
    print("Adding conversation to system...")
    await customer_service.add_conversation(conversation_data)
    
    # 5. Fetch Result
    customer = await customer_service.get_customer(customer_id)
    
    print("\n===== FINAL UNIFIED PROFILE =====")
    profile = customer.get("profile", {})
    print(json.dumps(profile, indent=2, default=str))
    
    # Also print summary for context
    print("\n===== UNIFIED SUMMARY =====")
    print(customer.get("unified_summary"))

if __name__ == "__main__":
    asyncio.run(process_conversation())

import asyncio
import uuid
import json
from app.services.ai_service import ai_service
from app.services.customer import customer_service

async def process_conversation():
    # Read the car conversation file
    try:
        with open("../test_car_convo.txt", "r") as f:
            content = f.read()
    except FileNotFoundError:
        # Fallback if running from root
        with open("test_car_convo.txt", "r") as f:
            content = f.read()
    
    print("--- Car Conversation Content ---")
    print(content[:100] + "...")
    print("----------------------------\n")
    
    customer_id = f"car_shopper_{uuid.uuid4().hex[:6]}"
    print(f"Processing for Customer ID: {customer_id}")
    
    # 1. Extract Context (Simulate Ingest API to verify smart sanitation)
    print("Extracting context via LLM...")
    extracted_context = await ai_service.extract_context(content)
    
    # Verify sanitation didn't kill valid fields
    prefs = extracted_context.get("extracted_context", {}).get("preferences", []) # Structure might differ in valid response?
    # Actually extract_context returns {topics, entities, action_items} if using mock fallbacks, 
    # but with use_real_llm=True (implied by .env), extract_context returns what?
    # Ah, extract_context calls _call_llm_api then maps to internal structure.
    # It returns {topics, entities, action_items, questions}
    # Wait, my previous _sanitize_context modification was inside extract_context's mapping block.
    
    print("Detecting intent...")
    intent = await ai_service.detect_intent(content)
    
    conversation_data = {
        "customer_id": customer_id,
        "channel": "chat",
        "content": content,
        "intent": intent,
        "extracted_context": extracted_context,
        "metadata": {"source": "test_script_car"}
    }
    
    print("Adding conversation to system...")
    await customer_service.add_conversation(conversation_data)
    
    customer = await customer_service.get_customer(customer_id)
    
    print("\n===== FINAL UNIFIED PROFILE (CAR SHOPPER) =====")
    profile = customer.get("profile", {})
    print(json.dumps(profile, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(process_conversation())

import asyncio
from app.services.ai_service import ai_service

async def test_extraction():
    # Test 1: Generic non-automotive input
    text = "I am looking for a gaming laptop with 32GB RAM and my budget is around $2000. I need it by next Friday."
    
    print(f"Input: {text}")
    
    # We are testing the mock implementation primarily if LLM is disabled, 
    # but the logic I changed was in _extract_entities which is the fallback.
    # If use_real_llm is True in settings, it will hit the API. 
    # I'll force it to check the local logic by calling _extract_entities directly or ensuring we check the result.
    
    # Direct check of internal method (the one we changed)
    entities = ai_service._extract_entities(text)
    print("\nExtracted Entities (Fallback Logic):")
    print(entities)
    
    # Assertions
    assert "vehicle_type" not in entities, "Should not detect vehicle_type"
    assert "fuel_type" not in entities, "Should not detect fuel_type"
    
    # Check if generic things are caught
    if "mentioned_amounts" in entities:
        print("SUCCESS: Detected amount genericallly")
    
    # Test 2: Automotive input (should NOT trigger hardcoded rules anymore)
    text_car = "I want a red Toyota Camry."
    entities_car = ai_service._extract_entities(text_car)
    print(f"\nInput: {text_car}")
    print("Extracted Entities (Fallback Logic):")
    print(entities_car)
    
    assert "car_brands" not in entities_car, "Should removed hardcoded brand detection"
    assert "car_color" not in entities_car, "Should removed hardcoded color detection"

if __name__ == "__main__":
    asyncio.run(test_extraction())

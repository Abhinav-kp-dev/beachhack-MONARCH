import asyncio
import httpx
import json

API_URL = "http://localhost:8000/api/v1/ingest/conversation"

async def test_dynamic_preferences():
    # Test Case 1: Laptops (Tech Domain)
    laptop_content = """
    I'm looking for a new laptop for gaming and coding. 
    I need at least 32GB of RAM and an RTX 4080 GPU. 
    My budget is around $2500 but I can stretch to $3000 if needed.
    Screen size should be 16 inches.
    """
    
    payload = {
        "customer_id": "test_dynamic_user_01",
        "channel": "chat",
        "content": laptop_content
    }
    
    print("\n--- Testing Laptop Context ---")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=payload, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                print("Status: SUCCESS")
                print("Extracted Context:")
                print(json.dumps(data.get("extracted_context", {}), indent=2))
            else:
                print(f"Status: FAILED ({response.status_code})")
                print(response.text)
        except Exception as e:
            print(f"Error: {e}")

    # Test Case 2: Travel (Service Domain)
    travel_content = """
    I want to plan a trip to Japan for 2 weeks in April.
    I prefer staying in ryokans and my budget is flexible.
    I want to visit Kyoto and Tokyo.
    Dietary restriction: Vegetarian.
    """
    
    payload_travel = {
        "customer_id": "test_dynamic_user_02",
        "channel": "chat",
        "content": travel_content
    }
    
    print("\n--- Testing Travel Context ---")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=payload_travel, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                print("Status: SUCCESS")
                print("Extracted Context:")
                print(json.dumps(data.get("extracted_context", {}), indent=2))
            else:
                print(f"Status: FAILED ({response.status_code})")
                print(response.text)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_dynamic_preferences())

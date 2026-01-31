import asyncio
import httpx
import json

# URL from .env (hardcoded for test)
API_URL = "http://192.168.220.76:8000/conversation"

async def test_llm(task_name, text):
    payload = {
        "customer_id": "probe_test",
        "channel": "internal",
        "text": text
    }
    if task_name:
        payload["task"] = task_name
        
    print(f"\n--- Testing task='{task_name}' ---")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(API_URL, json=payload)
            if resp.status_code == 200:
                print("Response:")
                print(json.dumps(resp.json(), indent=2))
            else:
                print(f"Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Failed: {e}")

async def main():
    non_car_text = "I need a gaming laptop, budget $2000."
    
    # Test 1: No task (default) - likely what extract_context does now
    # Wait, extract_context does NOT send 'task' param in current code!
    await test_llm(None, non_car_text)
    
    # Test 2: explicit extraction tasks
    await test_llm("extraction", non_car_text)
    await test_llm("extract_context", non_car_text)
    await test_llm("profile", non_car_text)
    await test_llm("general_extraction", non_car_text)

if __name__ == "__main__":
    asyncio.run(main())

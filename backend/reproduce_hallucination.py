import asyncio
import httpx
import json

API_URL = "http://192.168.220.76:8000/conversation"

async def test_extraction():
    # Read the full conversation
    with open("../test_convo.txt", "r") as f:
        content = f.read()
    
    print(f"Content length: {len(content)}")
    
    # Test 1: Default (No task) - Current behavior
    print("\n--- Testing DEFAULT (No task) ---")
    payload = {
        "customer_id": "test_debug",
        "channel": "internal",
        "text": content
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(API_URL, json=payload)
        data = resp.json()
        prefs = data.get("extracted_context", {}).get("preferences", [])
        print("Preferences:", json.dumps(prefs, indent=2))
        
    # Test 2: With task="profile"
    print("\n--- Testing TASK='profile' ---")
    payload["task"] = "profile"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(API_URL, json=payload)
        data = resp.json()
        prefs = data.get("extracted_context", {}).get("preferences", [])
        print("Preferences:", json.dumps(prefs, indent=2))
        
    # Test 4: With Prompt Injection
    print("\n--- Testing PROMPT INJECTION ---")
    prompt = "Context: General Inquiry. Extract valid preferences only. Do not assume automotive context.\n\n"
    payload = {
        "customer_id": "test_debug",
        "channel": "internal",
        "text": prompt + content
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(API_URL, json=payload)
        data = resp.json()
        prefs = data.get("extracted_context", {}).get("preferences", [])
        print("Preferences:", json.dumps(prefs, indent=2))

if __name__ == "__main__":
    asyncio.run(test_extraction())

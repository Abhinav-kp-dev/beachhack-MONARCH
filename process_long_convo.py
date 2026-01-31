
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8001"
CUSTOMER_ID = "car_buyer_complex_002"

async def process_conversation():
    # Read the conversation file
    with open("test_convo.txt", "r") as f:
        content = f.read()

    print(f"Reading conversation ({len(content)} bytes)...")

    # Payload
    payload = {
        "customer_id": CUSTOMER_ID,
        "channel": "chat",
        "content": content
    }

    async with httpx.AsyncClient() as client:
        # 1. Send conversation
        print(f"Sending conversation for {CUSTOMER_ID}...")
        response = await client.post(f"{BASE_URL}/conversation", json=payload)
        
        if response.status_code == 200:
            print("Conversation processed successfully!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        # 2. Get Context
        print("\nRetrieving Unified Profile...")
        context_response = await client.get(f"{BASE_URL}/customer/{CUSTOMER_ID}/context")
        if context_response.status_code == 200:
            print(json.dumps(context_response.json(), indent=2))
        else:
            print(f"Error retrieving context: {context_response.status_code}")

if __name__ == "__main__":
    asyncio.run(process_conversation())

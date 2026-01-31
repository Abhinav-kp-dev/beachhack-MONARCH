
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8001"
import sys

async def process_conversation():
    # 1. Check command line arguments first
    customer_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 2. Read the conversation file
    with open("test_convo.txt", "r") as f:
        content = f.read()
    
    # 3. If ID not provided in args, try to extract from file content
    if not customer_id:
        lines = content.splitlines()
        for i, line in enumerate(lines[:20]):
            clean_line = line.strip().lower()
            if "customer_id" in clean_line and i + 1 < len(lines):
                # Take the next line as the ID
                potential_id = lines[i+1].strip().replace('"', '').replace("'", "")
                if potential_id:
                    customer_id = potential_id
                    break
    
    # Final fallback
    if not customer_id:
        customer_id = "edu_learner_001" # Default to current test case

    print(f"--- Processing Conversation ---")
    print(f"Source: test_convo.txt")
    print(f"Target Customer ID: {customer_id}")
    print(f"-------------------------------")

    # Payload
    payload = {
        "customer_id": customer_id,
        "channel": "chat",
        "content": content
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        # 1. Send conversation
        print(f"Sending request to backend...")
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
        context_response = await client.get(f"{BASE_URL}/customer/{customer_id}/context")
        if context_response.status_code == 200:
            print(json.dumps(context_response.json(), indent=2))
        else:
            print(f"Error retrieving context: {context_response.status_code}")

if __name__ == "__main__":
    asyncio.run(process_conversation())

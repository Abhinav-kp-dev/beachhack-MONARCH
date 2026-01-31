import asyncio
import httpx
import json

API_URL = "http://192.168.220.76:8000/summary"

async def test_summary():
    payload = {
        "customer_id": "probe_test",
        "text": "The customer is interested in a gaming laptop with a budget of $2000. They previously mentioned wanting a high refresh rate screen."
    }
    
    print(f"\n--- Testing summary API ---")
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

if __name__ == "__main__":
    asyncio.run(test_summary())

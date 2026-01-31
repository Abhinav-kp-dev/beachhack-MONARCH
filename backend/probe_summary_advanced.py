import asyncio
import httpx
import json

SUMMARY_URL = "http://192.168.220.76:8000/summary"
CONVO_URL = "http://192.168.220.76:8000/conversation"

async def probe_endpoint(url, payload):
    print(f"\n--- Probing {url} ---")
    print(f"Payload: {payload}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print("Response:")
                print(json.dumps(resp.json(), indent=2))
            else:
                print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Failed: {e}")

async def main():
    text = "The customer is extremely unhappy with the late delivery of their order #12345. They want a refund."
    
    # Try /summary with different formats
    await probe_endpoint(SUMMARY_URL, {"customer_id": "test", "text": text, "channel": "internal"})
    await probe_endpoint(SUMMARY_URL, {"text": text})
    await probe_endpoint(SUMMARY_URL, {"content": text})
    
    # Try /conversation with task="summary"
    await probe_endpoint(CONVO_URL, {"customer_id": "test", "text": text, "channel": "internal", "task": "summary"})

if __name__ == "__main__":
    asyncio.run(main())

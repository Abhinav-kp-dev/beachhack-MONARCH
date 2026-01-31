import httpx
import os
import asyncio

API_URL = "http://192.168.220.76:8000/transcribe"
AUDIO_FILE = "voice_convo.mp3"

async def test_transcription():
    print("Starting transcription test...")
    if not os.path.exists(AUDIO_FILE):
        print(f"File not found: {AUDIO_FILE}")
        files = [f for f in os.listdir('.') if f.endswith('.mp3')]
        print(f"Available MP3s: {files}")
        if files:
            file_to_use = files[0]
        else:
            return
    else:
        file_to_use = AUDIO_FILE

    print(f"Sending {file_to_use} to {API_URL}...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(file_to_use, "rb") as f:
            files = {"file": (os.path.basename(file_to_use), f, "audio/mpeg")}
            resp = await client.post(API_URL, files=files)
        
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Success!")
        print(resp.json())
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_transcription())

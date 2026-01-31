#!/usr/bin/env python3
"""
Audio Transcription Script
Transcribes audio files using the Customer Intelligence System API
"""

import requests
import json
import os
from pathlib import Path

# ============================================================
# CONFIGURATION - Edit these values
# ============================================================
AUDIO_FILE_PATH = "/home/abhishek-reji/Downloads/output2.mp3"  # Path to your audio file
API_URL = "http://192.168.220.76:8000/transcribe"
CUSTOMER_ID = None  # Optional: Set customer ID to link transcript to a customer
# ============================================================


def transcribe_audio(
    audio_file_path: str,
    api_url: str = "http://192.168.220.76:8000/transcribe",
    customer_id: str = None
) -> dict:
    """
    Transcribe an audio file to text using the Whisper API.
    
    Args:
        audio_file_path: Path to the audio file (WAV, MP3, etc.)
        api_url: API endpoint URL
        customer_id: Optional customer ID to create conversation from transcript
    
    Returns:
        dict: Transcription result with transcript text and metadata
    """
    # Validate file exists
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    # Get file extension for content type
    file_ext = Path(audio_file_path).suffix.lower()
    content_types = {
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.webm': 'audio/webm',
    }
    content_type = content_types.get(file_ext, 'audio/wav')
    
    # Prepare the file for upload
    filename = os.path.basename(audio_file_path)
    
    with open(audio_file_path, 'rb') as audio_file:
        files = {
            'file': (filename, audio_file, content_type)
        }
        
        # Add customer_id as query parameter if provided
        params = {}
        if customer_id:
            params['customer_id'] = customer_id
        
        print(f"Transcribing: {audio_file_path}")
        print(f"File size: {os.path.getsize(audio_file_path) / 1024:.2f} KB")
        print(f"Sending to: {api_url}")
        print("-" * 50)
        
        # Make the API request
        response = requests.post(api_url, files=files, params=params)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            raise Exception(f"API Error ({response.status_code}): {response.text}")


def main():
    """Main function - reads audio file path from config and transcribes"""
    
    # Check if file exists
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"❌ Error: Audio file not found!")
        print(f"   Path: {AUDIO_FILE_PATH}")
        print(f"\n📝 Edit AUDIO_FILE_PATH at the top of this script to set your audio file path.")
        return
    
    try:
        result = transcribe_audio(AUDIO_FILE_PATH, api_url=API_URL, customer_id=CUSTOMER_ID)
        
        print("✅ Transcription Complete!")
        print("=" * 50)
        
        if 'transcript' in result:
            print(f"\n📝 Transcript:\n{result['transcript']}")
        
        if 'confidence' in result:
            print(f"\n🎯 Confidence: {result['confidence']:.2%}")
        
        if 'duration' in result:
            print(f"⏱️  Duration: {result['duration']:.2f} seconds")
        
        if 'duration_seconds' in result:
            print(f"⏱️  Duration: {result['duration_seconds']:.2f} seconds")
        
        if 'language' in result:
            print(f"🌐 Language: {result['language']}")
        
        if 'conversation_id' in result:
            print(f"\n💬 Conversation ID: {result['conversation_id']}")
            print(f"👤 Customer ID: {result.get('customer_id', 'N/A')}")
        
        print("\n" + "=" * 50)
        print("Full Response:")
        print(json.dumps(result, indent=2))
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

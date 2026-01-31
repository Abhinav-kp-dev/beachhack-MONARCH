#!/usr/bin/env python3
"""
Conversation Ingestion Script
Ingests customer conversations using the Customer Intelligence System API
Reads conversation text from a file called 'conversation.txt'
"""

import requests
import json
import os

# Configuration
INPUT_FILE = "conversation.txt"  # Text file to read conversation from
API_URL = "http://192.168.220.76:8000/conversation"
CHANNEL = "chat"  # Options: 'chat', 'email', 'call'

# Optional customer details (set to None if not needed)
CUSTOMER_ID = None
CUSTOMER_NAME = None
CUSTOMER_EMAIL = None
CUSTOMER_PHONE = None


def ingest_conversation(
    text: str,
    channel: str = "chat",
    customer_id: str = None,
    customer_name: str = None,
    customer_email: str = None,
    customer_phone: str = None,
    api_url: str = "http://192.168.220.76:8000/conversation"
) -> dict:
    """
    Ingest a customer conversation to extract context and store in memory.
    
    Args:
        text: The conversation text/transcript
        channel: Communication channel - 'chat', 'email', or 'call'
        customer_id: Optional customer ID (auto-generated if not provided)
        customer_name: Optional customer name
        customer_email: Optional customer email
        customer_phone: Optional customer phone
        api_url: API endpoint URL
    
    Returns:
        dict: Response with extracted context, sentiment, intent, and recommended action
    """
    payload = {
        "channel": channel,
        "text": text
    }
    
    # Add optional fields if provided
    if customer_id:
        payload["customer_id"] = customer_id
    if customer_name:
        payload["customer_name"] = customer_name
    if customer_email:
        payload["customer_email"] = customer_email
    if customer_phone:
        payload["customer_phone"] = customer_phone
    
    print(f"Ingesting conversation...")
    print(f"Channel: {channel}")
    print(f"Text length: {len(text)} characters")
    print("-" * 50)
    
    response = requests.post(
        api_url,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error ({response.status_code}): {response.text}")


def main():
    """Main function - reads from text file and ingests conversation"""
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, INPUT_FILE)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File '{INPUT_FILE}' not found!")
        print(f"   Expected location: {file_path}")
        print(f"\n📝 Please create '{INPUT_FILE}' with your conversation text.")
        print("   Example content:")
        print("   ---")
        print("   Hi, I need help with my order. It hasn't arrived yet.")
        print("   ---")
        return
    
    # Read the text file
    print(f"📂 Reading from: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    
    if not text:
        print("❌ Error: The text file is empty!")
        return
    
    print(f"📄 Content preview: {text[:100]}{'...' if len(text) > 100 else ''}")
    print("=" * 50)
    
    try:
        result = ingest_conversation(
            text=text,
            channel=CHANNEL,
            customer_id=CUSTOMER_ID,
            customer_name=CUSTOMER_NAME,
            customer_email=CUSTOMER_EMAIL,
            customer_phone=CUSTOMER_PHONE,
            api_url=API_URL
        )
        
        print("✅ Conversation Ingested Successfully!")
        print("=" * 50)
        
        print(f"\n🆔 Conversation ID: {result.get('conversation_id', 'N/A')}")
        print(f"👤 Customer ID: {result.get('customer_id', 'N/A')}")
        
        context = result.get('extracted_context', {})
        print(f"\n📊 Extracted Context:")
        print(f"   Intent: {context.get('intent', 'N/A')}")
        print(f"   Sentiment: {context.get('sentiment', 'N/A')}")
        print(f"   Urgency: {context.get('urgency', 'N/A')}")
        
        issues = context.get('issues', [])
        if issues:
            print(f"   Issues: {', '.join(issues)}")
        
        print(f"\n🎯 Recommended Action: {result.get('recommended_action', 'N/A')}")
        print(f"   Next Best Action: {context.get('next_best_action', 'N/A')}")
        
        memory = result.get('memory_status', {})
        if memory:
            print(f"\n💾 Memory Status: {memory.get('status', 'N/A')}")
        
        print("\n" + "=" * 50)
        print("Full Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

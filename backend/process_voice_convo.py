import asyncio
import os
import json
from app.services.ai_service import ai_service
from app.services.customer import customer_service

async def process_voice_conversation():
    # Audio file renamed for reliability
    audio_path = "../voice_convo.mp3"
    
    if not os.path.exists(audio_path):
        print(f"❌ Error: Audio file not found at {audio_path}")
        return

    print("--- 🎙️ Step 1: Transcribing Voice Call ---")
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    
    transcription = await ai_service.transcribe_audio(audio_data)
    transcript = transcription.get("transcript", "")
    
    if not transcript or "[Transcription Error]" in transcript:
        print("❌ Transcription failed.")
        return

    print(f"\n📝 Transcript:\n{transcript[:200]}...")
    print("-" * 30)

    print("\n--- 🧠 Step 2: Extracting Context & Updating Profile ---")
    
    # NEW: We must extract context BEFORE calling add_conversation
    print("AI is extracting context from transcript...")
    extracted_context = await ai_service.extract_context(transcript)
    sentiment = await ai_service.analyze_sentiment(transcript)
    intent = await ai_service.detect_intent(transcript)
    
    customer_id = "cust_mira_voice_test"
    
    conversation_data = {
        "customer_id": customer_id,
        "channel": "call",
        "content": transcript,
        "agent_id": "ai_bot_01",
        "extracted_context": extracted_context,
        "sentiment": sentiment,
        "intent": intent,
        "metadata": {"source": "voice_convo.mp3"}
    }
    
    # Store conversation (this triggers Graph Engine)
    await customer_service.add_conversation(conversation_data)
    
    print("\n✅ Conversation processed and stored successfully.")
    
    print("\n--- 👤 Step 3: Fetching Final Unified Profile ---")
    customer = await customer_service.get_customer(customer_id)
    
    if customer:
        print("\n===== FINAL UNIFIED PROFILE (MIRA) =====")
        profile = customer.get("profile", {})
        print(json.dumps(profile, indent=2))
        
        # If profile is empty, print the whole customer for debugging
        if not profile.get("attributes"):
            print("\n[DEBUG] Profile attributes empty. Full customer object:")
            
            def json_serial(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError("Type not serializable")
                
            debug_cust = {k: v for k, v in customer.items() if k not in ["interaction_history", "conversation_summaries"]}
            print(json.dumps(debug_cust, indent=2, default=json_serial))
        
        print("\n===== UNIFIED SUMMARY =====")
        print(customer.get("unified_summary", "No summary generated."))
    else:
        print("❌ Customer not found after update.")

if __name__ == "__main__":
    # Ensure event loop handles the async operations
    asyncio.run(process_voice_conversation())

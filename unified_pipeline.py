#!/usr/bin/env python3
"""
Unified Customer Profile Pipeline v2
- Separate collections for customers and conversations
- Auto-generates customer ID if not provided
- Updates customer profile after each conversation
- Stores each conversation as a new document
"""

import requests
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient

# ============================================================
# CONFIGURATION - Edit these values
# ============================================================

# Audio file to process
AUDIO_FILE_PATH = "/home/abhishek-reji/Downloads/output2.mp3"

# API endpoints
API_BASE_URL = "http://192.168.220.76:8000"
TRANSCRIBE_URL = f"{API_BASE_URL}/transcribe"
CONVERSATION_URL = f"{API_BASE_URL}/conversation"

# MongoDB Configuration
MONGODB_URI = "mongodb://localhost:27017"
DATABASE_NAME = "customer_intelligence"

# Customer details (optional - set CUSTOMER_ID to link to existing customer)
CUSTOMER_ID = "a294fbed-2561-4f3e-8d88-f629368119a4"  # Set to existing ID to update, or None to create new
CUSTOMER_NAME = None
CUSTOMER_EMAIL = None
CUSTOMER_PHONE = None
CHANNEL = "call"  # Options: 'chat', 'email', 'call'

# ============================================================


class CustomerDatabase:
    """Handles all MongoDB operations for customers and conversations"""
    
    def __init__(self, mongodb_uri: str, database_name: str):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[database_name]
        self.customers = self.db["customers"]
        self.conversations = self.db["conversations"]
        
        # Create indexes for faster lookups
        self.customers.create_index("customer_id", unique=True)
        self.conversations.create_index("customer_id")
        self.conversations.create_index("conversation_id", unique=True)
        
        print(f"✅ Connected to MongoDB: {database_name}")
        print(f"   📁 Collections: customers, conversations")
    
    def generate_customer_id(self) -> str:
        """Generate a new unique customer ID"""
        return f"CUST-{uuid.uuid4().hex[:8].upper()}"
    
    def customer_exists(self, customer_id: str) -> bool:
        """Check if a customer exists"""
        return self.customers.find_one({"customer_id": customer_id}) is not None
    
    def get_customer(self, customer_id: str) -> dict:
        """Get customer by ID"""
        customer = self.customers.find_one({"customer_id": customer_id})
        if customer:
            customer["_id"] = str(customer["_id"])
        return customer
    
    def create_customer(
        self,
        customer_id: str = None,
        name: str = None,
        email: str = None,
        phone: str = None
    ) -> dict:
        """Create a new customer profile"""
        if not customer_id:
            customer_id = self.generate_customer_id()
        
        customer = {
            "customer_id": customer_id,
            "name": name,
            "email": email,
            "phone": phone,
            "total_conversations": 0,
            "first_contact": datetime.utcnow(),
            "last_contact": datetime.utcnow(),
            "preferred_channel": None,
            "sentiment_history": [],
            "all_issues": [],
            "all_preferences": [],
            "all_commitments": [],
            "relationship_score": 50.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        self.customers.insert_one(customer)
        print(f"   ✅ Created new customer: {customer_id}")
        return customer
    
    def update_customer_from_conversation(
        self,
        customer_id: str,
        extracted_context: dict,
        channel: str,
        name: str = None,
        email: str = None,
        phone: str = None
    ) -> dict:
        """Update customer profile after a conversation"""
        
        # Get signals from extracted context
        signals = extracted_context.get("signals", {})
        sentiment = signals.get("sentiment", "neutral")
        issues = extracted_context.get("issues", [])
        preferences = extracted_context.get("preferences", [])
        commitments = extracted_context.get("commitments", [])
        
        # Build update operations
        update_ops = {
            "$inc": {"total_conversations": 1},
            "$set": {
                "last_contact": datetime.utcnow(),
                "preferred_channel": channel,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "sentiment_history": {
                    "sentiment": sentiment,
                    "timestamp": datetime.utcnow()
                }
            },
            "$addToSet": {
                "all_issues": {"$each": issues},
                "all_preferences": {"$each": preferences},
                "all_commitments": {"$each": commitments}
            }
        }
        
        # Update name/email/phone if provided
        if name:
            update_ops["$set"]["name"] = name
        if email:
            update_ops["$set"]["email"] = email
        if phone:
            update_ops["$set"]["phone"] = phone
        
        # Calculate relationship score based on sentiment
        sentiment_scores = {"positive": 10, "neutral": 0, "negative": -10}
        score_change = sentiment_scores.get(sentiment, 0)
        
        self.customers.update_one(
            {"customer_id": customer_id},
            update_ops
        )
        
        # Update relationship score separately (clamp between 0-100)
        self.customers.update_one(
            {"customer_id": customer_id},
            [
                {
                    "$set": {
                        "relationship_score": {
                            "$min": [100, {"$max": [0, {"$add": ["$relationship_score", score_change]}]}]
                        }
                    }
                }
            ]
        )
        
        print(f"   ✅ Updated customer profile: {customer_id}")
        return self.get_customer(customer_id)
    
    def add_conversation(
        self,
        customer_id: str,
        conversation_id: str,
        channel: str,
        transcript: str,
        language: str,
        extracted_context: dict,
        recommended_action: dict,
        source_file: str = None
    ) -> dict:
        """Add a new conversation to the conversations collection"""
        
        conversation = {
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "channel": channel,
            "transcript": transcript,
            "language": language,
            "extracted_context": extracted_context,
            "recommended_action": recommended_action,
            "source": {
                "type": "audio" if source_file else "text",
                "file": source_file
            },
            "created_at": datetime.utcnow()
        }
        
        self.conversations.insert_one(conversation)
        print(f"   ✅ Stored conversation: {conversation_id}")
        return conversation
    
    def get_customer_conversations(self, customer_id: str) -> list:
        """Get all conversations for a customer"""
        conversations = list(self.conversations.find(
            {"customer_id": customer_id}
        ).sort("created_at", -1))
        
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
        
        return conversations
    
    def get_all_customers(self) -> list:
        """Get all customers"""
        customers = list(self.customers.find())
        for c in customers:
            c["_id"] = str(c["_id"])
        return customers
    
    def get_all_conversations(self) -> list:
        """Get all conversations"""
        conversations = list(self.conversations.find().sort("created_at", -1))
        for c in conversations:
            c["_id"] = str(c["_id"])
        return conversations
    
    def close(self):
        self.client.close()


class CustomerProfilePipeline:
    """Unified pipeline for audio transcription, ingestion, and storage"""
    
    def __init__(self, mongodb_uri: str, database_name: str):
        self.db = CustomerDatabase(mongodb_uri, database_name)
    
    def transcribe_audio(self, audio_file_path: str) -> dict:
        """Step 1: Transcribe audio file to text"""
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
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
        filename = os.path.basename(audio_file_path)
        
        print(f"\n📁 Step 1: Transcribing Audio")
        print(f"   File: {audio_file_path}")
        print(f"   Size: {os.path.getsize(audio_file_path) / 1024:.2f} KB")
        
        with open(audio_file_path, 'rb') as audio_file:
            files = {'file': (filename, audio_file, content_type)}
            response = requests.post(TRANSCRIBE_URL, files=files)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Transcription complete!")
                print(f"   📝 Transcript: {result.get('transcript', '')[:100]}...")
                return result
            else:
                raise Exception(f"Transcription failed: {response.text}")
    
    def ingest_conversation(
        self, 
        text: str, 
        channel: str = "chat",
        customer_id: str = None,
        customer_name: str = None,
        customer_email: str = None,
        customer_phone: str = None
    ) -> dict:
        """Step 2: Ingest transcription to extract context"""
        print(f"\n💬 Step 2: Ingesting Conversation")
        print(f"   Channel: {channel}")
        print(f"   Text length: {len(text)} characters")
        
        payload = {
            "channel": channel,
            "text": text
        }
        
        if customer_id:
            payload["customer_id"] = customer_id
        if customer_name:
            payload["customer_name"] = customer_name
        if customer_email:
            payload["customer_email"] = customer_email
        if customer_phone:
            payload["customer_phone"] = customer_phone
        
        response = requests.post(
            CONVERSATION_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Ingestion complete!")
            print(f"   🆔 Conversation ID: {result.get('conversation_id', 'N/A')}")
            return result
        else:
            raise Exception(f"Ingestion failed: {response.text}")
    
    def run_pipeline(
        self,
        audio_file_path: str,
        customer_id: str = None,
        customer_name: str = None,
        customer_email: str = None,
        customer_phone: str = None,
        channel: str = "call"
    ) -> dict:
        """
        Run the complete pipeline:
        1. Transcribe audio
        2. Ingest conversation (extract context)
        3. Check/Create customer in database
        4. Store conversation
        5. Update customer profile
        """
        print("=" * 60)
        print("🚀 Starting Unified Customer Profile Pipeline v2")
        print("=" * 60)
        
        # Step 1: Transcribe
        transcription = self.transcribe_audio(audio_file_path)
        transcript_text = transcription.get("transcript", "")
        language = transcription.get("language", "en")
        
        if not transcript_text:
            raise Exception("Transcription returned empty text")
        
        # Step 2: Ingest conversation
        ingestion = self.ingest_conversation(
            text=transcript_text,
            channel=channel,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone
        )
        
        # Get IDs from ingestion result
        conv_customer_id = ingestion.get("customer_id")
        conversation_id = ingestion.get("conversation_id", str(uuid.uuid4()))
        extracted_context = ingestion.get("extracted_context", {})
        recommended_action = ingestion.get("recommended_action", {})
        
        # Step 3: Check/Create customer
        print(f"\n👤 Step 3: Managing Customer Profile")
        
        # Determine customer ID to use
        final_customer_id = customer_id or conv_customer_id
        
        if final_customer_id and self.db.customer_exists(final_customer_id):
            print(f"   Found existing customer: {final_customer_id}")
        else:
            # Create new customer
            if not final_customer_id:
                final_customer_id = self.db.generate_customer_id()
            
            self.db.create_customer(
                customer_id=final_customer_id,
                name=customer_name,
                email=customer_email,
                phone=customer_phone
            )
        
        # Step 4: Store conversation
        print(f"\n💾 Step 4: Storing Conversation")
        self.db.add_conversation(
            customer_id=final_customer_id,
            conversation_id=conversation_id,
            channel=channel,
            transcript=transcript_text,
            language=language,
            extracted_context=extracted_context,
            recommended_action=recommended_action,
            source_file=audio_file_path
        )
        
        # Step 5: Update customer profile
        print(f"\n📊 Step 5: Updating Customer Profile")
        updated_customer = self.db.update_customer_from_conversation(
            customer_id=final_customer_id,
            extracted_context=extracted_context,
            channel=channel,
            name=customer_name,
            email=customer_email,
            phone=customer_phone
        )
        
        print("\n" + "=" * 60)
        print("✅ Pipeline Complete!")
        print("=" * 60)
        
        return {
            "customer_id": final_customer_id,
            "conversation_id": conversation_id,
            "customer_profile": updated_customer,
            "transcript": transcript_text,
            "extracted_context": extracted_context,
            "recommended_action": recommended_action
        }
    
    def close(self):
        self.db.close()


def print_database_summary(db: CustomerDatabase):
    """Print summary of all data in the database"""
    print("\n" + "=" * 60)
    print("📊 DATABASE SUMMARY")
    print("=" * 60)
    
    customers = db.get_all_customers()
    conversations = db.get_all_conversations()
    
    print(f"\n👥 CUSTOMERS TABLE ({len(customers)} records)")
    print("-" * 40)
    for c in customers:
        print(f"  ID: {c['customer_id']}")
        print(f"    Name: {c.get('name', 'N/A')}")
        print(f"    Email: {c.get('email', 'N/A')}")
        print(f"    Total Conversations: {c.get('total_conversations', 0)}")
        print(f"    Relationship Score: {c.get('relationship_score', 0):.1f}")
        print(f"    Last Contact: {c.get('last_contact', 'N/A')}")
        print()
    
    print(f"\n💬 CONVERSATIONS TABLE ({len(conversations)} records)")
    print("-" * 40)
    for conv in conversations:
        print(f"  Conversation ID: {conv['conversation_id']}")
        print(f"    Customer ID: {conv['customer_id']}")
        print(f"    Channel: {conv.get('channel', 'N/A')}")
        print(f"    Transcript: {conv.get('transcript', '')[:60]}...")
        signals = conv.get('extracted_context', {}).get('signals', {})
        print(f"    Sentiment: {signals.get('sentiment', 'N/A')}")
        print(f"    Intent: {signals.get('intent', 'N/A')}")
        print(f"    Created: {conv.get('created_at', 'N/A')}")
        print()


def main():
    """Main function - runs the complete pipeline"""
    
    # Check if audio file exists
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"❌ Error: Audio file not found!")
        print(f"   Path: {AUDIO_FILE_PATH}")
        print(f"\n📝 Edit AUDIO_FILE_PATH at the top of this script.")
        return
    
    try:
        # Initialize pipeline
        pipeline = CustomerProfilePipeline(
            mongodb_uri=MONGODB_URI,
            database_name=DATABASE_NAME
        )
        
        # Run the pipeline
        result = pipeline.run_pipeline(
            audio_file_path=AUDIO_FILE_PATH,
            customer_id=CUSTOMER_ID,
            customer_name=CUSTOMER_NAME,
            customer_email=CUSTOMER_EMAIL,
            customer_phone=CUSTOMER_PHONE,
            channel=CHANNEL
        )
        
        # Print results
        print("\n📋 PIPELINE RESULT:")
        print("-" * 40)
        print(f"Customer ID: {result['customer_id']}")
        print(f"Conversation ID: {result['conversation_id']}")
        print(f"\nTranscript: {result['transcript']}")
        
        context = result.get('extracted_context', {})
        signals = context.get('signals', {})
        print(f"\nExtracted Context:")
        print(f"  Intent: {signals.get('intent', 'N/A')}")
        print(f"  Sentiment: {signals.get('sentiment', 'N/A')}")
        print(f"  Urgency: {signals.get('urgency', 'N/A')}")
        print(f"  Issues: {context.get('issues', [])}")
        
        print(f"\nRecommended Action: {result.get('recommended_action', 'N/A')}")
        
        # Print database summary
        print_database_summary(pipeline.db)
        
        # Close connection
        pipeline.close()
        
    except Exception as e:
        print(f"❌ Pipeline Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

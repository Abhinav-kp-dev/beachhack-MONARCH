
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys

# Connect to MongoDB
# Using the standard URI as per config
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "customer_intelligence"

async def verify_storage():
    # 1. Check for ID in command line arguments
    customer_id = sys.argv[1] if len(sys.argv) > 1 else "edu_learner_001"
    
    print(f"Connecting to {MONGO_URI}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    print(f"Querying for customer_id: {customer_id}")
    
    customer = await db.customers.find_one({"customer_id": customer_id})
    
    if customer:
        print("\n✅ Customer Found in Database!")
        print("-" * 40)
        print(f"ID: {customer.get('customer_id')}")
        print(f"Context Entities (Raw DB State):")
        
        entities = customer.get("context", {}).get("entities", {})
        import json
        print(json.dumps(entities, indent=2))
        
        print("\nRoot Preferences (Synced):")
        print(json.dumps(customer.get("preferences", {}), indent=2))
        
        print("\nUnified Summary:")
        print(customer.get("unified_summary"))
        
        print("\nInteraction History (Summaries):")
        for interaction in customer.get("interaction_history", []):
            print(f"- {interaction.get('timestamp')}: {interaction.get('summary')}")
            
        print("\nConversation Summaries List:")
        for summary in customer.get("conversation_summaries", []):
            print(f"- {summary.get('timestamp')}: {summary.get('summary')}")
            
        print("-" * 40)
    else:
        print("\n❌ Customer NOT found in Database.")

    print(f"\nQuerying for conversations with customer_id: {customer_id}")
    conversations_cursor = db.conversations.find({"customer_id": customer_id})
    conversations = await conversations_cursor.to_list(length=10)
    
    if conversations:
        print(f"✅ Found {len(conversations)} conversations!")
        for conv in conversations:
            print(f"- ID: {conv.get('conversation_id')}")
            print(f"  Snippet: {conv.get('content')[:50]}...")
    else:
        print("❌ No conversations found using filter {'customer_id': '" + customer_id + "'}")
        
        # Debug: Check all conversations to see if ID format is different
        print("\nDebug: Listing ALL conversations in DB (first 5):")
        all_convs = await db.conversations.find({}).to_list(length=5)
        for conv in all_convs:
            print(f"- CustID: {conv.get('customer_id')} | Content: {conv.get('content')[:30]}...")

if __name__ == "__main__":
    asyncio.run(verify_storage())

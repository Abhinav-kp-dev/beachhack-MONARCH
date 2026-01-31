from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

# In-memory storage for demo purposes
_customers_db: Dict[str, Dict[str, Any]] = {}
_conversations_db: Dict[str, Dict[str, Any]] = {}


class CustomerService:
    """Service for customer data management"""
    
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        return _customers_db.get(customer_id)
    
    async def create_or_update_customer(self, customer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update customer"""
        if customer_id in _customers_db:
            _customers_db[customer_id].update(data)
            _customers_db[customer_id]["updated_at"] = datetime.utcnow().isoformat()
        else:
            _customers_db[customer_id] = {
                "id": customer_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "total_interactions": 0,
                "topics_discussed": [],
                "sentiment_history": [],
                "pain_points": [],
                "preferences": {},
                "pending_issues": [],
                "resolved_issues": [],
                "key_memories": [],
                "relationship_score": 50.0,
                **data
            }
        return _customers_db[customer_id]
    
    async def get_customer_context(self, customer_id: str) -> Dict[str, Any]:
        """Get full customer context including conversation history"""
        customer = await self.get_customer(customer_id)
        
        if not customer:
            # Return default context for new customer
            return {
                "customer_id": customer_id,
                "name": None,
                "email": None,
                "phone": None,
                "total_interactions": 0,
                "last_interaction": None,
                "preferred_channel": None,
                "topics_discussed": [],
                "sentiment_history": [],
                "pain_points": [],
                "preferences": {},
                "pending_issues": [],
                "resolved_issues": [],
                "key_memories": [],
                "relationship_score": 0.0
            }
        
        # Get conversation history
        conversations = await self.get_customer_conversations(customer_id)
        
        return {
            **customer,
            "conversations": conversations[-10:] if conversations else []  # Last 10 conversations
        }
    
    async def get_customer_conversations(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a customer"""
        return [
            conv for conv in _conversations_db.values() 
            if conv.get("customer_id") == customer_id
        ]
    
    async def add_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new conversation"""
        conv_id = str(uuid.uuid4())
        conversation = {
            "id": conv_id,
            "created_at": datetime.utcnow().isoformat(),
            **conversation_data
        }
        _conversations_db[conv_id] = conversation
        
        # Update customer stats
        customer_id = conversation_data.get("customer_id")
        if customer_id:
            customer = await self.get_customer(customer_id)
            if customer:
                customer["total_interactions"] = customer.get("total_interactions", 0) + 1
                customer["last_interaction"] = datetime.utcnow().isoformat()
                
                # Update topics
                topics = conversation_data.get("extracted_context", {}).get("topics", [])
                existing_topics = customer.get("topics_discussed", [])
                customer["topics_discussed"] = list(set(existing_topics + topics))
                
                # Update sentiment history
                sentiment = conversation_data.get("sentiment")
                if sentiment:
                    customer.setdefault("sentiment_history", []).append({
                        "sentiment": sentiment,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            else:
                await self.create_or_update_customer(customer_id, {})
        
        return conversation
    
    async def update_customer_memory(self, customer_id: str, memory: str) -> Dict[str, Any]:
        """Add a key memory for the customer"""
        customer = await self.get_customer(customer_id)
        if customer:
            customer.setdefault("key_memories", []).append(memory)
            return customer
        return await self.create_or_update_customer(customer_id, {"key_memories": [memory]})


customer_service = CustomerService()

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from app.db.mongodb import get_mongodb

class CustomerService:
    """Service for customer data management using MongoDB"""
    
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        db = await get_mongodb()
        customer = await db.customers.find_one({"customer_id": customer_id})
        if customer:
            customer["_id"] = str(customer["_id"])
        return customer
    
    async def create_or_update_customer(self, customer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update customer"""
        db = await get_mongodb()
        customer = await self.get_customer(customer_id)
        
        if customer:
            update_data = {
                **data,
                "updated_at": datetime.utcnow()
            }
            await db.customers.update_one(
                {"customer_id": customer_id},
                {"$set": update_data}
            )
        else:
            customer_data = {
                "customer_id": customer_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "total_interactions": 0,
                "topics_discussed": [],
                "sentiment_history": [],
                "pain_points": [],
                "preferences": {},
                "pending_issues": [],
                "resolved_issues": [],
                "key_memories": [],
                "relationship_score": 50.0,
                "unified_summary": "",
                "interaction_history": [],
                "conversation_summaries": [],
                **data
            }
            await db.customers.insert_one(customer_data)
        
        return await self.get_customer(customer_id)
    
    async def get_customer_context(self, customer_id: str) -> Dict[str, Any]:
        """Get full customer context including conversation history"""
        customer = await self.get_customer(customer_id)
        
        if not customer:
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
                "relationship_score": 0.0,
                "conversations": []
            }
        
        conversations = await self.get_customer_conversations(customer_id)
        
        return {
            **customer,
            "conversations": conversations[-10:] if conversations else []
        }
    
    async def get_customer_conversations(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a customer"""
        db = await get_mongodb()
        cursor = db.conversations.find({"customer_id": customer_id}).sort("created_at", -1)
        conversations = await cursor.to_list(length=100)
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
        return conversations
    
    async def add_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new conversation using graph-based pipeline.
        
        NEW FLOW:
        1. Store conversation
        2. LLM extracts context (proposals only)
        3. Graph engine evaluates transitions
        4. Apply transitions to customer profile
        5. Generate interaction summary
        6. Update unified summary with final backend state
        7. Log everything in interaction history
        """
        db = await get_mongodb()
        conv_id = str(uuid.uuid4())
        conversation = {
            "id": conv_id,
            "conversation_id": conv_id,
            "created_at": datetime.utcnow(),
            **conversation_data
        }
        await db.conversations.insert_one(conversation)
        
        # Update customer stats and profile using graph engine
        customer_id = conversation_data.get("customer_id")
        if customer_id:
            customer = await self.get_customer(customer_id)
            if not customer:
                customer = await self.create_or_update_customer(customer_id, {})
            
            # Basic stats update
            update_ops = {
                "$inc": {"total_interactions": 1},
                "$set": {
                    "last_interaction": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow()
                }
            }
            
            # Update sentiment history
            sentiment = conversation_data.get("sentiment")
            if sentiment:
                update_ops["$push"] = {
                    "sentiment_history": {
                        "sentiment": sentiment,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            
            await db.customers.update_one({"customer_id": customer_id}, update_ops)
            
            # ===== GRAPH ENGINE PIPELINE =====
            
            # 1. Get LLM proposals (already extracted)
            extracted_context = conversation_data.get("extracted_context", {})
            intent_data = conversation_data.get("intent")
            
            # Combine intent into context for processing
            llm_proposals = {**extracted_context}
            if isinstance(intent_data, dict):
                llm_proposals["intent"] = intent_data
            
            # 2. Get current customer context
            current_context = customer.get("context", {})
            
            # 3. Graph engine evaluates transitions
            from app.services.graph_engine import graph_engine
            
            transition_decisions = await graph_engine.evaluate_transitions(
                current_state=current_context,
                proposed_state=llm_proposals
            )
            
            # 4. Apply transitions to customer profile
            final_state = await self.apply_graph_transitions(
                customer_id=customer_id,
                decisions=transition_decisions
            )
            
            # 5. Generate interaction summary
            from app.services.ai_service import ai_service
            
            interaction_summary = await ai_service.generate_interaction_summary(
                conversation_data.get("content", ""),
                intent_data,
                extracted_context
            )
            
            # 6. Update unified summary with final backend state
            customer = await self.get_customer(customer_id)  # Refresh after transitions
            existing_summary = customer.get("unified_summary", "")
            pending_issues = customer.get("pending_issues", [])
            
            updated_summary = await ai_service.update_unified_summary(
                existing_summary=existing_summary,
                new_interaction_summary=interaction_summary,
                final_backend_state=final_state,
                pending_issues=pending_issues
            )
            
            # 7. Prepare history entries with transition logs
            interaction_record = {
                "interaction_id": conv_id,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": interaction_summary,
                "intent": intent_data.get("value") if isinstance(intent_data, dict) else intent_data,
                "entities_extracted": extracted_context.get("entities", {}),
                "transitions_applied": [d.to_dict() for d in transition_decisions]
            }
            
            conversation_summary_record = {
                "conversation_id": conv_id,
                "summary": interaction_summary,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 8. Update customer with new summary and history
            await db.customers.update_one(
                {"customer_id": customer_id},
                {
                    "$set": {"unified_summary": updated_summary},
                    "$push": {
                        "interaction_history": interaction_record,
                        "conversation_summaries": conversation_summary_record
                    }
                }
            )
        
        # Return conversation with stringified ID for response
        conversation["_id"] = str(conversation["_id"])
        return conversation

    
    
    async def apply_graph_transitions(
        self,
        customer_id: str,
        decisions: List[Any]  # List[TransitionDecision]
    ) -> Dict[str, Any]:
        """
        Apply graph engine transition decisions to customer profile.
        
        This method:
        1. Converts decisions to MongoDB operations
        2. Updates the customer document
        3. Returns the final state for summary generation
        
        Args:
            customer_id: Customer ID
            decisions: List of TransitionDecision objects from graph engine
            
        Returns:
            Final customer context state after transitions
        """
        if not decisions:
            # No transitions - return current state
            customer = await self.get_customer(customer_id)
            return customer.get("context", {})
        
        db = await get_mongodb()
        from app.services.graph_engine import graph_engine
        
        # Prepare MongoDB update operations
        update_ops, pending_items = graph_engine.prepare_mongodb_updates(decisions)
        
        # Apply context updates
        if update_ops:
            # Sync confirmed entities to top-level preferences
            set_ops = update_ops.get("$set", {})
            preferences_updates = {}
            
            for key, value in set_ops.items():
                if key.startswith("context.entities."):
                    # Extract entity name: context.entities.car_type -> car_type
                    entity_name = key.split(".")[-1]
                    
                    # Check if confirmed
                    if isinstance(value, dict) and value.get("confirmed"):
                        preferences_updates[f"preferences.{entity_name}"] = value.get("value")
            
            # Merge into main update
            if preferences_updates:
                if "$set" not in update_ops:
                    update_ops["$set"] = {}
                update_ops["$set"].update(preferences_updates)

            await db.customers.update_one(
                {"customer_id": customer_id},
                update_ops
            )
        
        # Add pending items
        if pending_items:
            await db.customers.update_one(
                {"customer_id": customer_id},
                {"$push": {"pending_inference": {"$each": pending_items}}}
            )
        
        # Get updated customer and return final state
        customer = await self.get_customer(customer_id)
        current_context = customer.get("context", {})
        
        # Calculate final state using graph engine
        final_state = graph_engine.get_final_state(current_context, decisions)
        
        return final_state
    
    async def process_llm_output(self, customer_id: str, llm_output: Dict[str, Any]):
        """
        DEPRECATED: This method is kept for backward compatibility.
        New code should use the graph engine pipeline in add_conversation.
        
        Process LLM output and update profile based on confidence
        """
        
        # Handle simple fields directly if present
        if "intent" in llm_output:
            await self.handle_field(customer_id, "context.intent", llm_output["intent"])
            
        # Handle topics
        topics = llm_output.get("topics", {})
        if isinstance(topics, dict):
            for topic, data in topics.items():
                await self.handle_field(customer_id, f"context.topics.{topic}", data)
                
        # Handle entities
        entities = llm_output.get("entities", {})
        if isinstance(entities, dict):
            for entity_key, data in entities.items():
                await self.handle_field(customer_id, f"context.entities.{entity_key}", data)

    async def handle_field(self, customer_id: str, field: str, data: Dict[str, Any]):
        """
        DEPRECATED: This method is kept for backward compatibility.
        New code should use the graph engine pipeline.
        
        Handle individual field updates based on confidence thresholds
        """
        HIGH_CONFIDENCE = 0.80
        MEDIUM_CONFIDENCE = 0.55
        
        value = data.get("value")
        confidence = data.get("confidence", 0)
        
        db = await get_mongodb()
        
        if confidence >= HIGH_CONFIDENCE:
            # Auto-update profile
            update_data = {
                "value": value,
                "confidence": confidence,
                "confirmed": True,
                "updated_at": datetime.utcnow().isoformat()
            }
            await db.customers.update_one(
                {"customer_id": customer_id},
                {"$set": {field: update_data}}
            )
            print(f"✅ Auto-updated {field} for {customer_id} (Confidence: {confidence})")
            
        elif confidence >= MEDIUM_CONFIDENCE:
            # Store in context as unconfirmed AND add to pending
            update_data = {
                "value": value,
                "confidence": confidence,
                "confirmed": False,
                "updated_at": datetime.utcnow().isoformat()
            }
            await db.customers.update_one(
                {"customer_id": customer_id},
                {"$set": {field: update_data}}
            )
            
            # Also add to pending for review
            pending_item = {
                "field": field,
                "proposed_value": value,
                "confidence": confidence,
                "status": "needs_review",
                "detected_at": datetime.utcnow().isoformat()
            }
            await db.customers.update_one(
                {"customer_id": customer_id},
                {"$push": {"pending_inference": pending_item}}
            )
            print(f"⚠️ Added {field} to context (unconfirmed) and pending for {customer_id} (Confidence: {confidence})")
            
        else:
            # Low confidence - Re-evaluate (Log for now)
            print(f"❌ Discarded/Re-evaluating {field} for {customer_id} (Confidence: {confidence})")


    async def update_customer_memory(self, customer_id: str, memory: str) -> Dict[str, Any]:
        """Add a key memory for the customer"""
        db = await get_mongodb()
        await db.customers.update_one(
            {"customer_id": customer_id},
            {"$push": {"key_memories": memory}, "$set": {"updated_at": datetime.utcnow()}}
        )
        return await self.get_customer(customer_id)

customer_service = CustomerService()

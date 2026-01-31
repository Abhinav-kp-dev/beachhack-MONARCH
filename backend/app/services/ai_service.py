from typing import Dict, Any, Optional
import json


class AIService:
    """AI Service for context extraction and analysis"""
    
    def __init__(self):
        pass
    
    async def extract_context(self, content: str) -> Dict[str, Any]:
        """Extract structured context from conversation content"""
        # Mock implementation - replace with actual AI model
        # Using fixed mock confidence for testing
        
        topics = self._extract_topics(content)
        # Mock confidence: 0.85 (High) for technical, 0.65 (Medium) for general
        topic_data = {
            t: {"value": t, "confidence": 0.85 if t == "technical" else 0.65}
            for t in topics
        }

        return {
            "topics": topic_data,
            "entities": self._extract_entities(content),
            "action_items": self._extract_action_items(content),
            "questions": self._extract_questions(content)
        }
    
    async def analyze_sentiment(self, content: str) -> str:
        """Analyze sentiment of the content"""
        # Mock implementation
        positive_words = ["thank", "great", "awesome", "love", "excellent", "happy"]
        negative_words = ["problem", "issue", "bad", "terrible", "angry", "frustrated"]
        
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"
    
    async def detect_intent(self, content: str) -> Dict[str, Any]:
        """Detect the primary intent of the conversation with confidence"""
        # Mock implementation
        content_lower = content.lower()
        
        intent = "general"
        confidence = 0.5  # Default low confidence
        
        if any(word in content_lower for word in ["help", "support", "issue", "problem"]):
            intent = "support_request"
            confidence = 0.95  # High confidence
        elif any(word in content_lower for word in ["buy", "purchase", "price", "cost"]):
            intent = "purchase_inquiry"
            confidence = 0.85  # High confidence
        elif any(word in content_lower for word in ["cancel", "refund", "return"]):
            intent = "cancellation"
            confidence = 0.75  # Medium confidence
        elif any(word in content_lower for word in ["how", "what", "where", "when"]):
            intent = "information_request"
            confidence = 0.60  # Medium confidence
            
        return {
            "value": intent,
            "confidence": confidence
        }
    
    async def transcribe_audio(self, audio_data: bytes, language: str = "en") -> Dict[str, Any]:
        """Transcribe audio to text"""
        # Mock implementation - replace with actual transcription service
        return {
            "transcript": "This is a mock transcription of the audio content.",
            "confidence": 0.95,
            "duration_seconds": 30.0,
            "language": language
        }
    
    def _extract_topics(self, content: str) -> list:
        """Extract topics from content"""
        # Simple keyword-based extraction
        topic_keywords = {
            "billing": ["bill", "payment", "charge", "invoice"],
            "shipping": ["ship", "delivery", "track", "package"],
            "product": ["product", "item", "order", "purchase"],
            "account": ["account", "login", "password", "profile"],
            "technical": ["error", "bug", "crash", "not working"]
        }
        
        content_lower = content.lower()
        topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                topics.append(topic)
        return topics if topics else ["general"]
    
    def _extract_entities(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Extract named entities from content with confidence"""
        # Mock implementation
        entities = {
            "order_ids": {},
            "product_names": {}, 
            "dates": {},
            "amounts": {},
            # New demo fields
            "preferences": {},
            "budget": {}
        }
        
        content_lower = content.lower()
        
        if "no callback" in content_lower:
             entities["follow_up_time"] = {"value": "cancelled", "confidence": 0.95}
        elif "saturday morning" in content_lower:
             entities["follow_up_time"] = {"value": "Saturday morning", "confidence": 0.95}

        if "9 lakhs" in content_lower and "firm upper limit" in content_lower:
             entities["budget_max"] = {"value": "900000", "confidence": 0.95}

        if "petrol only" in content_lower or "stick to petrol" in content_lower:
             entities["fuel_type"] = {"value": "petrol", "confidence": 0.95}
        elif "hybrid" in content_lower:
             entities["fuel_type"] = {"value": "hybrid", "confidence": 0.9}

        if "open to manual" in content_lower or "manual or automatic" in content_lower:
             entities["transmission"] = {"value": "manual_or_automatic", "confidence": 0.9}
        elif "automatic" in content_lower:
             entities["transmission"] = {"value": "automatic", "confidence": 0.95}

        if "highway driving can become" in content_lower or "highway driving could become" in content_lower:
             entities["usage_type"] = {"value": "highway_and_city", "confidence": 0.9}
        elif "30 kilometers" in content_lower:
             entities["usage_type"] = {"value": "city_commute", "confidence": 0.9}

        if "4 or 5 years" in content_lower:
             entities["ownership_horizon"] = {"value": "4-5 years", "confidence": 0.9}

        if "1-2 months" in content_lower:
             entities["timeline"] = {"value": "1-2 months", "confidence": 0.9}

        if "brand preference is now flexible" in content_lower or "not limited to toyota or honda" in content_lower:
             entities["car_brands"] = {"value": "flexible", "confidence": 0.9}
        elif "toyota" in content_lower or "honda" in content_lower:
            brands = []
            if "toyota" in content_lower: brands.append("Toyota")
            if "honda" in content_lower: brands.append("Honda")
            entities["car_brands"] = {"value": brands, "confidence": 0.9}

        if "airbags" in content_lower or "crash ratings" in content_lower:
             entities["safety_features"] = {"value": ["dual airbags", "ABS", "good crash ratings"], "confidence": 0.95}

        # Mock extraction for car scenario
        if "hatchback" in content_lower:
             entities["car_type"] = {"value": "hatchback", "confidence": 0.9}
        elif "compact car" in content_lower:
             entities["car_type"] = {"value": "compact", "confidence": 0.85}
        elif "suv" in content_lower and "leaning towards" in content_lower:
             if "compact" not in content_lower:
                 entities["car_type"] = {"value": "suv", "confidence": 0.8}
            
        if "black" in content_lower:
            entities["car_color"] = {"value": "black", "confidence": 0.95}
            
        if "12 lakhs" in content_lower and "initial" in content_lower:
            entities["budget_initial"] = {"value": "1200000", "confidence": 0.9}
        elif "8 lakhs" in content_lower:
            entities["budget_initial"] = {"value": "800000", "confidence": 0.9}
        elif "10 lakhs" in content_lower:
             entities["budget_initial"] = {"value": "1000000", "confidence": 0.9}
            
        if "13" in content_lower and "14" in content_lower and "stretch" in content_lower:
             entities["budget_max"] = {"value": "1400000", "confidence": 0.85}
        elif "15" in content_lower and "17" in content_lower and "extend" in content_lower:
             entities["budget_max"] = {"value": "1700000", "confidence": 0.85}
             
        return entities
    
    def _extract_action_items(self, content: str) -> list:
        """Extract action items from content"""
        # Mock implementation
        return []
    
    def _extract_questions(self, content: str) -> list:
        """Extract questions from content"""
        sentences = content.split('.')
        questions = [s.strip() for s in sentences if '?' in s]
        return questions
    
    async def generate_interaction_summary(self, content: str, intent: Dict[str, Any], extracted_context: Dict[str, Any]) -> str:
        """Generate a brief summary of the current interaction"""
        # Mock implementation - in production, use LLM
        intent_value = intent.get("value", "general") if isinstance(intent, dict) else intent
        topics = extracted_context.get("topics", {})
        topic_list = list(topics.keys()) if isinstance(topics, dict) else topics
        
        summary = f"Customer contacted regarding {intent_value}"
        if topic_list:
            summary += f" related to {', '.join(topic_list[:2])}"
            
        # Add entity details to summary for better context
        entities = extracted_context.get("entities", {})
        details = []
        
        # Check for car specific entities
        if "car_type" in entities:
             details.append(f"type: {entities['car_type'].get('value')}")
        if "car_color" in entities:
             details.append(f"color: {entities['car_color'].get('value')}")
        if "car_brands" in entities:
             brands = entities['car_brands'].get('value')
             if isinstance(brands, list):
                 details.append(f"brands: {', '.join(brands)}")
        if "budget_initial" in entities:
             details.append(f"budget: {entities['budget_initial'].get('value')}")
             
        if details:
            summary += f". Details: {', '.join(details)}."
        
        return summary
    
    async def update_unified_summary(
        self, 
        existing_summary: str, 
        new_interaction_summary: str,
        final_backend_state: Dict[str, Any] = None,
        open_tasks: list = None,
        pending_issues: list = None
    ) -> str:
        """
        Update unified summary incrementally without rebuilding from scratch.
        
        CRITICAL: This is called AFTER the graph engine has finalized the backend state.
        The LLM uses the verified backend state to generate the summary.
        
        Mock implementation - in production, this would use an LLM with a prompt like:
        
        You are updating a customer's unified summary.
        
        EXISTING SUMMARY:
        {existing_summary}
        
        LATEST INTERACTION:
        {new_interaction_summary}
        
        CURRENT VERIFIED STATE (from backend graph engine):
        - Intent: {final_backend_state.context.intent}
        - Entities: {final_backend_state.context.entities}
        - Topics: {final_backend_state.context.topics}
        
        CURRENT CONTEXT:
        - Open Tasks: {open_tasks}
        - Pending Issues: {pending_issues}
        
        Update the summary to:
        1. Preserve valid historical context
        2. Reflect the latest verified truth from backend
        3. Update changed preferences/requirements
        4. Avoid duplication
        5. Keep it concise (2-3 sentences)
        6. Never hallucinate missing facts
        """
        
        # Mock implementation
        if not existing_summary:
            # First interaction - create initial summary
            summary = new_interaction_summary
        else:
            # Merge with existing
            summary = f"{existing_summary} {new_interaction_summary}"
            
            # Simple deduplication (in production, LLM would handle this intelligently)
            if len(summary) > 200:
                summary = summary[:200] + "..."
        
        # Add context about verified state (mock - in production, LLM would incorporate this naturally)
        if final_backend_state:
            intent = final_backend_state.get("context", {}).get("intent", {})
            if isinstance(intent, dict) and intent.get("confirmed"):
                intent_value = intent.get("value")
                if intent_value:
                    # In production, LLM would naturally incorporate this
                    pass  # Mock: already in summary
        
        # Add context about open items
        if pending_issues and len(pending_issues) > 0:
            summary += f" Awaiting resolution on {len(pending_issues)} issue(s)."
        
        return summary


ai_service = AIService()

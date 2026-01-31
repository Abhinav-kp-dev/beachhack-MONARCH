from typing import Dict, Any, Optional
import json


class AIService:
    """AI Service for context extraction and analysis"""
    
    def __init__(self):
        pass
    
    async def extract_context(self, content: str) -> Dict[str, Any]:
        """Extract structured context from conversation content"""
        # Mock implementation - replace with actual AI model
        context = {
            "topics": self._extract_topics(content),
            "entities": self._extract_entities(content),
            "action_items": self._extract_action_items(content),
            "questions": self._extract_questions(content)
        }
        return context
    
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
    
    async def detect_intent(self, content: str) -> str:
        """Detect the primary intent of the conversation"""
        # Mock implementation
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["help", "support", "issue", "problem"]):
            return "support_request"
        elif any(word in content_lower for word in ["buy", "purchase", "price", "cost"]):
            return "purchase_inquiry"
        elif any(word in content_lower for word in ["cancel", "refund", "return"]):
            return "cancellation"
        elif any(word in content_lower for word in ["how", "what", "where", "when"]):
            return "information_request"
        return "general"
    
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
    
    def _extract_entities(self, content: str) -> Dict[str, list]:
        """Extract named entities from content"""
        # Mock implementation
        return {
            "order_ids": [],
            "product_names": [],
            "dates": [],
            "amounts": []
        }
    
    def _extract_action_items(self, content: str) -> list:
        """Extract action items from content"""
        # Mock implementation
        return []
    
    def _extract_questions(self, content: str) -> list:
        """Extract questions from content"""
        sentences = content.split('.')
        questions = [s.strip() for s in sentences if '?' in s]
        return questions


ai_service = AIService()

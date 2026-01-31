"""
Production LLM Service with OpenAI Integration

This service replaces the mock implementations in ai_service.py with real LLM calls.
It integrates seamlessly with the graph engine for deterministic profile updates.
"""

from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from app.core.config import settings
import json


class ProductionLLMService:
    """
    Production LLM service using OpenAI.
    
    This service ONLY extracts and proposes - it NEVER directly modifies customer profiles.
    All profile updates go through the graph engine.
    """
    
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Cost-effective for extraction tasks
    
    async def extract_context(self, content: str) -> Dict[str, Any]:
        """
        Extract structured context from conversation content.
        
        Returns entities, topics, action items with confidence scores.
        The graph engine will decide which to accept.
        """
        if not self.client:
            # Fallback to mock if no API key
            return await self._mock_extract_context(content)
        
        prompt = f"""Extract structured information from this customer conversation.

Conversation:
{content}

Extract the following with confidence scores (0.0-1.0):

1. Topics discussed (billing, shipping, product, technical, etc.)
2. Entities (order IDs, product names, dates, amounts, budget, timeline, etc.)
3. Action items
4. Questions asked
5. Preferences (user constraints, requirements, specific needs)

Return JSON in this format:
{{
  "topics": {{
    "topic_name": {{"value": "topic_name", "confidence": 0.0}}
  }},
  "entities": {{
    "entity_key": {{"value": "entity_value", "confidence": 0.0}}
  }},
  "preferences": [
    {{"category": "category_name", "value": "preference_value", "confidence": 0.0}}
  ],
  "action_items": ["item1", "item2"],
  "questions": ["question1", "question2"]
}}

Be conservative with confidence scores:
- 0.9-1.0: Explicitly stated, no ambiguity
- 0.7-0.9: Clearly implied, high certainty
- 0.5-0.7: Reasonably inferred, some uncertainty
- Below 0.5: Speculative or unclear

Only include entities/topics you can extract. Return empty objects if none found.
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise information extraction assistant. Extract only what is explicitly stated or clearly implied. Be conservative with confidence scores."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"LLM extraction error: {e}")
            return await self._mock_extract_context(content)
    
    async def analyze_sentiment(self, content: str) -> str:
        """Analyze sentiment of the content"""
        if not self.client:
            return self._mock_sentiment(content)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Analyze the sentiment. Respond with only one word: positive, negative, or neutral."},
                    {"role": "user", "content": content}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            sentiment = response.choices[0].message.content.strip().lower()
            if sentiment in ["positive", "negative", "neutral"]:
                return sentiment
            return "neutral"
            
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return self._mock_sentiment(content)
    
    async def detect_intent(self, content: str) -> Dict[str, Any]:
        """
        Detect the primary intent with confidence score.
        
        The graph engine will decide whether to accept this based on confidence.
        """
        if not self.client:
            return self._mock_intent(content)
        
        prompt = f"""Analyze this customer conversation and determine the primary intent.

Conversation:
{content}

Common intents:
- support_request: Customer needs help with an issue
- purchase_inquiry: Customer asking about buying/pricing
- cancellation: Customer wants to cancel/refund
- information_request: Customer asking for information
- feedback: Customer providing feedback
- complaint: Customer expressing dissatisfaction
- general: General conversation

Return JSON:
{{
  "value": "intent_name",
  "confidence": 0.0
}}

Confidence guidelines:
- 0.9-1.0: Intent is crystal clear
- 0.7-0.9: Intent is very likely
- 0.5-0.7: Intent is probable but uncertain
- Below 0.5: Intent is unclear
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent classification assistant. Be precise and conservative with confidence scores."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Intent detection error: {e}")
            return self._mock_intent(content)
    
    async def generate_interaction_summary(
        self,
        content: str,
        intent: Dict[str, Any],
        extracted_context: Dict[str, Any]
    ) -> str:
        """Generate a brief summary of the current interaction"""
        if not self.client:
            return self._mock_interaction_summary(content, intent, extracted_context)
        
        intent_value = intent.get("value", "general") if isinstance(intent, dict) else intent
        topics = extracted_context.get("topics", {})
        entities = extracted_context.get("entities", {})
        
        prompt = f"""Create a brief 1-2 sentence summary of this customer interaction.

Conversation:
{content}

Detected Intent: {intent_value}
Topics: {list(topics.keys()) if topics else 'None'}
Entities: {list(entities.keys()) if entities else 'None'}

Summary should:
- Be concise (1-2 sentences max)
- Focus on what the customer communicated
- Include key details (intent, main topic, important entities)
- Be factual, no speculation

Example: "Customer inquired about upgrading their plan to the premium tier with a budget of $500/month."
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a concise summarization assistant. Create brief, factual summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Summary generation error: {e}")
            return self._mock_interaction_summary(content, intent, extracted_context)
    
    async def update_unified_summary(
        self,
        existing_summary: str,
        new_interaction_summary: str,
        final_backend_state: Dict[str, Any] = None,
        open_tasks: list = None,
        pending_issues: list = None
    ) -> str:
        """
        Update unified summary incrementally using final backend state.
        
        CRITICAL: This is called AFTER the graph engine has finalized the backend state.
        The LLM uses the verified backend state to generate the summary.
        """
        if not self.client:
            return self._mock_unified_summary(
                existing_summary,
                new_interaction_summary,
                final_backend_state,
                pending_issues
            )
        
        # Extract verified state from backend
        verified_intent = None
        verified_entities = {}
        verified_topics = {}
        
        if final_backend_state:
            context = final_backend_state.get("context", {})
            
            intent_data = context.get("intent", {})
            if isinstance(intent_data, dict) and intent_data.get("confirmed"):
                verified_intent = intent_data.get("value")
            
            entities_data = context.get("entities", {})
            for key, data in entities_data.items():
                if isinstance(data, dict) and data.get("confirmed"):
                    verified_entities[key] = data.get("value")
            
            topics_data = context.get("topics", {})
            for key, data in topics_data.items():
                if isinstance(data, dict) and data.get("confirmed"):
                    verified_topics[key] = data.get("value")
        
        prompt = f"""Update the customer's unified summary based on the latest interaction and verified backend state.

EXISTING SUMMARY:
{existing_summary if existing_summary else "No previous summary"}

LATEST INTERACTION:
{new_interaction_summary}

CURRENT VERIFIED STATE (from backend graph engine):
- Intent: {verified_intent or "Not set"}
- Entities: {verified_entities if verified_entities else "None"}
- Topics: {list(verified_topics.keys()) if verified_topics else "None"}
- Pending Issues: {len(pending_issues) if pending_issues else 0}

Instructions:
1. Preserve valid historical context from existing summary
2. Incorporate new information from latest interaction
3. Reflect the verified backend state (this is the source of truth)
4. Update any changed preferences/requirements
5. Avoid duplication - don't repeat the same information
6. Keep it concise (2-3 sentences maximum)
7. Never hallucinate or speculate - only use verified information
8. If pending issues exist, mention them briefly

Return only the updated summary, nothing else.
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise summarization assistant. Create concise, factual summaries using only verified information. Never speculate or hallucinate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Add pending issues note if needed
            if pending_issues and len(pending_issues) > 0 and "pending" not in summary.lower():
                summary += f" Awaiting resolution on {len(pending_issues)} issue(s)."
            
            return summary
            
        except Exception as e:
            print(f"Unified summary error: {e}")
            return self._mock_unified_summary(
                existing_summary,
                new_interaction_summary,
                final_backend_state,
                pending_issues
            )
    
    # ===== Mock Fallbacks =====
    
    async def _mock_extract_context(self, content: str) -> Dict[str, Any]:
        """Fallback mock extraction"""
        from app.services.ai_service import ai_service
        return await ai_service.extract_context(content)
    
    def _mock_sentiment(self, content: str) -> str:
        """Fallback mock sentiment"""
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
    
    def _mock_intent(self, content: str) -> Dict[str, Any]:
        """Fallback mock intent"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["help", "support", "issue", "problem"]):
            return {"value": "support_request", "confidence": 0.85}
        elif any(word in content_lower for word in ["buy", "purchase", "price", "cost"]):
            return {"value": "purchase_inquiry", "confidence": 0.80}
        elif any(word in content_lower for word in ["cancel", "refund", "return"]):
            return {"value": "cancellation", "confidence": 0.75}
        else:
            return {"value": "general", "confidence": 0.50}
    
    def _mock_interaction_summary(
        self,
        content: str,
        intent: Dict[str, Any],
        extracted_context: Dict[str, Any]
    ) -> str:
        """Fallback mock interaction summary"""
        intent_value = intent.get("value", "general") if isinstance(intent, dict) else intent
        topics = extracted_context.get("topics", {})
        topic_list = list(topics.keys()) if isinstance(topics, dict) else []
        
        summary = f"Customer contacted regarding {intent_value}"
        if topic_list:
            summary += f" related to {', '.join(topic_list[:2])}"
        
        return summary
    
    def _mock_unified_summary(
        self,
        existing_summary: str,
        new_interaction_summary: str,
        final_backend_state: Dict[str, Any],
        pending_issues: list
    ) -> str:
        """Fallback mock unified summary"""
        if not existing_summary:
            summary = new_interaction_summary
        else:
            summary = f"{existing_summary} {new_interaction_summary}"
            if len(summary) > 200:
                summary = summary[:200] + "..."
        
        if pending_issues and len(pending_issues) > 0:
            summary += f" Awaiting resolution on {len(pending_issues)} issue(s)."
        
        return summary


# Singleton instance
production_llm_service = ProductionLLMService()

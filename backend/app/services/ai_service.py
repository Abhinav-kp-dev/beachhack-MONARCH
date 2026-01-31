from typing import Dict, Any, Optional
import json
import httpx
from app.core.config import settings
from app.core.logging import logger


class AIService:
    """AI Service for context extraction and analysis using external LLM API"""
    
    def __init__(self):
        self.api_url = settings.EXTERNAL_LLM_API_URL
        self.summary_url = settings.EXTERNAL_SUMMARY_API_URL
        self.use_real_llm = settings.USE_PRODUCTION_LLM

    async def _call_llm_api(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Helper to call external LLM API"""
        if not self.use_real_llm:
            return None
            
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"Calling external LLM API at {self.api_url}")
                response = await client.post(self.api_url, json=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"LLM API Error: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to call LLM API: {str(e)}", exc_info=True)
            return None

    async def _call_summary_api(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Helper to call dedicated external Summary API"""
        if not self.use_real_llm:
            return None
            
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Calling external Summary API at {self.summary_url}")
                # The dedicated summary API might expect a simpler payload or same as conversation
                response = await client.post(self.summary_url, json=payload)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Summary API returned {response.status_code} - falling back to conversation API")
                    return await self._call_llm_api(payload)
        except Exception as e:
            logger.error(f"Failed to call Summary API: {str(e)}")
            return await self._call_llm_api(payload)
    
    async def extract_context(self, content: str) -> Dict[str, Any]:
        """Extract structured context from conversation content"""
        # Clean content for LLM - remove internal headers
        cleaned_content = content
        if "customer_id" in content and "\n" in content:
            # Strip first few lines if they look like headers
            lines = content.splitlines()
            if len(lines) > 2 and "customer_id" in lines[0].lower():
                cleaned_content = "\n".join(lines[3:]) # Skip ID and blank lines
        
        if self.use_real_llm:
            # Prepend strong context instruction to override external model bias
            system_instruction = "Context: General Inquiry. Extract valid user preferences into generic keys. Do NOT force data into automotive fields. Do NOT use keys: 'vehicle_type', 'fuel_type', 'car_color', 'mileage', 'seating_capacity', 'transmission', 'variant'. Use keys like 'timeline', 'budget', 'preference' instead.\n\n"
            
            payload = {
                "customer_id": "extraction_only",
                "channel": "internal",
                "text": system_instruction + cleaned_content
            }
            api_response = await self._call_llm_api(payload)
            
            if api_response and "extracted_context" in api_response:
                ext = api_response["extracted_context"]
                logger.info(f"[RAW LLM RESPONSE] {json.dumps(ext)}")
                logger.info("Successfully received context from real LLM API, mapping fields...")
                
                # TRANSFORMATION LAYER: Map their schema to ours
                
                # Sanitize context to remove hallucinations
                # Pass original content for context verification
                ext = self._sanitize_context(ext, content)
                
                topics = {}
                entities = {}
                action_items = []
                
                # 1. Map preferences -> entities
                # Generic mapping: Map all extracted preferences to entities directly
                for pref in ext.get("preferences", []):
                    cat = pref.get("category")
                    val = pref.get("value")
                    confidence = pref.get("confidence", 0.9)
                    
                    if cat and val:
                        # Fix for our internal naming if necessary
                        if cat == "budget": cat = "budget_initial"
                        
                        entities[cat] = {
                            "value": val,
                            "confidence": confidence
                        }
                
                # 2. Map commitments -> entities (Generic)
                # Map any commitment to an entity if it looks useful
                for comm in ext.get("commitments", []):
                    if isinstance(comm, dict):
                        key = comm.get("category", "commitment")
                        val = comm.get("value")
                        if val:
                            entities[key] = {"value": val, "confidence": 0.9}
                    elif isinstance(comm, str):
                        # If it's just a string, we can't easily categorize it without NLP, 
                        # so we append it to action items or a generic 'commitments' list
                        # For now, let's treat it as an action item if it's actionable
                        action_items.append(comm)
                
                # 3. Map issues -> action_items
                for issue in ext.get("issues", []):
                    if isinstance(issue, dict):
                        action_items.append(issue.get("value", str(issue)))
                    else:
                        action_items.append(str(issue))
                
                # 4. Handle signals (sentiment/intent)
                signals = ext.get("signals", {})
                if signals.get("intent"):
                    topics[signals["intent"]] = {"value": signals["intent"], "confidence": 0.9}

                return {
                    "topics": topics,
                    "entities": entities,
                    "action_items": action_items,
                    "questions": self._extract_questions(content) # Keep local regex for now
                }
            
            # If we are here, use_real_llm is True but API failed or returned invalid data
            logger.error("Real LLM API failed to return valid context. Strict mode enabled: NOT using mocks.")
            # Return empty structure rather than mock data to avoid confusion
            return {
                "topics": {},
                "entities": {},
                "action_items": [],
                "questions": []
            }
                
        # Only use mock if explicitly configured to NOT use real LLM
        logger.warning("Real LLM disabled. Using mock implementation.")
        topics = self._extract_topics(content)
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
        # Simple cleaning
        cleaned_content = content
        if "customer_id" in content and len(content.splitlines()) > 3:
             cleaned_content = "\n".join(content.splitlines()[3:])

        if self.use_real_llm:
            payload = {
                "customer_id": "analysis_only",
                "channel": "internal",
                "text": cleaned_content, 
                "task": "sentiment"
            }
            api_response = await self._call_llm_api(payload)
            if api_response:
                # Try to find sentiment in signals or root
                sentiment = api_response.get("sentiment")
                if not sentiment and "extracted_context" in api_response:
                    sentiment = api_response["extracted_context"].get("signals", {}).get("sentiment")
                
                if sentiment:
                    return str(sentiment).lower()

        # Fallback to mock implementation
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
        # Simple cleaning
        cleaned_content = content
        if "customer_id" in content and len(content.splitlines()) > 3:
             cleaned_content = "\n".join(content.splitlines()[3:])

        if self.use_real_llm:
            payload = {
                "customer_id": "analysis_only",
                "channel": "internal",
                "text": cleaned_content,
                "task": "intent"
            }
            api_response = await self._call_llm_api(payload)
            if api_response:
                intent_data = api_response.get("intent")
                if not intent_data and "extracted_context" in api_response:
                    intent_val = api_response["extracted_context"].get("signals", {}).get("intent")
                    if intent_val:
                        intent_data = {"value": intent_val, "confidence": 0.9}
                
                if intent_data:
                    return intent_data

        # Fallback to mock implementation
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
        """Transcribe audio to text using external Whisper API"""
        if not self.use_real_llm:
            return {
                "transcript": "Real LLM is disabled. This is a mock transcript.",
                "confidence": 0.95,
                "duration_seconds": 30.0,
                "language": language
            }

        # The external API expects multipart/form-data
        # We need a filename for the upload logic in some frameworks
        files = {"file": ("audio_file.mp3", audio_data, "audio/mpeg")}
        
        # Build the transcribe URL by replacing /conversation with /transcribe
        transcribe_url = self.api_url.replace("/conversation", "/transcribe")
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info(f"Calling transcription API at {transcribe_url}")
                response = await client.post(transcribe_url, files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "transcript": result.get("transcript", ""),
                        "confidence": result.get("confidence", 0.95),
                        "duration_seconds": result.get("duration", result.get("duration_seconds", 0.0)),
                        "language": result.get("language", language)
                    }
                else:
                    logger.error(f"Transcription API Error: {response.status_code} - {response.text}")
                    raise Exception(f"Transcription failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {str(e)}", exc_info=True)
            # Minimal fallback for stability
            return {
                "transcript": "[Transcription Error]",
                "confidence": 0.0,
                "duration_seconds": 0.0,
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
    
    
    def _sanitize_context(self, context: Dict[str, Any], content: str = "") -> Dict[str, Any]:
        """
        Sanitize extracted context to remove known hallucinations unless supported by content.
        implements 'Smart Relevance Check'.
        """
        # Map fields to required keywords. If field is present, one of the keywords MUST be in the text.
        param_requirements = {
            "vehicle_type": ["car", "vehicle", "truck", "bike", "scooter", "suv", "sedan", "hatchback", "auto"],
            "fuel_type": ["fuel", "petrol", "diesel", "electric", "hybrid", "gas", "ev"],
            "mileage": ["mileage", "km/l", "efficiency", "range", "km", "miles"],
            "seating_capacity": ["seat", "passenger", "people", "calapcity", "seater"],
            "transmission": ["manual", "automatic", "gear", "transmission", "clutch"],
            "car_color": ["color", "red", "black", "white", "blue", "paint"], # Be careful with generic 'color'
        }
        
        content_lower = content.lower() if content else ""
        
        # 1. Sanitize preferences
        if "preferences" in context:
            clean_prefs = []
            for pref in context["preferences"]:
                cat = pref.get("category", "").lower().strip()
                val = pref.get("value", "")
                
                # Check if this category has specific requirements
                if cat in param_requirements:
                    required_keywords = param_requirements[cat]
                    # Check if any keyword matches
                    is_valid = any(kw in content_lower for kw in required_keywords)
                    
                    if not is_valid:
                        # HEURISTIC: Remap known confusions
                        if cat == "seating_capacity" and ("hour" in str(val) or "week" in str(val)):
                            logger.warning(f"SmartSanitizer: Remapping '{cat}'='{val}' to 'commitment' (Time detected)")
                            pref["category"] = "commitment"
                            clean_prefs.append(pref)
                        else:
                            logger.warning(f"SmartSanitizer: Dropping '{cat}'='{val}' - No supporting keywords found in text.")
                        continue
                    
                clean_prefs.append(pref)
            context["preferences"] = clean_prefs
            
        return context

    def _extract_entities(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Extract named entities from content with confidence"""
        # Mock implementation - Generic fallback only.
        # In a real scenario without the LLM, we can't reliably do this dynamically.
        # We will return a basic structure.
        
        entities = {}
        content_lower = content.lower()
        
        # Simple rule-based extraction for demonstration if LLM is off
        # but WITHOUT specific domain assumptions
        import re
        
        # Extract potential amounts (generic)
        amounts = re.findall(r'[\$£€₹]\s?(\d+(?:,\d+)*(?:\.\d{2})?)', content)
        if amounts:
             entities["mentioned_amounts"] = {"value": amounts, "confidence": 0.7}

        # Extract potential dates/times (very basic)
        if "tomorrow" in content_lower:
             entities["relative_time"] = {"value": "tomorrow", "confidence": 0.8}
        
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
        """Generate a brief summary of the current interaction using real LLM if available"""
        if self.use_real_llm:
            # Simple cleaning
            cleaned_content = content
            if "customer_id" in content and len(content.splitlines()) > 3:
                cleaned_content = "\n".join(content.splitlines()[3:])

            payload = {
                "customer_id": "summary_only",
                "channel": "internal",
                "text": cleaned_content,
                "task": "summary" # Attempt to use summary task
            }
            api_response = await self._call_summary_api(payload)
            if api_response and "summary" in api_response:
                return api_response["summary"]

        if self.use_real_llm:
            # ... (previous real LLM logic)
            pass

        # Improved fallback logic
        intent_value = intent.get("value", "general") if isinstance(intent, dict) else intent
        summary = f"Interaction regarding {intent_value.replace('_', ' ')}."
        
        entities = extracted_context.get("entities", {})
        impactful_details = []
        
        # Extract meaningful details from entities for mock summary
        for key, info in entities.items():
            val = info.get("value") if isinstance(info, dict) else info
            if val and key not in ["customer_id", "intent"]:
                impactful_details.append(f"{key.replace('_', ' ')}: {val}")
        
        if impactful_details:
            summary += f" Key details: {', '.join(impactful_details)}."
        else:
            # Try to extract something from contents
            if "budget" in content.lower(): summary += " Budget was discussed."
            if "timeline" in content.lower(): summary += " Timeline was discussed."
            
        return summary
    
    async def update_unified_summary(
        self, 
        existing_summary: str, 
        new_interaction_summary: str,
        final_backend_state: Dict[str, Any] = None,
        open_tasks: list = None,
        pending_issues: list = None
    ) -> Dict[str, Any]:
        """
        Update unified summary incrementally using real LLM if available.
        Returns a dict: {'summary': str, 'questions': List[str], 'recommendations': List[Dict]}
        """
        
        # Default fallback structure (Simulate diverse "database" of questions)
        result = {
            "summary": f"{existing_summary} {new_interaction_summary}".strip(),
            "questions": [
                "Does the customer have any timeline constraints?",
                "Are there any specific budget preferences we missed?",
                "Is there anything else I can help you with?",
                "Would you like to schedule a follow-up?"
            ],
            "recommendations": [
                {"category": "engagement", "recommendation": "Verify customer satisfaction before closing", "confidence": 0.85, "reason": "Standard procedure"},
                {"category": "upsell", "recommendation": "Check for available upgrades", "confidence": 0.60, "reason": "Potential interest based on profile"}
            ]
        }
        
        # If open tasks/issues exist, tailor the defaults
        if pending_issues:
             result["questions"] = [
                 f"Can you provide more details about the {pending_issues[0].get('description', 'issue')}?",
                 "Has the previous issue been resolved to your satisfaction?",
                 "Is there urgency around this request?"
             ]
             result["recommendations"].append({
                 "category": "support", 
                 "recommendation": "Prioritize resolving open issue", 
                 "confidence": 0.95, 
                 "reason": "Active issue detected"
             })

        if self.use_real_llm:
            combined_context = f"EXISTING SUMMARY: {existing_summary}\n\nNEW INTERACTION: {new_interaction_summary}"
            if final_backend_state:
                combined_context += f"\n\nCURRENT PROFILE STATE: {json.dumps(final_backend_state)}"

            payload = {
                "customer_id": "summary_and_planning",
                "channel": "internal",
                "text": combined_context,
                "task": "summary",
                "context": (
                    "1. Update the EXISTING SUMMARY into a single, cohesive customer narrative.\n"
                    "2. Generate 3 specific follow-up questions for the agent to ask.\n"
                    "3. Generate 1-2 strategic recommendations (next best actions) with confidence score (0-1)."
                )
            }
            api_response = await self._call_summary_api(payload)
            
            if api_response:
                # LLM response handling - expecting structured output or we parse it
                # Assuming the external API returns 'summary', 'questions', 'recommendations' 
                # or we extract them from 'extracted_context' if the prompt was complex
                
                # Check for direct fields
                if "summary" in api_response:
                    result["summary"] = api_response["summary"]
                
                # Extract questions/recommendations from potential extended fields or context
                # If API supports custom structured output, great. If not, fallback to parsing or separate calls.
                # For this implementation, we assume the API returns them or we use simple heuristics
                
                if "questions" in api_response:
                    result["questions"] = api_response["questions"]
                
                if "recommendations" in api_response:
                    result["recommendations"] = api_response["recommendations"]
                
                return result

        # Generic merge/improvement fallback logic
        if not existing_summary or "None." in existing_summary or "Interaction regarding inquiry." in existing_summary:
             result["summary"] = new_interaction_summary
        elif new_interaction_summary not in existing_summary:
             # Intelligent appending - avoid exact duplication
             result["summary"] = f"{existing_summary} Further interaction: {new_interaction_summary}"
        
        return result


ai_service = AIService()

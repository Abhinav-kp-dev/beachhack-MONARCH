"""
Context extraction service using LLaMA 3
Extracts structured information from conversations with anti-hallucination measures

AUTHORITY: LLM = Compiler (facts only)
- LLM outputs transient data: preferences, issues, commitments, signals
- NO summarization, NO decision-making, NO action recommendations
- ExtractedContext has NO authority until validated and stored in CustomerProfile
"""

import requests
import json
import logging
from typing import Optional, Dict
from models import ExtractedContext
from utils.prompt_templates import CONTEXT_EXTRACTION_PROMPT
from services.cost_optimization import get_llm_cache, get_simple_detector, get_cost_tracker
import config

logger = logging.getLogger(__name__)


class ContextExtractionService:
    """Service for extracting structured context from conversations using LLaMA 3"""
    
    def __init__(self):
        self.ollama_url = f"{config.OLLAMA_URL}/api/generate"
        self.model = config.OLLAMA_MODEL
        
        # Cost optimization components
        self.cache = get_llm_cache()
        self.simple_detector = get_simple_detector()
        self.cost_tracker = get_cost_tracker()
        
        logger.info(f"Initialized ContextExtractionService with model: {self.model}")
        logger.info("Cost optimization enabled: caching, simple query detection, cost tracking")
    
    def _preprocess_tagged_conversation(self, conversation_text: str) -> str:
        """
        Preprocess tagged conversations to ensure proper formatting.
        Handles common tag formats: "Customer:", "CUSTOMER:", "[Customer]", etc.
        
        Args:
            conversation_text: Raw conversation text with speaker tags
            
        Returns:
            Formatted conversation text with consistent tags
        """
        # Already properly tagged, return as-is
        if "CUSTOMER:" in conversation_text or "PROFESSIONAL:" in conversation_text:
            return conversation_text
        
        # Convert common formats to standard format
        import re
        
        # Replace various customer tags
        conversation_text = re.sub(
            r'\b(Customer|customer|CLIENT|Client|USER|User)\s*[:\-]',
            'CUSTOMER:',
            conversation_text
        )
        
        # Replace various professional tags  
        conversation_text = re.sub(
            r'\b(Agent|agent|AGENT|Professional|professional|Rep|rep|Sales|sales|Support|support|Assistant|assistant)\s*[:\-]',
            'PROFESSIONAL:',
            conversation_text
        )
        
        return conversation_text
    
    def _deduplicate_and_normalize(self, items: list, is_classified: bool = False) -> list:
        """
        Intelligent deduplication and normalization of extracted items with confidence scores.
        Handles variations, plurals, and semantic duplicates.
        Keeps highest confidence score for duplicates.
        
        Args:
            items: List of items to deduplicate
            is_classified: True if items are ClassifiedPreference objects with categories
        """
        if not items:
            return []
        
        # Handle ClassifiedPreference objects (preferences)
        if is_classified:
            from models import ClassifiedPreference
            
            # Convert to ClassifiedPreference objects if needed
            classified_items = []
            for item in items:
                if isinstance(item, dict) and 'category' in item and 'value' in item and 'confidence' in item:
                    classified_items.append(ClassifiedPreference(
                        category=item['category'],
                        value=item['value'],
                        confidence=item['confidence']
                    ))
                elif hasattr(item, 'category') and hasattr(item, 'value') and hasattr(item, 'confidence'):
                    classified_items.append(item)
            
            # Group by category for deduplication
            by_category = {}
            for item in classified_items:
                category = item.category.lower().strip()
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(item)
            
            # Deduplicate within each category
            result = []
            for category, items_in_cat in by_category.items():
                seen_values = {}
                
                for item in items_in_cat:
                    value = item.value.strip()
                    if not value or len(value) < 2:
                        continue
                    
                    normalized_value = ' '.join(value.lower().strip().split())
                    
                    # Check for duplicates or substrings
                    found_duplicate = False
                    keys_to_remove = []
                    
                    for existing_key in list(seen_values.keys()):
                        if normalized_value in existing_key or existing_key in normalized_value:
                            # Keep higher confidence or longer version
                            if item.confidence > seen_values[existing_key].confidence:
                                keys_to_remove.append(existing_key)
                                seen_values[normalized_value] = item
                            found_duplicate = True
                            break
                        elif normalized_value == existing_key:
                            if item.confidence > seen_values[existing_key].confidence:
                                seen_values[normalized_value] = item
                            found_duplicate = True
                            break
                    
                    for key in keys_to_remove:
                        del seen_values[key]
                    
                    if not found_duplicate:
                        seen_values[normalized_value] = item
                
                # Add deduplicated items from this category
                result.extend([{
                    'category': item.category,
                    'value': item.value,
                    'confidence': item.confidence
                } for item in seen_values.values()])
            
            # Sort by confidence
            result.sort(key=lambda x: x['confidence'], reverse=True)
            return result[:50]
        
        # Handle regular ConfidenceScore objects (issues, commitments)
        else:
            from models import ConfidenceScore
            
            # Convert to ConfidenceScore objects if needed
            confidence_items = []
            for item in items:
                if isinstance(item, dict) and 'value' in item and 'confidence' in item:
                    confidence_items.append(ConfidenceScore(value=item['value'], confidence=item['confidence']))
                elif isinstance(item, str):
                    confidence_items.append(ConfidenceScore(value=item, confidence=0.8))
                elif hasattr(item, 'value') and hasattr(item, 'confidence'):
                    confidence_items.append(item)
            
            # Normalize and deduplicate
            seen_values = {}  # {normalized_value: ConfidenceScore}
            
            for item in confidence_items:
                value = item.value.strip()
                if not value or len(value) < 2:
                    continue
                
                normalized_value = ' '.join(value.lower().strip().split())
                
                # Check for exact duplicates or substrings
                found_duplicate = False
                keys_to_remove = []
                
                for existing_key in list(seen_values.keys()):
                    if normalized_value in existing_key:
                        if item.confidence > seen_values[existing_key].confidence:
                            keys_to_remove.append(existing_key)
                            seen_values[normalized_value] = item
                        found_duplicate = True
                        break
                    elif existing_key in normalized_value:
                        if item.confidence >= seen_values[existing_key].confidence * 0.9:
                            keys_to_remove.append(existing_key)
                            seen_values[normalized_value] = item
                        found_duplicate = True
                        break
                    elif normalized_value == existing_key:
                        if item.confidence > seen_values[existing_key].confidence:
                            seen_values[normalized_value] = item
                        found_duplicate = True
                        break
                
                for key in keys_to_remove:
                    del seen_values[key]
                
                if not found_duplicate:
                    seen_values[normalized_value] = item
            
            # Convert back to list of dicts
            result = sorted(
                [{'value': item.value, 'confidence': item.confidence} for item in seen_values.values()],
                key=lambda x: x['confidence'],
                reverse=True
            )
            
            return result[:50]
    
    def extract_context(self, conversation_text: str, customer_id: str = "unknown") -> Optional[ExtractedContext]:
        """
        Extract structured context from conversation text with intelligent analysis.
        Handles tagged conversations (CUSTOMER/PROFESSIONAL) and detects agreements.
        
        COST OPTIMIZATION:
        1. Check if query is too simple (skip LLM)
        2. Check cache for similar conversations
        3. Call LLM only if necessary
        4. Track costs for ROI analysis
        
        INTELLIGENT ANALYSIS:
        - Detects when professional suggests and customer agrees
        - Analyzes each conversation exchange for context
        - Tracks sentiment and agreement patterns
        
        AUTHORITY: LLM = Compiler (facts only)
        - Outputs preferences, issues, commitments, signals (transient)
        - NO decision-making, NO summaries, NO persistence
        - This data has NO authority until validated and stored in CustomerProfile
        
        Args:
            conversation_text: Raw conversation text (may include speaker tags)
            customer_id: Customer ID for cost tracking
            
        Returns:
            ExtractedContext object or None if extraction fails
        """
        try:
            # Preprocess tagged conversations for better analysis
            processed_text = self._preprocess_tagged_conversation(conversation_text)
            
            # Log if conversation has speaker tags
            if "CUSTOMER:" in processed_text or "PROFESSIONAL:" in processed_text:
                logger.info("📋 Tagged conversation detected - analyzing customer-professional interactions")
            
            # OPTIMIZATION 1: Detect simple queries (no LLM needed)
            is_simple, reason = self.simple_detector.is_simple(processed_text)
            if is_simple:
                logger.info(f"💰 COST SAVED: Simple query detected ({reason}) - Skipping LLM")
                self.cost_tracker.record_llm_call(customer_id, cached=True)
                return ExtractedContext(
                    preferences=[],
                    issues=[],
                    commitments=[],
                    signals={"sentiment": "neutral", "urgency": "low", "intent": "greeting"}
                )
            
            # OPTIMIZATION 2: Check cache
            cached_response = self.cache.get(processed_text)
            if cached_response:
                logger.info(f"💰 COST SAVED: Cache hit - Skipping LLM call")
                self.cost_tracker.record_llm_call(customer_id, cached=True)
                return ExtractedContext(**cached_response)
            
            # OPTIMIZATION 3: LLM call required
            logger.info("Calling LLM for intelligent context extraction...")
            self.cost_tracker.record_llm_call(customer_id, cached=False)
            
            # Prepare prompt
            prompt = CONTEXT_EXTRACTION_PROMPT.format(
                conversation=processed_text
            )
            
            # Call LLaMA 3 via Ollama with retry logic
            logger.info("Calling LLaMA 3 for context extraction...")
            
            max_retries = 2  # Reduced retries
            response = None
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        self.ollama_url,
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "temperature": 0.05,  # Very low for consistency
                            "top_p": 0.85,  # Increased for better coverage
                            "top_k": 25,  # Increased for better extraction
                            "repeat_penalty": 1.1,  # Moderate to allow repetition if needed
                            "format": "json",
                            "options": {
                                "num_predict": 1500,  # Increased significantly for large conversations
                                "num_ctx": 4096,  # Doubled context window for large inputs
                            }
                        },
                        timeout=90  # Increased timeout for large conversations
                    )
                    if response.status_code == 200:
                        logger.info(f"✓ LLM extraction successful (attempt {attempt + 1})")
                        break
                    logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code}")
                    last_error = f"Status {response.status_code}"
                except requests.exceptions.Timeout:
                    logger.warning(f"Attempt {attempt + 1} timed out after 90s")
                    last_error = "Timeout"
                    if attempt < max_retries - 1:
                        continue
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        continue
            
            if not response or response.status_code != 200:
                logger.error(f"All LLM attempts failed. Last error: {last_error}")
                logger.info("Returning minimal valid context to prevent complete failure")
                return ExtractedContext(
                    preferences=[],
                    issues=[],
                    commitments=[],
                    signals={"sentiment": "neutral", "urgency": "low", "intent": "unknown"}
                )
            
            # Parse response
            result = response.json()
            raw_response = result.get("response", "")
            
            logger.debug(f"Raw LLaMA response: {raw_response}")
            
            # Parse JSON from response
            # Clean up response if it has markdown code blocks
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```"):
                # Remove markdown code blocks
                lines = cleaned_response.split("\n")
                cleaned_response = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned_response
                cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
            
            context_data = json.loads(cleaned_response)
            
            logger.debug(f"Parsed context_data: {context_data}")
            
            # Validate and create ExtractedContext
            # Handle legacy format if LLM still returns old schema
            if 'intent' in context_data and 'signals' not in context_data:
                logger.warning("LLM returned old format, converting to new format")
                # Convert old format to new
                context_data['signals'] = {
                    'intent': context_data.pop('intent', 'general'),
                    'sentiment': context_data.pop('sentiment', 'neutral'),
                    'urgency': context_data.pop('urgency', 'low')
                }
                # Remove old next_best_action if present
                context_data.pop('next_best_action', None)
                logger.debug(f"Converted context_data: {context_data}")
            
            # Ensure all required fields have defaults
            context_data.setdefault('preferences', [])
            context_data.setdefault('issues', [])
            context_data.setdefault('commitments', [])
            context_data.setdefault('signals', {})
            
            # CONFIDENCE VALIDATION: Ensure all items have confidence scores
            # Filter out items with confidence < 0.5 (too uncertain)
            
            # Validate preferences (classified with categories)
            if 'preferences' in context_data:
                validated_prefs = []
                for item in context_data['preferences']:
                    if isinstance(item, dict) and 'category' in item and 'value' in item and 'confidence' in item:
                        conf = max(0.0, min(1.0, float(item['confidence'])))
                        if conf >= 0.5:
                            pref = {
                                'category': item['category'].lower().strip(),
                                'value': item['value'].strip(),
                                'confidence': conf
                            }
                            # Log source information if present (for debugging)
                            if 'source' in item:
                                logger.debug(f"Preference source: {item['source']} - {pref['value']}")
                            validated_prefs.append(pref)
                    elif isinstance(item, dict) and 'value' in item and 'confidence' in item:
                        # Old format - assign default category
                        conf = max(0.0, min(1.0, float(item['confidence'])))
                        if conf >= 0.5:
                            validated_prefs.append({
                                'category': 'other',
                                'value': item['value'].strip(),
                                'confidence': conf
                            })
                context_data['preferences'] = validated_prefs
            
            # Validate issues and commitments
            for field in ['issues', 'commitments']:
                validated_items = []
                for item in context_data.get(field, []):
                    if isinstance(item, dict) and 'value' in item and 'confidence' in item:
                        conf = max(0.0, min(1.0, float(item['confidence'])))
                        if conf >= 0.5:
                            validated_items.append({'value': item['value'], 'confidence': conf})
                    elif isinstance(item, str):
                        validated_items.append({'value': item, 'confidence': 0.8})
                context_data[field] = validated_items
            
            # POST-PROCESSING: Intelligent deduplication and normalization
            context_data['preferences'] = self._deduplicate_and_normalize(context_data['preferences'], is_classified=True)
            context_data['issues'] = self._deduplicate_and_normalize(context_data['issues'])
            context_data['commitments'] = self._deduplicate_and_normalize(context_data['commitments'])
            
            # Validate signals
            valid_sentiments = ['neutral', 'positive', 'negative', 'frustrated', 'excited']
            valid_urgencies = ['low', 'medium', 'high', 'critical']
            if context_data['signals'].get('sentiment') not in valid_sentiments:
                context_data['signals']['sentiment'] = 'neutral'
            if context_data['signals'].get('urgency') not in valid_urgencies:
                context_data['signals']['urgency'] = 'low'
            
            context = ExtractedContext(**context_data)
            logger.info(f"Successfully extracted and normalized context: {len(context.preferences)} preferences, {len(context.issues)} issues, {len(context.commitments)} commitments")
            
            # OPTIMIZATION 4: Cache successful extraction (using processed text as key)
            self.cache.set(processed_text, context_data)
            logger.debug("Cached LLM response for future use")
            
            return context
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLaMA response: {e}")
            logger.error(f"Raw response: {raw_response}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to Ollama failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Context extraction failed: {e}")
            logger.error(f"Context data was: {context_data if 'context_data' in locals() else 'not parsed'}")
            return None
    
    def extract_customer_info(self, text: str) -> Dict[str, str]:
        """
        Extract customer identification information from text (name, email, phone)
        
        Args:
            text: Conversation text
            
        Returns:
            Dict with name, email, phone (empty strings if not found)
        """
        try:
            prompt = f"""Extract customer identification information from the following conversation.
Return ONLY a JSON object with these fields (use empty string if not found):
- name: Customer's full name
- email: Customer's email address
- phone: Customer's phone number

Conversation:
{text}

Return ONLY valid JSON, no explanations:"""

            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.0,
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.warning(f"Customer info extraction API error: {response.status_code}")
                return {"name": "", "email": "", "phone": ""}
            
            result = response.json()
            raw_response = result.get("response", "")
            
            # Clean markdown if present
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```"):
                lines = cleaned_response.split("\n")
                cleaned_response = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned_response
                cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
            
            info = json.loads(cleaned_response)
            
            # Validate and return with defaults
            return {
                "name": info.get("name", "").strip(),
                "email": info.get("email", "").strip(),
                "phone": info.get("phone", "").strip()
            }
            
        except Exception as e:
            logger.warning(f"Customer info extraction failed: {e}")
            return {"name": "", "email": "", "phone": ""}


# Singleton instance
_extraction_service = None

def get_extraction_service() -> ContextExtractionService:
    """Get or create singleton instance of ContextExtractionService"""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ContextExtractionService()
    return _extraction_service


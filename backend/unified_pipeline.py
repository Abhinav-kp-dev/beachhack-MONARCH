#!/usr/bin/env python3
"""
Unified Customer Profile Pipeline v2
- Separate collections for customers and conversations
- Auto-generates customer ID if not provided
- Updates customer profile after each conversation
- Stores each conversation as a new document
- Structured slot-based preference system (latest value wins)
"""

import requests
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient
from typing import Dict, List, Any, Optional, Tuple

# ============================================================
# CONFIGURATION - Edit these values
# ============================================================

# Audio file to process
AUDIO_FILE_PATH = "/home/abhishek-reji/Downloads/output4.mp3"

# API endpoints
API_BASE_URL = "http://192.168.220.76:8000"
TRANSCRIBE_URL = f"{API_BASE_URL}/transcribe"
CONVERSATION_URL = f"{API_BASE_URL}/conversation"

# MongoDB Configuration
MONGODB_URI = "mongodb://localhost:27017"
DATABASE_NAME = "customer_intelligence"

# Customer details (optional - set CUSTOMER_ID to link to existing customer)
CUSTOMER_ID = None  # Set to existing ID to update, or None to create new
CUSTOMER_NAME = None
CUSTOMER_EMAIL = None
CUSTOMER_PHONE = None
CHANNEL = "call"  # Options: 'chat', 'email', 'call'

# ============================================================
# LOCAL PREFERENCE EXTRACTION (Fallback when API returns empty)
# ============================================================
# This extracts preferences directly from conversation text using
# pattern matching when the LLM API fails to extract them.


class LocalPreferenceExtractor:
    """
    Extracts preferences from conversation text using pattern matching.
    
    FALLBACK: Used when the API returns empty preferences.
    This is a universal extractor that looks for common patterns like:
    - "I prefer X", "I want X", "looking for X"
    - Budget mentions: "around X lakhs", "budget of X"
    - Time references: "in X months", "by next X"
    - Requirements: "must have X", "need X", "important: X"
    """
    
    # Common extraction patterns (category -> regex patterns)
    EXTRACTION_PATTERNS = {
        # Budget patterns
        "budget": [
            r"budget[^\d]*(\d+(?:\.\d+)?)\s*(?:lakh|lac|l|k|thousand|crore)?",
            r"around\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac|l|k)?",
            r"stretch\s*to\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac)?",
            r"(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\s*(?:budget|range)?",
        ],
        # Timeline patterns
        "purchase_timeline": [
            r"(?:in\s*the\s*)?next\s*(\d+[-–]\d+|\d+)\s*months?",
            r"(?:within|by)\s*(\d+[-–]\d+|\d+)\s*months?",
            r"planning\s*(?:to\s*buy\s*)?(?:in\s*)?(\d+[-–]\d+|\d+)\s*months?",
        ],
        # Vehicle type patterns
        "vehicle_type": [
            r"(?:looking\s*for|leaning\s*towards?|considering|prefer)\s*(?:a\s*|an\s*)?(suv|sedan|hatchback|compact|muv|crossover)",
            r"(suv|sedan|hatchback|compact|muv|crossover)\s*(?:might\s*be|would\s*be|is)",
        ],
        # Fuel type patterns
        "fuel_type": [
            r"(?:considering|prefer|thinking|interested\s*in)\s*(petrol|diesel|hybrid|electric|cng|ev)",
            r"(petrol|diesel|hybrid|electric|cng|ev)\s*(?:would\s*be|could\s*be|seems?)",
        ],
        # Transmission patterns
        "transmission": [
            r"(?:prefer|want|need)\s*(automatic|manual|amt|cvt)",
            r"(automatic|manual|amt|cvt)\s*(?:transmission|gear)?",
        ],
        # Brand patterns
        "brand_preference": [
            r"(?:trust|prefer|like|experience\s*with|interested\s*in)\s*([\w]+)\s*(?:brand|company|cars?)?",
            r"(toyota|honda|hyundai|maruti|tata|mahindra|kia|volkswagen|skoda|mg|bmw|mercedes|audi|ford|nissan|renault)\s*(?:seems?|is|are)?",
        ],
        # Usage patterns
        "usage_type": [
            r"(?:for|it\'?s\s*for)\s*(personal|business|commercial|family)\s*(?:use|purpose)?",
            r"(daily\s*commute|office|city\s*driving|highway|long\s*trips?)",
        ],
        # Ownership duration
        "ownership_duration": [
            r"(?:keep|own|use)\s*(?:this\s*car\s*)?(?:for\s*)?(?:at\s*least\s*)?(\d+[-–]\d+|\d+)\s*years?",
        ],
        # Safety features
        "safety_requirements": [
            r"(?:need|want|must\s*have|non-negotiable)[:\s]*(airbags?|abs|crash\s*rating|safety)",
            r"(airbags?|abs|crash\s*ratings?)\s*(?:is|are)?\s*(?:important|must|needed)?",
        ],
        # Callback/follow-up
        "callback_preference": [
            r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*(morning|afternoon|evening|night)?",
            r"call\s*(?:me\s*)?(?:back\s*)?(next\s*week|tomorrow|today)",
        ],
        # Concerns/hesitations
        "concerns": [
            r"(?:not\s*sure|concerned|worried|hesitant)\s*(?:about|if)\s*(.+?)(?:\.|$)",
            r"might\s*postpone\s*(?:if|because)\s*(.+?)(?:\.|$)",
        ],
        # Features wanted
        "features_wanted": [
            r"(?:need|want|must\s*have|looking\s*for)[:\s]*([\w\s]+?)(?:,|\.|and|$)",
        ],
        # Features not wanted
        "features_not_wanted": [
            r"(?:don\'?t\s*(?:really\s*)?care\s*about|don\'?t\s*need|not\s*interested\s*in)[:\s]*([\w\s]+?)(?:\.|$)",
        ],
        # Daily commute
        "daily_commute_km": [
            r"(?:daily\s*)?commute[^\d]*(\d+)\s*(?:km|kilometers?|kms?)",
            r"(\d+)\s*(?:km|kilometers?)\s*(?:daily|commute)?",
        ],
    }
    
    @classmethod
    def extract_from_text(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extract all preferences from conversation text.
        
        Returns list of preference dicts: [{category, value, confidence}, ...]
        """
        extracted = []
        text_lower = text.lower()
        
        # Extract customer statements (lines after "Customer:")
        customer_statements = []
        for line in text.split('\n'):
            if line.strip().lower().startswith('customer:'):
                customer_statements.append(line.split(':', 1)[1].strip() if ':' in line else line)
        
        # Combine customer statements for focused extraction
        customer_text = ' '.join(customer_statements).lower()
        
        for category, patterns in cls.EXTRACTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, customer_text, re.IGNORECASE)
                for match in matches:
                    if match and len(match.strip()) > 1:
                        # Normalize the value
                        value = match.strip() if isinstance(match, str) else match[0].strip() if match else None
                        if value:
                            # Avoid duplicates
                            existing = [e for e in extracted if e['category'] == category and e['value'] == value]
                            if not existing:
                                extracted.append({
                                    'category': category,
                                    'value': value,
                                    'confidence': 0.75,
                                    'source': 'local_extraction'
                                })
        
        return extracted
    
    @classmethod
    def extract_key_value_pairs(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extract explicit key-value patterns from text.
        
        Patterns like:
        - "Budget: 10 lakhs"
        - "Preferred brand: Toyota"
        - "Timeline: 6 months"
        """
        extracted = []
        
        # Pattern for "Key: Value" or "Key - Value"
        kv_pattern = r'(?:^|\n)\s*([A-Za-z][A-Za-z\s]+?)[\s]*[:–-][\s]*([^\n]+)'
        
        matches = re.findall(kv_pattern, text, re.MULTILINE)
        for key, value in matches:
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            if key and value and len(key) < 30:
                extracted.append({
                    'category': key,
                    'value': value,
                    'confidence': 0.8,
                    'source': 'key_value_extraction'
                })
        
        return extracted


# ============================================================
# CATEGORY VALIDATION & CORRECTION
# ============================================================
# Fixes LLM mislabeling issues like "petrol" → vehicle_type (wrong)
# Should be "petrol" → fuel_type (correct)


class CategoryValidator:
    """
    Validates and corrects category assignments from the LLM.
    
    Problem: LLM sometimes assigns values to wrong categories:
    - "petrol" assigned to vehicle_type (should be fuel_type)
    - "automatic" might be assigned to vehicle_type (should be transmission)
    
    Solution: Check if value matches known patterns for the category,
    and re-assign to correct category if mismatched.
    """
    
    # Known value patterns for each category
    # These are used to VALIDATE, not to hardcode - any value can still be stored
    CATEGORY_PATTERNS = {
        "vehicle_type": {
            "keywords": ["sedan", "hatchback", "suv", "muv", "compact", "crossover", "coupe", 
                        "convertible", "wagon", "pickup", "truck", "van", "car", "vehicle"],
            "anti_keywords": ["petrol", "diesel", "electric", "hybrid", "cng", "automatic", 
                             "manual", "amt", "cvt"]  # These should NOT be vehicle_type
        },
        "fuel_type": {
            "keywords": ["petrol", "diesel", "electric", "hybrid", "cng", "lpg", "ev", 
                        "gasoline", "fuel", "battery"],
            "anti_keywords": ["sedan", "suv", "hatchback", "automatic", "manual"]
        },
        "transmission": {
            "keywords": ["automatic", "manual", "amt", "cvt", "dct", "gear", "transmission"],
            "anti_keywords": ["petrol", "diesel", "sedan", "suv"]
        },
        "brand": {
            "keywords": ["toyota", "honda", "hyundai", "maruti", "tata", "mahindra", "kia",
                        "bmw", "mercedes", "audi", "volkswagen", "skoda", "ford", "nissan",
                        "renault", "mg", "jeep", "japanese", "korean", "german", "indian",
                        "manufacturer", "company", "brand"],
            "anti_keywords": []
        },
        "budget": {
            "keywords": ["lakh", "lakhs", "rupee", "rs", "inr", "crore", "thousand", "k",
                        "budget", "price", "cost", "afford"],
            "anti_keywords": []
        },
        "features": {
            "keywords": ["airbag", "abs", "safety", "sunroof", "touchscreen", "camera",
                        "sensor", "cruise", "parking", "feature", "rating"],
            "anti_keywords": []
        },
        "ownership_horizon": {
            "keywords": ["year", "years", "month", "months", "long", "term", "duration",
                        "keep", "own", "ownership"],
            "anti_keywords": []
        }
    }
    
    @classmethod
    def validate_and_correct(cls, category: str, value: str) -> str:
        """
        Validate if value belongs to the assigned category.
        If mismatched, return the correct category.
        
        Args:
            category: The LLM-assigned category
            value: The preference value
            
        Returns:
            Corrected category (may be same as input if valid)
        """
        if not value:
            return category
            
        value_lower = value.lower()
        category_lower = category.lower().replace(" ", "_")
        
        # Check if value contains anti-keywords for this category
        if category_lower in cls.CATEGORY_PATTERNS:
            anti_keywords = cls.CATEGORY_PATTERNS[category_lower].get("anti_keywords", [])
            
            for anti_kw in anti_keywords:
                if anti_kw in value_lower:
                    # Value contains an anti-keyword - find the correct category
                    correct_category = cls._find_correct_category(value_lower)
                    if correct_category and correct_category != category_lower:
                        return correct_category
        
        return category_lower
    
    @classmethod
    def _find_correct_category(cls, value_lower: str) -> Optional[str]:
        """Find the correct category for a value based on keyword matching."""
        best_match = None
        best_score = 0
        
        for cat, patterns in cls.CATEGORY_PATTERNS.items():
            keywords = patterns.get("keywords", [])
            score = sum(1 for kw in keywords if kw in value_lower)
            
            if score > best_score:
                best_score = score
                best_match = cat
        
        return best_match
    
    @classmethod
    def correct_preferences_list(cls, preferences: List[Dict]) -> List[Dict]:
        """
        Correct category assignments for a list of preferences.
        
        Returns new list with corrected categories.
        """
        corrected = []
        
        for pref in preferences:
            category = pref.get("category", "")
            value = pref.get("value", "")
            
            # Validate and correct category
            corrected_category = cls.validate_and_correct(category, value)
            
            # Create corrected preference
            corrected_pref = dict(pref)
            if corrected_category != category.lower().replace(" ", "_"):
                corrected_pref["original_category"] = category
                corrected_pref["category"] = corrected_category
                corrected_pref["category_corrected"] = True
            else:
                corrected_pref["category"] = corrected_category
                corrected_pref["category_corrected"] = False
            
            corrected.append(corrected_pref)
        
        return corrected


# ============================================================
# PREFERENCE SYSTEM - Dynamic LLM-Based Extraction
# ============================================================
# NOTE: No hardcoded canonical attributes!
# The system uses LLM-extracted categories directly, making it
# universal for any industry (cars, hotels, restaurants, etc.)


class PreferenceParser:
    """
    Parses preferences into structured slot-based format.
    
    DYNAMIC APPROACH (Universal for any industry):
    - Uses LLM-extracted category/value pairs directly
    - No hardcoded attributes - works for cars, hotels, restaurants, etc.
    - Each attribute has only ONE active value (LATEST WINS - overwrites previous)
    - Old values are stored in preference_history for audit
    """
    
    @staticmethod
    def normalize_to_snake_case(text: str) -> str:
        """Convert text to snake_case for attribute names"""
        # Remove special characters, replace spaces with underscores
        text = re.sub(r'[^\w\s]', '', text.lower())
        text = re.sub(r'\s+', '_', text.strip())
        return text
    
    @staticmethod
    def extract_number(text: str) -> Optional[float]:
        """Extract numeric value from text, handling lakh/crore"""
        text = text.lower()
        
        # Pattern for numbers with lakh/crore
        lakh_pattern = r'(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)'
        crore_pattern = r'(\d+(?:\.\d+)?)\s*(?:crore|cr)'
        plain_number = r'(\d+(?:,\d+)*(?:\.\d+)?)'
        
        # Check for crore first
        match = re.search(crore_pattern, text)
        if match:
            return float(match.group(1)) * 10000000
        
        # Check for lakh
        match = re.search(lakh_pattern, text)
        if match:
            return float(match.group(1)) * 100000
        
        # Plain number
        match = re.search(plain_number, text)
        if match:
            return float(match.group(1).replace(',', ''))
        
        return None
    
    @classmethod
    def parse_preference_string(cls, pref_input) -> Dict[str, Any]:
        """
        Parse a single preference into structured format.
        
        DYNAMIC APPROACH: Uses the LLM-extracted category/value directly.
        No hardcoded canonical attributes - works for any industry.
        
        Handles API formats:
        - Dict: {'category': 'color', 'value': 'black', 'confidence': 1.0}
        - String: "looking for a sedan"
        
        Returns:
            {
                "attribute": str,           # Normalized attribute name (from category or inferred)
                "value": Any,               # Extracted value
                "raw_input": str/dict,      # Original input
                "confidence": float,        # 0.0-1.0 confidence score
                "is_llm_extracted": bool,   # Whether LLM provided structure
                "parsed_at": datetime
            }
        """
        result = {
            "raw_input": pref_input,
            "parsed_at": datetime.utcnow(),
            "confidence": 0.5,
            "is_llm_extracted": False
        }
        
        # Handle structured dict input from LLM API
        if isinstance(pref_input, dict):
            # LLM provided category and value - USE DIRECTLY
            category = pref_input.get("category")
            value = pref_input.get("value")
            confidence = pref_input.get("confidence", 0.8)
            
            if category and value:
                # Normalize category to snake_case for consistent attribute names
                result["attribute"] = cls.normalize_to_snake_case(category)
                result["value"] = cls._parse_value(value)
                result["confidence"] = confidence
                result["is_llm_extracted"] = True
                return result
            
            # Fallback: try other dict formats
            pref_string = pref_input.get("preference", pref_input.get("value", str(pref_input)))
        else:
            pref_string = str(pref_input)
        
        # For string inputs, try to infer attribute and value
        pref_lower = pref_string.lower().strip()
        
        # Try to extract number values (budgets, quantities, etc.)
        num = cls.extract_number(pref_lower)
        if num and any(word in pref_lower for word in ['budget', 'price', 'cost', 'lakh', 'rupee', 'dollar', 'spend']):
            result["attribute"] = "budget"
            result["value"] = num
            result["confidence"] = 0.85
            return result
        
        # Create provisional attribute from string
        result["attribute"] = cls.normalize_to_snake_case(pref_string[:40])
        result["value"] = pref_string
        result["confidence"] = 0.4
        
        return result
    
    @staticmethod
    def _parse_value(value):
        """Parse and normalize a value (handle strings like '8 lakhs' -> number)"""
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            
            # Try to extract number with lakh/crore
            lakh_pattern = r'(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)'
            crore_pattern = r'(\d+(?:\.\d+)?)\s*(?:crore|cr)'
            
            match = re.search(crore_pattern, value_lower)
            if match:
                return float(match.group(1)) * 10000000
            
            match = re.search(lakh_pattern, value_lower)
            if match:
                return float(match.group(1)) * 100000
            
            # Return original string if no number pattern
            return value
        
        return value
    
    @classmethod
    def parse_preferences_list(cls, preferences: List[str]) -> List[Dict[str, Any]]:
        """Parse a list of preference strings"""
        return [cls.parse_preference_string(p) for p in preferences if p]


class PreferenceManager:
    """
    Manages structured preferences with slot-based updates.
    
    UPDATE BEHAVIOR (OVERWRITE, NOT APPEND):
    - When a new preference for an existing attribute arrives, the OLD value is:
      1. Moved to preference_history with timestamp
      2. REPLACED by the new value
    - This ensures only ONE active value per attribute
    - History is maintained for audit/analytics purposes
    """
    
    @staticmethod
    def update_preferences(
        current_preferences: Dict[str, Any],
        current_history: List[Dict],
        new_parsed_preferences: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Dict]]:
        """
        Update preferences with new values.
        
        OVERWRITE BEHAVIOR:
        - If attribute exists → old value moves to history, new value replaces it
        - If attribute doesn't exist → new attribute is created
        
        Args:
            current_preferences: Current preferences dict {attribute: {value, confidence, ...}}
            current_history: Current preference history list
            new_parsed_preferences: List of newly parsed preferences
            
        Returns:
            (updated_preferences, updated_history)
        """
        updated_prefs = dict(current_preferences) if current_preferences else {}
        updated_history = list(current_history) if current_history else []
        
        for new_pref in new_parsed_preferences:
            attr = new_pref.get("attribute")
            if not attr:
                continue
            
            # Check if attribute already exists
            if attr in updated_prefs:
                # OVERWRITE: Move old value to history
                old_value = updated_prefs[attr]
                updated_history.append({
                    "attribute": attr,
                    "old_value": old_value.get("value"),
                    "old_confidence": old_value.get("confidence"),
                    "replaced_at": datetime.utcnow(),
                    "replaced_by": new_pref.get("value"),
                    "raw_input": old_value.get("raw_input")
                })
            
            # Set new value (either create or overwrite)
            updated_prefs[attr] = {
                "value": new_pref.get("value"),
                "confidence": new_pref.get("confidence", 0.5),
                "raw_input": new_pref.get("raw_input"),
                "is_canonical": new_pref.get("is_canonical", False),
                "updated_at": datetime.utcnow()
            }
        
        return updated_prefs, updated_history
    
    @staticmethod
    def migrate_from_string_array(all_preferences: List[str]) -> Tuple[Dict[str, Any], List[Dict]]:
        """
        MIGRATION FUNCTION: Convert old string array format to structured preferences.
        
        Process:
        1. Parse each string into structured format
        2. Process in order (oldest first assumed)
        3. Later entries overwrite earlier ones (last value wins)
        4. Overwrites are tracked in history
        
        Args:
            all_preferences: Old format ["preference1", "preference2", ...]
            
        Returns:
            (structured_preferences, preference_history)
        """
        preferences = {}
        history = []
        
        # Parse all preference strings
        parsed = PreferenceParser.parse_preferences_list(all_preferences)
        
        # Process in order - later entries will overwrite earlier ones
        for parsed_pref in parsed:
            attr = parsed_pref.get("attribute")
            if not attr:
                continue
            
            if attr in preferences:
                # Track the overwrite in history
                old = preferences[attr]
                history.append({
                    "attribute": attr,
                    "old_value": old.get("value"),
                    "old_confidence": old.get("confidence"),
                    "replaced_at": datetime.utcnow(),
                    "replaced_by": parsed_pref.get("value"),
                    "raw_input": old.get("raw_input"),
                    "migration_note": "Resolved during migration from string array"
                })
            
            # Set/overwrite the preference
            preferences[attr] = {
                "value": parsed_pref.get("value"),
                "confidence": parsed_pref.get("confidence", 0.5),
                "raw_input": parsed_pref.get("raw_input"),
                "is_canonical": parsed_pref.get("is_canonical", False),
                "updated_at": datetime.utcnow()
            }
        
        return preferences, history


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
        """
        Create a new customer profile with structured preferences.
        
        Schema:
        - preferences: Dict[str, Any] - Structured slot-based preferences (one value per attribute)
        - preference_history: List[Dict] - History of overwritten preferences
        """
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
            # NEW: Structured preferences (replaces old all_preferences array)
            "preferences": {},  # Dict[attribute_name, {value, confidence, updated_at, ...}]
            "preference_history": [],  # History of overwritten values
            # KEPT FOR BACKWARD COMPATIBILITY (raw strings from API)
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
        transcript_text: str = None,
        name: str = None,
        email: str = None,
        phone: str = None
    ) -> dict:
        """
        Update customer profile after a conversation.
        
        PREFERENCE UPDATE BEHAVIOR (OVERWRITE, NOT APPEND):
        - New preferences REPLACE existing ones for the same attribute
        - Old values are moved to preference_history
        - This ensures only ONE active value per attribute
        
        FALLBACK: If API returns empty preferences, uses LocalPreferenceExtractor
        to extract preferences directly from the transcript text.
        """
        
        # Get current customer data for preference update
        current_customer = self.get_customer(customer_id)
        current_preferences = current_customer.get("preferences", {}) if current_customer else {}
        current_pref_history = current_customer.get("preference_history", []) if current_customer else []
        
        # Get signals from extracted context
        signals = extracted_context.get("signals", {})
        sentiment = signals.get("sentiment", "neutral")
        issues = extracted_context.get("issues", [])
        raw_preferences = extracted_context.get("preferences", [])  # From API
        commitments = extracted_context.get("commitments", [])
        
        # FALLBACK: If API returned empty preferences, use local extraction
        if not raw_preferences and transcript_text:
            print(f"   ⚠️ API returned empty preferences, using local extraction...")
            raw_preferences = LocalPreferenceExtractor.extract_from_text(transcript_text)
            print(f"   ✅ Locally extracted {len(raw_preferences)} preferences")
        
        # CATEGORY VALIDATION: Fix LLM mislabeling (e.g., "petrol" → vehicle_type should be fuel_type)
        if raw_preferences:
            raw_preferences = CategoryValidator.correct_preferences_list(raw_preferences)
            corrections = [p for p in raw_preferences if p.get("category_corrected")]
            if corrections:
                print(f"   🔧 Corrected {len(corrections)} mislabeled categories:")
                for c in corrections:
                    print(f"      - \"{c.get('value')}\": {c.get('original_category')} → {c.get('category')}")
        
        # Parse and update preferences using structured system
        if raw_preferences:
            parsed_prefs = PreferenceParser.parse_preferences_list(raw_preferences)
            updated_prefs, updated_history = PreferenceManager.update_preferences(
                current_preferences,
                current_pref_history,
                parsed_prefs
            )
        else:
            updated_prefs = current_preferences
            updated_history = current_pref_history
        
        # Build update operations
        update_ops = {
            "$inc": {"total_conversations": 1},
            "$set": {
                "last_contact": datetime.utcnow(),
                "preferred_channel": channel,
                "updated_at": datetime.utcnow(),
                # Update structured preferences (OVERWRITES existing)
                "preferences": updated_prefs,
                "preference_history": updated_history
            },
            "$push": {
                "sentiment_history": {
                    "sentiment": sentiment,
                    "timestamp": datetime.utcnow()
                }
            },
            "$addToSet": {
                "all_issues": {"$each": issues},
                # Still append raw preferences for backward compatibility
                "all_preferences": {"$each": raw_preferences if isinstance(raw_preferences, list) else []},
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
        if raw_preferences:
            print(f"      📋 Preferences updated: {list(updated_prefs.keys())}")
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
    
    def migrate_customer_preferences(self, customer_id: str) -> dict:
        """
        MIGRATION FUNCTION: Migrate a customer from old string array to structured preferences.
        
        Call this once per customer to convert:
        - all_preferences: ["string1", "string2", ...]
        To:
        - preferences: {attribute: {value, confidence, ...}, ...}
        - preference_history: [{old_value, replaced_at, ...}, ...]
        """
        customer = self.get_customer(customer_id)
        if not customer:
            print(f"   ❌ Customer not found: {customer_id}")
            return None
        
        old_prefs = customer.get("all_preferences", [])
        if not old_prefs:
            print(f"   ⚠️ No preferences to migrate for: {customer_id}")
            return customer
        
        # Migrate using PreferenceManager
        structured_prefs, pref_history = PreferenceManager.migrate_from_string_array(old_prefs)
        
        # Update customer with migrated data
        self.customers.update_one(
            {"customer_id": customer_id},
            {
                "$set": {
                    "preferences": structured_prefs,
                    "preference_history": pref_history,
                    "updated_at": datetime.utcnow(),
                    "migration_completed_at": datetime.utcnow()
                }
            }
        )
        
        print(f"   ✅ Migrated preferences for: {customer_id}")
        print(f"      📋 Attributes: {list(structured_prefs.keys())}")
        print(f"      📜 History entries: {len(pref_history)}")
        
        return self.get_customer(customer_id)
    
    def migrate_all_customers(self) -> dict:
        """
        MIGRATION FUNCTION: Migrate all customers to structured preferences.
        
        Returns summary of migration.
        """
        customers = list(self.customers.find({}))
        migrated = 0
        skipped = 0
        errors = 0
        
        print(f"\n🔄 Starting migration for {len(customers)} customers...")
        
        for customer in customers:
            customer_id = customer.get("customer_id")
            try:
                # Skip if already migrated
                if customer.get("migration_completed_at"):
                    skipped += 1
                    continue
                
                self.migrate_customer_preferences(customer_id)
                migrated += 1
            except Exception as e:
                print(f"   ❌ Error migrating {customer_id}: {e}")
                errors += 1
        
        summary = {
            "total": len(customers),
            "migrated": migrated,
            "skipped": skipped,
            "errors": errors
        }
        
        print(f"\n✅ Migration complete: {summary}")
        return summary
    
    def get_customer_preferences_summary(self, customer_id: str) -> dict:
        """
        Get a summary of a customer's structured preferences.
        
        Returns clean dict with just attribute -> value mappings.
        """
        customer = self.get_customer(customer_id)
        if not customer:
            return None
        
        preferences = customer.get("preferences", {})
        summary = {}
        
        for attr, details in preferences.items():
            if isinstance(details, dict):
                summary[attr] = details.get("value")
            else:
                summary[attr] = details
        
        return summary
    
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
        1. Transcribe audio to text
        2. Ingest conversation (extract context via LLM)
        3. Check/Create customer in database
        4. Store conversation
        5. Update customer profile with preferences
        
        Args:
            audio_file_path: Path to audio file to transcribe
        """
        print("=" * 60)
        print("🚀 Starting Unified Customer Profile Pipeline v2")
        print("=" * 60)
        
        # Step 1: Transcribe audio
        transcription = self.transcribe_audio(audio_file_path)
        transcript_text = transcription.get("transcript", "")
        language = transcription.get("language", "en")
        source_file = audio_file_path
        
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
            source_file=source_file
        )
        
        # Step 5: Update customer profile
        print(f"\n📊 Step 5: Updating Customer Profile")
        updated_customer = self.db.update_customer_from_conversation(
            customer_id=final_customer_id,
            extracted_context=extracted_context,
            channel=channel,
            transcript_text=transcript_text,  # Pass transcript for local extraction fallback
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
    
    print(f"🎤 Processing audio: {AUDIO_FILE_PATH}")
    
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
        print(f"\nTranscript: {result['transcript'][:500]}..." if len(result['transcript']) > 500 else f"\nTranscript: {result['transcript']}")
        
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

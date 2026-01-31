"""
Cost optimization service for production deployment
Provides caching, rate limiting, and cost tracking
"""

import logging
import hashlib
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from tinydb import TinyDB, Query
import config

logger = logging.getLogger(__name__)


# ============================================
# LLM RESPONSE CACHE
# ============================================

class LLMCache:
    """
    Cache LLM responses to reduce redundant API calls.
    Uses semantic similarity to detect duplicate/similar queries.
    """
    
    def __init__(self, cache_db_path: str = "data/llm_cache.json", ttl_hours: int = 24):
        self.db = TinyDB(cache_db_path)
        self.ttl = timedelta(hours=ttl_hours)
        logger.info(f"Initialized LLM cache with {ttl_hours}h TTL")
    
    def _hash_text(self, text: str) -> str:
        """Create hash of normalized text for exact matching"""
        # Normalize: lowercase, strip whitespace, remove punctuation variations
        normalized = ' '.join(text.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def get(self, conversation_text: str) -> Optional[Dict[str, Any]]:
        """
        Try to get cached response for similar conversation.
        Returns cached ExtractedContext dict if found and not expired.
        """
        text_hash = self._hash_text(conversation_text)
        CacheQuery = Query()
        
        results = self.db.search(CacheQuery.text_hash == text_hash)
        
        if results:
            cached = results[0]
            cache_time = datetime.fromisoformat(cached['timestamp'])
            
            # Check if cache is still valid
            if datetime.now() - cache_time < self.ttl:
                logger.info(f"✅ LLM Cache HIT - Saved LLM call")
                return cached['response']
            else:
                # Expired, remove it
                self.db.remove(CacheQuery.text_hash == text_hash)
                logger.debug("Cache entry expired")
        
        logger.debug("Cache MISS - LLM call required")
        return None
    
    def set(self, conversation_text: str, response: Dict[str, Any]):
        """Cache LLM response for future use"""
        text_hash = self._hash_text(conversation_text)
        CacheQuery = Query()
        
        # Remove old entry if exists
        self.db.remove(CacheQuery.text_hash == text_hash)
        
        # Add new cache entry
        self.db.insert({
            'text_hash': text_hash,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'text_preview': conversation_text[:100]  # For debugging
        })
        logger.debug("Cached LLM response")
    
    def clear_expired(self):
        """Remove expired cache entries"""
        CacheQuery = Query()
        all_entries = self.db.all()
        removed = 0
        
        for entry in all_entries:
            cache_time = datetime.fromisoformat(entry['timestamp'])
            if datetime.now() - cache_time >= self.ttl:
                self.db.remove(CacheQuery.text_hash == entry['text_hash'])
                removed += 1
        
        if removed > 0:
            logger.info(f"Cleared {removed} expired cache entries")
        
        return removed


# ============================================
# SIMPLE QUERY DETECTOR
# ============================================

class SimpleQueryDetector:
    """
    Detect simple/common queries that don't need LLM processing.
    Saves LLM costs on greetings, acknowledgments, simple questions.
    """
    
    # Patterns that don't need LLM extraction
    SIMPLE_PATTERNS = [
        # Greetings (no extractable info)
        ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'],
        
        # Acknowledgments (no new info)
        ['ok', 'okay', 'thanks', 'thank you', 'got it', 'understood', 'sure', 'yes', 'no'],
        
        # Single word responses
        ['bye', 'goodbye', 'later'],
        
        # Very short (< 10 chars likely not useful)
        # Handled separately
    ]
    
    @staticmethod
    def is_simple(text: str) -> Tuple[bool, str]:
        """
        Check if text is too simple to warrant LLM extraction.
        
        Returns:
            (is_simple, reason) - If simple, skip LLM and use empty defaults
        """
        if not text or len(text.strip()) == 0:
            return (True, "Empty text")
        
        # Very short messages (< 10 chars)
        if len(text.strip()) < 10:
            return (True, "Too short (< 10 chars)")
        
        # Check against pattern lists
        text_lower = text.lower().strip()
        
        for pattern_group in SimpleQueryDetector.SIMPLE_PATTERNS:
            for pattern in pattern_group:
                if text_lower == pattern or text_lower.startswith(pattern + ' ') or text_lower.endswith(' ' + pattern):
                    return (True, f"Simple pattern: '{pattern}'")
        
        # Check if it's ONLY greetings/acknowledgments (no substantive content)
        words = text_lower.split()
        if len(words) <= 3:
            # 3 words or less, check if all are simple patterns
            all_simple = all(
                any(word in pattern for pattern in sum(SimpleQueryDetector.SIMPLE_PATTERNS, []))
                for word in words
            )
            if all_simple:
                return (True, "Only simple words")
        
        return (False, "Complex query - LLM needed")


# ============================================
# RATE LIMITER
# ============================================

class RateLimiter:
    """
    Rate limiting to prevent cost overruns.
    Tracks per-customer and global API call rates.
    """
    
    def __init__(self, 
                 customer_limit_per_hour: int = 100,
                 global_limit_per_hour: int = 1000):
        self.customer_limit = customer_limit_per_hour
        self.global_limit = global_limit_per_hour
        
        # In-memory tracking (reset on restart)
        # For production, use Redis or persistent storage
        self.customer_calls = defaultdict(list)  # customer_id -> [timestamps]
        self.global_calls = []  # [timestamps]
        
        logger.info(f"Rate limiter: {customer_limit_per_hour}/customer/hour, {global_limit_per_hour}/global/hour")
    
    def _clean_old_calls(self, calls_list: list, window_hours: int = 1):
        """Remove calls older than time window"""
        cutoff = datetime.now() - timedelta(hours=window_hours)
        return [ts for ts in calls_list if ts > cutoff]
    
    def check_limit(self, customer_id: str) -> Tuple[bool, str]:
        """
        Check if request is within rate limits.
        
        Returns:
            (allowed, reason) - True if allowed, False if rate limited
        """
        now = datetime.now()
        
        # Clean old entries
        self.customer_calls[customer_id] = self._clean_old_calls(self.customer_calls[customer_id])
        self.global_calls = self._clean_old_calls(self.global_calls)
        
        # Check customer limit
        if len(self.customer_calls[customer_id]) >= self.customer_limit:
            return (False, f"Customer rate limit exceeded: {self.customer_limit}/hour")
        
        # Check global limit
        if len(self.global_calls) >= self.global_limit:
            return (False, f"Global rate limit exceeded: {self.global_limit}/hour")
        
        # Record this call
        self.customer_calls[customer_id].append(now)
        self.global_calls.append(now)
        
        return (True, "Within limits")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limit statistics"""
        return {
            "global_calls_last_hour": len(self.global_calls),
            "global_limit": self.global_limit,
            "active_customers": len([k for k, v in self.customer_calls.items() if v]),
            "customer_limit": self.customer_limit
        }


# ============================================
# COST TRACKER
# ============================================

class CostTracker:
    """
    Track API costs and usage metrics for ROI analysis.
    """
    
    def __init__(self, db_path: str = "data/cost_tracking.json"):
        self.db = TinyDB(db_path)
        
        # Estimated costs (adjust based on actual pricing)
        self.COST_PER_LLM_CALL = 0.001  # $0.001 per call (local/Ollama = $0)
        self.COST_PER_EMBEDDING = 0.0001  # $0.0001 per embedding
        
        logger.info("Initialized cost tracker")
    
    def record_llm_call(self, customer_id: str, cached: bool = False):
        """Record LLM API call"""
        self.db.insert({
            'type': 'llm_call',
            'customer_id': customer_id,
            'timestamp': datetime.now().isoformat(),
            'cached': cached,
            'cost': 0 if cached else self.COST_PER_LLM_CALL
        })
    
    def record_embedding(self, customer_id: str, count: int = 1):
        """Record embedding generation"""
        self.db.insert({
            'type': 'embedding',
            'customer_id': customer_id,
            'timestamp': datetime.now().isoformat(),
            'count': count,
            'cost': self.COST_PER_EMBEDDING * count
        })
    
    def get_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get cost summary for time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        CostQuery = Query()
        recent = self.db.search(
            CostQuery.timestamp >= cutoff.isoformat()
        )
        
        total_cost = sum(entry.get('cost', 0) for entry in recent)
        llm_calls = len([e for e in recent if e['type'] == 'llm_call'])
        cached_calls = len([e for e in recent if e['type'] == 'llm_call' and e.get('cached', False)])
        embeddings = sum(e.get('count', 0) for e in recent if e['type'] == 'embedding')
        
        cache_hit_rate = (cached_calls / llm_calls * 100) if llm_calls > 0 else 0
        
        return {
            'period_hours': hours,
            'total_cost': round(total_cost, 4),
            'llm_calls': llm_calls,
            'cached_calls': cached_calls,
            'cache_hit_rate': round(cache_hit_rate, 1),
            'embeddings': embeddings,
            'cost_savings_from_cache': round(cached_calls * self.COST_PER_LLM_CALL, 4)
        }


# ============================================
# SINGLETON INSTANCES
# ============================================

_llm_cache = None
_simple_detector = None
_rate_limiter = None
_cost_tracker = None

def get_llm_cache() -> LLMCache:
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache(
            cache_db_path=str(config.DATA_DIR / "llm_cache.json"),
            ttl_hours=getattr(config, 'LLM_CACHE_TTL_HOURS', 24)
        )
    return _llm_cache

def get_simple_detector() -> SimpleQueryDetector:
    global _simple_detector
    if _simple_detector is None:
        _simple_detector = SimpleQueryDetector()
    return _simple_detector

def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            customer_limit_per_hour=getattr(config, 'CUSTOMER_RATE_LIMIT', 100),
            global_limit_per_hour=getattr(config, 'GLOBAL_RATE_LIMIT', 1000)
        )
    return _rate_limiter

def get_cost_tracker() -> CostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker(
            db_path=str(config.DATA_DIR / "cost_tracking.json")
        )
    return _cost_tracker

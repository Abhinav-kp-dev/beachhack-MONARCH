"""
Unified AI Service Adapter

This adapter provides a single interface that switches between:
- Production LLM (OpenAI) when USE_PRODUCTION_LLM=True
- Mock LLM (for testing) when USE_PRODUCTION_LLM=False

Usage:
    from app.services.ai_adapter import ai_adapter
    
    result = await ai_adapter.extract_context(content)
"""

from typing import Dict, Any
from app.core.config import settings


class AIServiceAdapter:
    """
    Adapter that switches between production and mock LLM services.
    
    This allows easy testing without API calls and seamless production deployment.
    """
    
    def __init__(self):
        self._service = None
    
    def _get_service(self):
        """Lazy load the appropriate service based on settings"""
        if self._service is None:
            if settings.USE_PRODUCTION_LLM and settings.OPENAI_API_KEY:
                from app.services.llm_service import production_llm_service
                self._service = production_llm_service
                print("✅ Using Production LLM (OpenAI)")
            else:
                from app.services.ai_service import ai_service
                self._service = ai_service
                print("⚠️  Using Mock LLM (set USE_PRODUCTION_LLM=True and OPENAI_API_KEY to use real LLM)")
        
        return self._service
    
    async def extract_context(self, content: str) -> Dict[str, Any]:
        """Extract structured context from conversation content"""
        return await self._get_service().extract_context(content)
    
    async def analyze_sentiment(self, content: str) -> str:
        """Analyze sentiment of the content"""
        return await self._get_service().analyze_sentiment(content)
    
    async def detect_intent(self, content: str) -> Dict[str, Any]:
        """Detect the primary intent with confidence score"""
        return await self._get_service().detect_intent(content)
    
    async def generate_interaction_summary(
        self,
        content: str,
        intent: Dict[str, Any],
        extracted_context: Dict[str, Any]
    ) -> str:
        """Generate a brief summary of the current interaction"""
        return await self._get_service().generate_interaction_summary(
            content, intent, extracted_context
        )
    
    async def update_unified_summary(
        self,
        existing_summary: str,
        new_interaction_summary: str,
        final_backend_state: Dict[str, Any] = None,
        open_tasks: list = None,
        pending_issues: list = None
    ) -> str:
        """Update unified summary incrementally using final backend state"""
        return await self._get_service().update_unified_summary(
            existing_summary,
            new_interaction_summary,
            final_backend_state,
            open_tasks,
            pending_issues
        )


# Singleton instance
ai_adapter = AIServiceAdapter()

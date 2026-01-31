from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Customer Intelligence System"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./customer_intelligence.db"
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "customer_intelligence"
    
    # AI Service
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    EXTERNAL_LLM_API_URL: str = "http://192.168.220.76:8000/conversation"
    EXTERNAL_SUMMARY_API_URL: str = "http://192.168.220.76:8000/summary"
    
    # Graph Engine Confidence Thresholds
    # Tune these based on your LLM's performance
    CONFIDENCE_HIGH: float = 0.80   # Auto-accept changes
    CONFIDENCE_MEDIUM: float = 0.55  # Move to pending review
    # Anything below MEDIUM is ignored
    
    # Feature Flags
    USE_PRODUCTION_LLM: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

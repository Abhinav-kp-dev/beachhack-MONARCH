"""
Configuration management for the application
Loads settings from environment variables with sensible defaults
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# Database paths
CUSTOMERS_DB = str(DATA_DIR / "customers.json")
CONVERSATIONS_DB = str(DATA_DIR / "conversations.json")
ACTIONS_DB = str(DATA_DIR / "actions.json")
AUDIT_LOG_DB = str(DATA_DIR / "audit_log.json")  # New: State change audit trail
FAISS_INDEX_PATH = str(DATA_DIR / "faiss.index")
TEXTS_STORE_PATH = str(DATA_DIR / "texts.json")

# AI Model settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu or cuda
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

# Memory settings
SEMANTIC_SEARCH_TOP_K = int(os.getenv("SEMANTIC_SEARCH_TOP_K", "5"))
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "2000"))

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS settings (for frontend)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# Cost Optimization Settings
LLM_CACHE_TTL_HOURS = int(os.getenv("LLM_CACHE_TTL_HOURS", "24"))  # Cache duration
CUSTOMER_RATE_LIMIT = int(os.getenv("CUSTOMER_RATE_LIMIT", "100"))  # Calls per customer per hour
GLOBAL_RATE_LIMIT = int(os.getenv("GLOBAL_RATE_LIMIT", "1000"))  # Total calls per hour
ENABLE_COST_OPTIMIZATION = os.getenv("ENABLE_COST_OPTIMIZATION", "true").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from app.core.config import settings
from app.api import ingest, context, inventory

app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time customer memory and context engine",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(context.router, tags=["Context"])
app.include_router(inventory.router, tags=["Actions"])

from app.db.mongodb import close_mongodb

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongodb()


@app.get("/health")
async def health_check():
    """System health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "conversation": "POST /conversation",
            "customer_context": "GET /customer/{id}/context",
            "transcribe": "POST /transcribe",
            "action_trigger": "POST /action/trigger"
        }
    }

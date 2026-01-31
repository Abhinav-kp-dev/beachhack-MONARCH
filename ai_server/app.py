"""
Context-Aware Customer Intelligence System - Main FastAPI Application
Complete backend API for customer conversation management with AI-powered context extraction
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from tinydb import Query
import logging
import os
import shutil

# Local imports
import config
from models import (
    CustomerProfile, Action, ConversationInput,
    TranscribeInput, ActionTriggerInput, ExtractedContext
)
from services.context_extraction import get_extraction_service
from services.customer_service import get_customer_service
from services.memory_service import get_memory_service
from services.action_service import get_action_service
from services.whisper_service import transcribe_audio
from services.cost_optimization import get_rate_limiter, get_cost_tracker
from utils.audio_utils import preprocess_audio

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Context-Aware Customer Intelligence System",
    description="Real-time customer memory and context engine for customer support",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
extraction_service = get_extraction_service()
customer_service = get_customer_service()
memory_service = get_memory_service()
action_service = get_action_service()
rate_limiter = get_rate_limiter()
cost_tracker = get_cost_tracker()

logger.info("All services initialized successfully")


@app.get("/health")
def health_check():
    """
    Health check endpoint
    Returns system status and available services
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "extraction": "ready",
            "memory": "ready",
            "customer": "ready",
            "action": "ready",
            "transcription": "ready"
        },
        "models": {
            "llama": config.OLLAMA_MODEL,
            "whisper": config.WHISPER_MODEL,
            "embeddings": config.EMBEDDING_MODEL
        }
    }


@app.post("/conversation", response_model=Dict[str, Any])
async def ingest_conversation(conversation_input: ConversationInput):
    """
    Ingest a new customer conversation with AUTHORITY SEPARATION
    
    NEW FLOW (deterministic, authority-separated):
    1. Get/Create customer (state machine)
    2. Store evidence (raw conversation for audit)
    3. Extract facts (LLM = compiler, transient output)
    4. Update state (deterministic validation)
    5. Recommend action (rule-based, no AI)
    6. Index for search (semantic, display only)
    
    AUTHORITY MODEL:
    - ConversationEvidence: Raw data (audit trail)
    - ExtractedContext: Transient facts (no authority)
    - CustomerProfile: Single source of truth
    - Action: Deterministic rules with provenance
    
    Args:
        conversation_input: Conversation details
        
    Returns:
        Conversation record with extracted context and rule-based action
    """
    try:
        logger.info(f"Ingesting new {conversation_input.channel} conversation")
        
        # STEP 0: Rate limiting check (cost control)
        # Note: Check will happen after customer creation for new customers
        
        # STEP 1: Get or create customer (STATE MACHINE)
        is_new_customer = False
        
        if conversation_input.customer_id:
            # User provided a customer ID - check if it exists
            customer = customer_service.get_customer(conversation_input.customer_id)
            if not customer:
                # Customer ID provided but doesn't exist - create new with this ID
                logger.info(f"Creating new customer with provided ID: {conversation_input.customer_id}")
                customer, was_created = customer_service.create_customer(
                    customer_id=conversation_input.customer_id,
                    name=conversation_input.customer_name,
                    email=conversation_input.customer_email,
                    phone=conversation_input.customer_phone
                )
                is_new_customer = was_created
            else:
                # Customer exists - use existing customer
                logger.info(f"Found existing customer: {customer.customer_id}")
                is_new_customer = False
        else:
            # No customer ID provided - create new customer (auto-generate ID)
            logger.info("Creating new customer with auto-generated ID")
            customer, was_created = customer_service.create_customer(
                name=conversation_input.customer_name,
                email=conversation_input.customer_email,
                phone=conversation_input.customer_phone
            )
            is_new_customer = was_created
        
        logger.info(f"Processing conversation for customer: {customer.customer_id} (new={is_new_customer})")
        
        # Rate limiting check (after customer is identified)
        allowed, reason = rate_limiter.check_limit(customer.customer_id)
        if not allowed:
            logger.warning(f"Rate limit exceeded for {customer.customer_id}: {reason}")
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {reason}")
        
        # STEP 2: Store raw evidence for audit trail
        conversation_id = memory_service.add_evidence(
            customer_id=customer.customer_id,
            text=conversation_input.text,
            channel=conversation_input.channel
        )
        logger.info(f"Stored evidence: {conversation_id}")
        
        # STEP 3: Extract facts (LLM = COMPILER, transient, no authority)
        # Now with cost optimization (caching, simple query detection)
        try:
            extracted_context = extraction_service.extract_context(
                conversation_input.text,
                customer_id=customer.customer_id
            )
            if extracted_context is None:
                raise ValueError("Extraction returned None")
        except Exception as e:
            logger.warning(f"Context extraction failed: {e}, using empty defaults")
            extracted_context = ExtractedContext(
                preferences=[],
                issues=[],
                commitments=[],
                signals={}
            )
        
        logger.info(f"Extracted context: {len(extracted_context.preferences)} prefs, {len(extracted_context.issues)} issues")
        
        # STEP 4: Update state (DETERMINISTIC VALIDATION)
        customer = customer_service.update_customer_from_facts(
            customer_id=customer.customer_id,
            extracted_context=extracted_context,
            conversation_id=conversation_id
        )
        logger.info(f"Updated customer state deterministically")
        
        # STEP 5: Recommend action (RULE-BASED, deterministic with provenance)
        recommended_action = action_service.recommend_action(customer)
        logger.info(f"Rule-based action: {recommended_action['action_type']} (Rule: {recommended_action['rule_id']})")
        
        # STEP 6: Index for semantic search (DISPLAY ONLY)
        memory_service.add_to_search_index(
            conversation_id=conversation_id,
            customer_id=customer.customer_id,
            text=conversation_input.text
        )
        logger.info(f"Indexed for search")
        
        # Get latest customer state for response
        customer = customer_service.get_customer(customer.customer_id)
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "customer_id": customer.customer_id,
            "is_new_customer": is_new_customer,
            "customer": {
                "customer_id": customer.customer_id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "preferences_count": sum(len(v) for v in customer.preferences.values()) if isinstance(customer.preferences, dict) else len(customer.preferences),
                "issues_count": len([i for i in customer.issues if i.status.lower() == "open"]),
                "commitments_count": len(customer.commitments),
                "total_interactions": customer.interaction_count
            },
            "extracted_context": {
                "preferences": [p.model_dump() if hasattr(p, 'model_dump') else p for p in extracted_context.preferences],
                "issues": [i.model_dump() if hasattr(i, 'model_dump') else i for i in extracted_context.issues],
                "commitments": [c.model_dump() if hasattr(c, 'model_dump') else c for c in extracted_context.commitments],
                "signals": extracted_context.signals
            },
            "recommended_action": {
                "type": recommended_action['action_type'],
                "priority": recommended_action['priority'],
                "details": recommended_action['details'],
                "rule_id": recommended_action['rule_id'],
                "rule_reason": recommended_action['reason']
            },
            "authority_flow": "Evidence → Facts → State → Rules → Search"
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customer/{customer_id}/context", response_model=Dict[str, Any])
async def get_customer_context(customer_id: str, include_audit: bool = False):
    """
    Retrieve full context for a customer with AUTHORITY SEPARATION
    
    AUTHORITY MODEL:
    - customer_profile: Authoritative state (single source of truth)
    - recent_evidence: Raw conversations (audit trail, for display)
    - search_results: Semantic search (⚠️ DISPLAY ONLY, no authority)
    - audit_trail: State change log (optional, for debugging)
    
    NO AI SUMMARIES - Agent uses state + evidence directly
    
    Args:
        customer_id: Customer identifier
        include_audit: Include state change audit trail
        
    Returns:
        Complete customer context with clear authority boundaries
    """
    try:
        logger.info(f"Retrieving context for customer: {customer_id}")
        
        # 1. Get customer profile (AUTHORITATIVE STATE)
        customer = customer_service.get_customer(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # 2. Get recent evidence (RAW DATA for display)
        recent_evidence = memory_service.get_customer_evidence(customer_id, limit=5)
        
        # 3. Get semantic search results (DISPLAY ONLY)
        # Build query from preferences (handle both dict and list formats)
        if customer.preferences:
            if isinstance(customer.preferences, dict):
                # Flatten structured preferences for search query
                all_prefs = []
                for category, values in customer.preferences.items():
                    all_prefs.extend(values)
                query_text = " ".join(all_prefs) if all_prefs else f"customer {customer_id}"
            else:
                # Legacy list format
                query_text = " ".join(customer.preferences)
        else:
            query_text = f"customer {customer_id}"
        search_results = memory_service.search_similar(query_text, customer_id=customer_id, k=3)
        
        # 4. Get audit trail (optional, for debugging)
        audit_trail = None
        if include_audit:
            audit_trail = customer_service.get_audit_trail(customer_id, limit=20)
        
        # 5. Calculate context quality score and time saved
        from utils.metrics import calculate_context_quality_score, calculate_time_saved
        context_quality = calculate_context_quality_score(customer)
        time_saved = calculate_time_saved(customer)
        
        # 6. Generate AI-powered recommendations (R006)
        from services.action_service import ActionRules
        recommendations = ActionRules.generate_recommendations(customer)
        
        logger.info(f"Context retrieved successfully for customer: {customer_id}")
        
        response = {
            "authority_model": "State + Evidence + Search (separated)",
            "customer_profile": {
                "customer_id": customer.customer_id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "preferences": customer.preferences,
                "issues": [
                    {
                        "description": issue.description,
                        "status": issue.status,
                        "reported_at": issue.reported_at.isoformat(),
                        "conversation_id": getattr(issue, 'conversation_id', None)
                    }
                    for issue in customer.issues
                ],
                "commitments": customer.commitments,
                "last_interaction": customer.last_interaction.isoformat() if customer.last_interaction else None,
                "created_at": customer.created_at.isoformat(),
                "updated_at": customer.updated_at.isoformat()
            },
            "recent_evidence": [
                {
                    "conversation_id": e.conversation_id,
                    "timestamp": e.timestamp.isoformat(),
                    "channel": e.channel,
                    "raw_text": e.raw_text[:200] + "..." if len(e.raw_text) > 200 else e.raw_text
                }
                for e in recent_evidence
            ],
            "search_results": {
                "warning": "⚠️ DISPLAY ONLY - Not authoritative, use for context hints only",
                "results": search_results
            },
            "statistics": {
                "total_preferences": sum(len(v) for v in customer.preferences.values()) if isinstance(customer.preferences, dict) else len(customer.preferences),
                "open_issues": len([i for i in customer.issues if i.status.lower() == "open"]),
                "total_commitments": len(customer.commitments),
                "evidence_count": len(recent_evidence)
            },
            "context_quality": context_quality,
            "time_saved": time_saved,
            "recommendations": recommendations
        }
        
        if audit_trail:
            response["audit_trail"] = audit_trail
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve customer context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe", response_model=Dict[str, Any])
async def transcribe(
    file: UploadFile = File(...), 
    customer_id: Optional[str] = Form(None),
    customer_name: Optional[str] = Form(None),
    customer_email: Optional[str] = Form(None),
    customer_phone: Optional[str] = Form(None)
):
    """
    Transcribe audio file to text using Whisper and create full customer context
    
    COMPLETE WORKFLOW:
    1. Transcribe audio to text
    2. Use provided customer_id if given (existing customer), or auto-generate (new customer)
    3. Store raw transcribed text as evidence in database
    4. Extract context (preferences, issues, commitments) using LLM
    5. Store extracted context in customer profile with validation
    6. Index conversation for semantic search
    7. Return comprehensive response with all details
    
    Args:
        file: Audio file upload (multipart/form-data)
        customer_id: Optional customer ID (Form field) - if provided, adds to existing customer
        customer_name: Optional customer name (Form field) - for new customers
        customer_email: Optional customer email (Form field) - for new customers
        customer_phone: Optional customer phone (Form field) - for new customers
        
    Returns:
        Complete response with transcript, customer_id, is_new_customer flag, extracted context, and customer details
    """
    try:
        logger.info(f"Transcribing audio file: {file.filename}")
        logger.info(f"Received customer_id: {customer_id}, name: {customer_name}, email: {customer_email}, phone: {customer_phone}")
        
        # Save uploaded file
        file_path = os.path.join(config.UPLOADS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Transcribe using Whisper
        result = transcribe_audio(file_path, return_timestamps=False)
        transcript_text = result.get("text", "")
        
        logger.info(f"Transcription completed: {len(transcript_text)} characters")
        
        # Build response with transcript
        response = {
            "status": "success",
            "transcript": transcript_text,
            "language": result.get("language", "unknown")
        }
        
        # STEP 1: Create conversation from transcript
        # The ingest_conversation function will handle customer lookup/creation and return is_new_customer
        conv_input = ConversationInput(
            customer_id=customer_id,  # May be None for new customers
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            channel="call",
            text=transcript_text
        )
        conv_result = await ingest_conversation(conv_input)
        
        # STEP 2: Build comprehensive response using results from ingest_conversation
        response["customer_id"] = conv_result.get("customer_id")
        response["is_new_customer"] = conv_result.get("is_new_customer", False)
        response["conversation_id"] = conv_result.get("conversation_id")
        response["extracted_context"] = conv_result.get("extracted_context", {})
        response["recommended_action"] = conv_result.get("recommended_action", {})
        response["indexed_for_search"] = True
        
        logger.info(f"Transcription completed for customer {response['customer_id']} (new={response['is_new_customer']})")
        
        # Add customer details
        customer = customer_service.get_customer(response["customer_id"])
        if customer:
            response["customer"] = {
                "customer_id": customer.customer_id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "preferences_count": sum(len(v) for v in customer.preferences.values()) if isinstance(customer.preferences, dict) else len(customer.preferences),
                "issues_count": len([i for i in customer.issues if i.status.lower() == "open"]),
                "commitments_count": len(customer.commitments),
                "total_interactions": customer.interaction_count
            }
        
        logger.info(f"Transcription and context extraction completed for customer {customer_id}")
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        return response
        
    except Exception as e:
        logger.error(f"Transcription workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/identify-customer", response_model=Dict[str, Any])
async def identify_customer(text: str, phone: Optional[str] = None, email: Optional[str] = None):
    """
    Identify if transcript/text mentions an existing customer or is a new customer
    
    INTELLIGENT IDENTIFICATION:
    1. Extract name, phone, email from text using LLM
    2. Search existing customers by:
       - Phone number (exact match)
       - Email (exact match)
       - Name (fuzzy match)
       - Semantic search on conversation history
    3. Return match confidence and customer details
    
    Args:
        text: Conversation text or transcript
        phone: Optional phone number to check
        email: Optional email to check
        
    Returns:
        Match result with customer_id if found, or indication it's a new customer
    """
    try:
        logger.info("Identifying customer from text and contact info")
        
        # STEP 1: Extract contact info from text using LLM
        extracted_info = extraction_service.extract_customer_info(text)
        
        # Merge with provided contact info (provided info takes priority)
        name = extracted_info.get("name", "")
        phone_extracted = phone or extracted_info.get("phone", "")
        email_extracted = email or extracted_info.get("email", "")
        
        logger.info(f"Extracted info - Name: {name}, Phone: {phone_extracted}, Email: {email_extracted}")
        
        # STEP 2: Search for existing customer
        all_customers = customer_service.get_all_customers()
        
        matched_customer = None
        match_confidence = 0.0
        match_reason = ""
        
        # Priority 1: Phone number exact match (highest confidence)
        if phone_extracted:
            for customer in all_customers:
                if customer.phone and customer.phone.replace("-", "").replace(" ", "") == phone_extracted.replace("-", "").replace(" ", ""):
                    matched_customer = customer
                    match_confidence = 1.0
                    match_reason = "phone_exact_match"
                    logger.info(f"Found customer by phone: {customer.customer_id}")
                    break
        
        # Priority 2: Email exact match (high confidence)
        if not matched_customer and email_extracted:
            for customer in all_customers:
                if customer.email and customer.email.lower() == email_extracted.lower():
                    matched_customer = customer
                    match_confidence = 0.95
                    match_reason = "email_exact_match"
                    logger.info(f"Found customer by email: {customer.customer_id}")
                    break
        
        # Priority 3: Name fuzzy match (medium confidence)
        if not matched_customer and name:
            from difflib import SequenceMatcher
            best_match_score = 0.0
            best_match_customer = None
            
            for customer in all_customers:
                if customer.name:
                    similarity = SequenceMatcher(None, name.lower(), customer.name.lower()).ratio()
                    if similarity > best_match_score and similarity > 0.8:  # 80% similarity threshold
                        best_match_score = similarity
                        best_match_customer = customer
            
            if best_match_customer:
                matched_customer = best_match_customer
                match_confidence = best_match_score * 0.8  # Scale down confidence for name matching
                match_reason = "name_fuzzy_match"
                logger.info(f"Found customer by name similarity: {matched_customer.customer_id} (score: {best_match_score:.2f})")
        
        # Priority 4: Semantic search on conversation history (lower confidence)
        if not matched_customer and len(text) > 50:
            search_results = memory_service.search_similar(text, k=3)
            if search_results["results"]:
                top_result = search_results["results"][0]
                if top_result["similarity"] > 0.85:  # High similarity threshold
                    result_customer_id = top_result["metadata"]["customer_id"]
                    matched_customer = customer_service.get_customer(result_customer_id)
                    if matched_customer:
                        match_confidence = top_result["similarity"] * 0.7  # Scale down for semantic match
                        match_reason = "semantic_similarity"
                        logger.info(f"Found customer by semantic search: {matched_customer.customer_id} (similarity: {top_result['similarity']:.2f})")
        
        # Build response
        if matched_customer:
            response = {
                "status": "existing_customer",
                "customer_id": matched_customer.customer_id,
                "confidence": match_confidence,
                "match_reason": match_reason,
                "customer": {
                    "customer_id": matched_customer.customer_id,
                    "name": matched_customer.name,
                    "email": matched_customer.email,
                    "phone": matched_customer.phone,
                    "preferences_count": len(matched_customer.preferences),
                    "issues_count": len([i for i in matched_customer.issues if i.status.lower() == "open"]),
                    "last_interaction": matched_customer.last_interaction.isoformat() if matched_customer.last_interaction else None
                },
                "extracted_info": {
                    "name": name,
                    "phone": phone_extracted,
                    "email": email_extracted
                }
            }
        else:
            response = {
                "status": "new_customer",
                "customer_id": None,
                "confidence": 0.0,
                "match_reason": "no_match_found",
                "extracted_info": {
                    "name": name,
                    "phone": phone_extracted,
                    "email": email_extracted
                },
                "suggestion": "Create new customer profile with extracted information"
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Customer identification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/action/recommend", response_model=Dict[str, Any])
async def recommend_action(customer_id: str):
    """
    Get rule-based action recommendation for customer
    
    AUTHORITY: RULES = LOGIC (deterministic, no AI)
    - Uses CustomerProfile (authoritative state) only
    - Returns action with full provenance (rule_id + reason)
    - Deterministic and auditable
    
    Args:
        customer_id: Customer identifier
        
    Returns:
        Recommended action with rule provenance
    """
    try:
        logger.info(f"Getting rule-based recommendation for customer {customer_id}")
        
        # Get customer state
        customer = customer_service.get_customer(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get rule-based recommendation
        action = action_service.recommend_action(customer)
        
        logger.info(f"Recommendation: {action['action_type']} (Rule: {action['rule_id']})")
        
        return {
            "status": "success",
            "action": {
                "type": action['action_type'],
                "priority": action['priority'],
                "details": action['details'],
                "rule_id": action['rule_id'],
                "rule_reason": action['reason']
            },
            "provenance": {
                "customer_id": customer.customer_id,
                "rule_id": action['rule_id'],
                "reason": action['reason'],
                "deterministic": True,
                "ai_involved": False
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/actions/pending", response_model=List[Dict[str, Any]])
async def get_pending_actions(limit: int = 50):
    """
    Get all pending actions across all customers
    
    Args:
        limit: Maximum number of actions to return
        
    Returns:
        List of pending actions
    """
    try:
        actions = action_service.get_pending_actions(limit=limit)
        
        return [
            {
                "action_id": a.action_id,
                "type": a.type,
                "customer_id": a.customer_id,
                "priority": a.priority,
                "details": a.details,
                "created_at": a.created_at.isoformat()
            }
            for a in actions
        ]
        
    except Exception as e:
        logger.error(f"Failed to retrieve pending actions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/action/{action_id}/status", response_model=Dict[str, Any])
async def update_action_status(action_id: str, status: str):
    """
    Update action status (pending, completed, cancelled)
    
    Args:
        action_id: Action identifier
        status: New status
        
    Returns:
        Updated action
    """
    try:
        if status not in ["pending", "completed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        action = action_service.update_action_status(action_id, status)
        
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        
        return {
            "status": "success",
            "action": action.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update action status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customers", response_model=List[Dict[str, Any]])
async def list_customers():
    """
    List all customers (authoritative state only)
    
    Returns:
        List of customer profiles from single source of truth
    """
    try:
        customers = customer_service.get_all_customers()
        
        return [
            {
                "customer_id": c.customer_id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "last_interaction": c.last_interaction.isoformat() if c.last_interaction else None,
                "preferences_count": sum(len(v) for v in c.preferences.values()) if isinstance(c.preferences, dict) else len(c.preferences),
                "open_issues_count": len([i for i in c.issues if i.status.lower() == "open"]),
                "commitments_count": len(c.commitments)
            }
            for c in customers
        ]
        
    except Exception as e:
        logger.error(f"Failed to list customers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/customer/{customer_id}/issue/resolve", response_model=Dict[str, Any])
async def resolve_issue(customer_id: str, issue_description: str, resolution: str):
    """
    Mark a customer issue as resolved
    
    Args:
        customer_id: Customer identifier
        issue_description: Description of issue to resolve
        resolution: Resolution notes
        
    Returns:
        Updated customer profile
    """
    try:
        customer = customer_service.resolve_issue(customer_id, issue_description, resolution)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Customer or issue not found")
        
        return {
            "status": "success",
            "message": "Issue resolved successfully",
            "customer_id": customer.customer_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve issue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customer/{customer_id}/audit", response_model=Dict[str, Any])
async def get_audit_trail(customer_id: str, limit: int = 50):
    """
    Get audit trail for customer state changes
    
    AUTHORITY: Audit log shows all deterministic state transitions
    
    Args:
        customer_id: Customer identifier
        limit: Maximum entries to return
        
    Returns:
        Audit trail with full provenance
    """
    try:
        audit_entries = customer_service.get_audit_trail(customer_id, limit)
        
        return {
            "customer_id": customer_id,
            "audit_trail": audit_entries,
            "total_entries": len(audit_entries)
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit trail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CONTEXT RETRIEVAL ENDPOINTS (Enhanced)
# ============================================

@app.get("/context/search", response_model=Dict[str, Any])
async def search_context(query: str, customer_id: Optional[str] = None, limit: int = 5):
    """
    Semantic search for context across all conversations
    
    RETRIEVAL METHODS:
    1. Semantic search using FAISS embeddings
    2. Optional filter by customer_id
    3. Returns conversations with similarity scores
    
    Args:
        query: Search query text
        customer_id: Optional filter by specific customer
        limit: Maximum results to return
        
    Returns:
        Search results with conversations and metadata
    """
    try:
        logger.info(f"Semantic search: '{query}' (customer_id: {customer_id}, limit: {limit})")
        
        # Perform semantic search
        results = memory_service.search_similar(query, customer_id=customer_id, k=limit)
        
        # Enrich results with customer details
        enriched_results = []
        for result in results.get("results", []):
            cust_id = result["metadata"]["customer_id"]
            customer = customer_service.get_customer(cust_id)
            
            enriched_results.append({
                "conversation_id": result["metadata"]["conversation_id"],
                "customer_id": cust_id,
                "customer_name": customer.name if customer else "Unknown",
                "similarity": result["similarity"],
                "timestamp": result["metadata"].get("timestamp"),
                "text_preview": result.get("text", "")[:200] + "..." if len(result.get("text", "")) > 200 else result.get("text", "")
            })
        
        return {
            "status": "success",
            "query": query,
            "results": enriched_results,
            "total_results": len(enriched_results)
        }
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/context/customer/{customer_id}", response_model=Dict[str, Any])
async def get_customer_context(customer_id: str, include_raw_text: bool = False):
    """
    Get complete context for a specific customer
    
    RETRIEVAL METHODS:
    1. Customer profile (preferences, issues, commitments)
    2. Context reliability scores
    3. Raw conversation history (optional)
    4. Audit trail of context changes
    
    Args:
        customer_id: Customer identifier
        include_raw_text: Include full conversation text (default: False)
        
    Returns:
        Complete customer context with metadata
    """
    try:
        logger.info(f"Retrieving complete context for customer: {customer_id}")
        
        # Get customer profile
        customer = customer_service.get_customer(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Get conversation history
        conversations = memory_service.get_customer_evidence(customer_id, limit=50)
        
        # Build response
        response = {
            "status": "success",
            "customer_id": customer_id,
            "profile": {
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "last_interaction": customer.last_interaction.isoformat() if customer.last_interaction else None,
                "total_interactions": customer.interaction_count,
                "created_at": customer.created_at.isoformat()
            },
            "context": {
                "preferences": customer.preferences,
                "preferences_count": sum(len(v) for v in customer.preferences.values()) if isinstance(customer.preferences, dict) else len(customer.preferences),
                "issues": [
                    {
                        "description": issue.description,
                        "status": issue.status,
                        "reported_at": issue.reported_at.isoformat(),
                        "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
                        "conversation_id": getattr(issue, 'conversation_id', None)
                    }
                    for issue in customer.issues
                ],
                "open_issues_count": len([i for i in customer.issues if i.status.lower() == "open"]),
                "commitments": customer.commitments,
                "commitments_count": len(customer.commitments)
            },
            "reliability": {
                "total_updates": customer.context_metadata.get("total_updates", 0) if customer.context_metadata else 0,
                "preference_scores": customer.context_metadata.get("preference_scores", {}) if customer.context_metadata else {},
                "most_reliable_preferences": sorted(
                    customer.context_metadata.get("preference_scores", {}).items() if customer.context_metadata else [],
                    key=lambda x: x[1],
                    reverse=True
                )[:5] if customer.context_metadata and customer.context_metadata.get("preference_scores") else []
            },
            "conversations": [
                {
                    "conversation_id": conv.conversation_id,
                    "timestamp": conv.timestamp.isoformat(),
                    "channel": conv.channel,
                    "text": conv.text if include_raw_text else f"{conv.text[:150]}..." if len(conv.text) > 150 else conv.text
                }
                for conv in conversations
            ],
            "conversations_count": len(conversations)
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get customer context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/context/conversation/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation_context(conversation_id: str):
    """
    Get context for a specific conversation
    
    RETRIEVAL METHODS:
    1. Raw conversation text
    2. Extracted context from that conversation
    3. Customer details at time of conversation
    
    Args:
        conversation_id: Conversation identifier
        
    Returns:
        Conversation details with extracted context
    """
    try:
        logger.info(f"Retrieving conversation: {conversation_id}")
        
        # Search for conversation in evidence store
        from tinydb import TinyDB
        evidence_db = TinyDB(config.CONVERSATIONS_DB)
        Query_obj = Query()
        results = evidence_db.search(Query_obj.conversation_id == conversation_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv_data = results[0]
        customer_id = conv_data.get("customer_id")
        
        # Get customer profile
        customer = customer_service.get_customer(customer_id)
        
        response = {
            "status": "success",
            "conversation_id": conversation_id,
            "customer_id": customer_id,
            "customer_name": customer.name if customer else "Unknown",
            "channel": conv_data.get("channel", "unknown"),
            "timestamp": conv_data.get("timestamp"),
            "raw_text": conv_data.get("text", ""),
            "text_length": len(conv_data.get("text", "")),
            "customer_snapshot": {
                "preferences_at_time": len(customer.preferences) if customer else 0,
                "open_issues_at_time": len([i for i in customer.issues if i.status.lower() == "open"]) if customer else 0,
                "commitments_at_time": len(customer.commitments) if customer else 0
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/context/timeline", response_model=Dict[str, Any])
async def get_context_timeline(
    customer_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
):
    """
    Get time-based context changes and conversations
    
    RETRIEVAL METHODS:
    1. Time-filtered conversations
    2. Context changes over time
    3. Issue resolution timeline
    
    Args:
        customer_id: Optional filter by customer
        start_date: Optional start date (ISO format)
        end_date: Optional end date (ISO format)
        limit: Maximum entries to return
        
    Returns:
        Timeline of conversations and context changes
    """
    try:
        logger.info(f"Retrieving context timeline (customer: {customer_id}, dates: {start_date} to {end_date})")
        
        from tinydb import TinyDB
        evidence_db = TinyDB(config.CONVERSATIONS_DB)
        
        # Get all conversations
        Query_obj = Query()
        if customer_id:
            results = evidence_db.search(Query_obj.customer_id == customer_id)
        else:
            results = evidence_db.all()
        
        # Filter by date if provided
        if start_date or end_date:
            from datetime import datetime
            filtered_results = []
            for result in results:
                timestamp_str = result.get("timestamp", "")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str) if isinstance(timestamp_str, str) else timestamp_str
                    
                    if start_date and datetime.fromisoformat(start_date) > timestamp:
                        continue
                    if end_date and datetime.fromisoformat(end_date) < timestamp:
                        continue
                    
                    filtered_results.append(result)
            results = filtered_results
        
        # Sort by timestamp
        results = sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
        results = results[:limit]
        
        # Build timeline
        timeline = []
        for conv in results:
            cust_id = conv.get("customer_id")
            customer = customer_service.get_customer(cust_id)
            
            timeline.append({
                "type": "conversation",
                "conversation_id": conv.get("conversation_id"),
                "customer_id": cust_id,
                "customer_name": customer.name if customer else "Unknown",
                "channel": conv.get("channel", "unknown"),
                "timestamp": conv.get("timestamp"),
                "text_preview": conv.get("text", "")[:200] + "..." if len(conv.get("text", "")) > 200 else conv.get("text", "")
            })
        
        return {
            "status": "success",
            "timeline": timeline,
            "total_entries": len(timeline),
            "filters": {
                "customer_id": customer_id,
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get context timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CUSTOMER SUMMARY ENDPOINTS
# ============================================

@app.post("/summary")
@app.get("/summary")
async def summary_redirect():
    """
    Redirect endpoint - guides users to correct summary endpoints
    """
    return JSONResponse(
        status_code=200,
        content={
            "message": "Summary endpoint moved",
            "available_endpoints": {
                "external_database": {
                    "endpoint": "POST /customer/summarize",
                    "description": "For teammates with external database - send customer JSON, get AI summary",
                    "example": {
                        "url": "http://192.168.220.76:8000/customer/summarize",
                        "method": "POST",
                        "body": {
                            "customer_id": "abc123",
                            "name": "John Doe",
                            "preferences": {},
                            "issues": [],
                            "commitments": []
                        }
                    }
                },
                "local_database": {
                    "endpoint": "GET /customer/{customer_id}/summary",
                    "description": "For users with access to local database - get summary by customer ID",
                    "example": {
                        "url": "http://192.168.220.76:8000/customer/CUST001/summary",
                        "method": "GET"
                    }
                }
            },
            "documentation": {
                "external_db": "See EXTERNAL_DATABASE_API.md",
                "local_db": "See CUSTOMER_SUMMARY_API.md",
                "quick_ref": "See QUICK_REF_EXTERNAL.txt"
            },
            "test_script": "python test_external_summary.py"
        }
    )

@app.post("/customer/summarize", response_model=Dict[str, Any])
async def summarize_customer_profile(profile_data: Dict[str, Any]):
    """
    Generate an LLM-powered summary from customer profile JSON
    
    This endpoint is for teammates who have their own database.
    They send the customer profile data as JSON and get back an AI summary.
    
    Args:
        profile_data: Customer profile data in JSON format containing:
            - customer_id (required)
            - preferences, issues, commitments, etc.
        
    Returns:
        AI-generated summary with metadata
    """
    try:
        customer_id = profile_data.get('customer_id', 'unknown')
        logger.info(f"Generating summary for external customer data: {customer_id}")
        
        # Validate required field
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id is required in profile_data")
        
        # 3. Generate summary using LLM
        from utils.prompt_templates import CUSTOMER_PROFILE_SUMMARY_PROMPT
        import json
        import requests
        
        prompt = CUSTOMER_PROFILE_SUMMARY_PROMPT.format(
            profile_data=json.dumps(profile_data, indent=2)
        )
        
        logger.info(f"Calling LLaMA 3 for customer profile summary (external data)...")
        response = requests.post(
            config.OLLAMA_URL,
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower for more factual summaries
                    "top_p": 0.9,
                    "num_predict": 500  # Limit summary length
                }
            },
            timeout=30
        )
        response.raise_for_status()
        llm_response = response.json()
        summary_text = llm_response.get('response', '').strip()
        
        logger.info(f"Successfully generated summary for external customer {customer_id}")
        
        # 4. Return summary with metadata
        return {
            "status": "success",
            "customer_id": customer_id,
            "summary": summary_text,
            "metadata": {
                "name": profile_data.get('name'),
                "email": profile_data.get('email'),
                "phone": profile_data.get('phone'),
                "total_interactions": profile_data.get('interaction_count', 0),
                "open_issues_count": len([i for i in profile_data.get('issues', []) if isinstance(i, dict) and i.get('status', '').lower() == 'open']),
                "active_commitments_count": len([c for c in profile_data.get('commitments', []) if isinstance(c, dict) and c.get('status', '').lower() == 'pending']),
                "last_interaction": profile_data.get('last_interaction')
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate customer summary from external data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@app.get("/customer/{customer_id}/summary", response_model=Dict[str, Any])
async def get_customer_summary(customer_id: str):
    """
    Generate an LLM-powered summary of a customer profile
    
    This endpoint is designed for team members to quickly understand
    a customer's profile without parsing raw JSON data.
    
    Args:
        customer_id: Customer identifier
        
    Returns:
        AI-generated summary of customer profile with key insights
    """
    try:
        logger.info(f"Generating summary for customer: {customer_id}")
        
        # 1. Get customer profile
        customer = customer_service.get_customer(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # 2. Prepare profile data for LLM
        profile_data = {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "interaction_count": customer.interaction_count,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "last_interaction": customer.last_interaction.isoformat() if customer.last_interaction else None,
            "preferences": customer.preferences,
            "issues": [{
                "concern": issue.concern,
                "status": issue.status,
                "confidence": issue.confidence,
                "reported_at": issue.reported_at.isoformat() if issue.reported_at else None
            } for issue in customer.issues],
            "commitments": [{
                "action": commit.action,
                "timeline": commit.timeline,
                "confidence": commit.confidence,
                "status": commit.status,
                "created_at": commit.created_at.isoformat() if commit.created_at else None
            } for commit in customer.commitments],
            "last_sentiment": customer.last_sentiment,
            "last_urgency": customer.last_urgency,
            "last_intent": customer.last_intent
        }
        
        # 3. Generate summary using LLM
        from utils.prompt_templates import CUSTOMER_PROFILE_SUMMARY_PROMPT
        import json
        import requests
        
        prompt = CUSTOMER_PROFILE_SUMMARY_PROMPT.format(
            profile_data=json.dumps(profile_data, indent=2)
        )
        
        logger.info("Calling LLaMA 3 for customer profile summary...")
        response = requests.post(
            config.OLLAMA_URL,
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower for more factual summaries
                    "top_p": 0.9,
                    "num_predict": 500  # Limit summary length
                }
            },
            timeout=30
        )
        response.raise_for_status()
        llm_response = response.json()
        summary_text = llm_response.get('response', '').strip()
        
        logger.info(f"Successfully generated summary for customer {customer_id}")
        
        # 4. Return summary with metadata
        return {
            "status": "success",
            "customer_id": customer_id,
            "summary": summary_text,
            "metadata": {
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "total_interactions": customer.interaction_count,
                "open_issues_count": len([i for i in customer.issues if i.status.lower() == "open"]),
                "active_commitments_count": len([c for c in customer.commitments if c.status.lower() == "pending"]),
                "last_interaction": customer.last_interaction.isoformat() if customer.last_interaction else None
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate customer summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


# ============================================
# COST MONITORING & OPTIMIZATION ENDPOINTS
# ============================================

@app.get("/admin/cost-summary", response_model=Dict[str, Any])
async def get_cost_summary(hours: int = 24):
    """
    Get cost and usage summary for ROI analysis
    
    Args:
        hours: Time period in hours (default 24)
        
    Returns:
        Cost summary with cache hit rates and savings
    """
    try:
        summary = cost_tracker.get_summary(hours)
        rate_stats = rate_limiter.get_stats()
        
        return {
            "period_hours": hours,
            "cost_metrics": summary,
            "rate_limit_stats": rate_stats,
            "optimization_recommendations": {
                "cache_performance": "Excellent" if summary['cache_hit_rate'] > 50 else "Good" if summary['cache_hit_rate'] > 30 else "Low",
                "estimated_monthly_cost": round(summary['total_cost'] * (720 / hours), 2),
                "estimated_monthly_savings": round(summary['cost_savings_from_cache'] * (720 / hours), 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get cost summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/clear-cache", response_model=Dict[str, Any])
async def clear_llm_cache():
    """
    Clear expired LLM cache entries (admin only)
    
    Returns:
        Number of entries cleared
    """
    try:
        from services.cost_optimization import get_llm_cache
        cache = get_llm_cache()
        removed = cache.clear_expired()
        
        return {
            "status": "success",
            "entries_removed": removed
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoints removed - use new authority-separated endpoints instead
# Old: /memory/add -> Use /conversation
# Old: /memory/search -> Use /customer/{id}/context


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT)



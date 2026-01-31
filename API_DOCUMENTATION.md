# API Documentation - Authority-Separated Architecture

## Overview
This API implements a strict authority separation model for customer intelligence management. All endpoints respect the principle: **Evidence → Facts → State → Rules → Search**.

**Base URL**: `http://<host>:8000` (default: `http://0.0.0.0:8000`)

**Architecture**: FastAPI with CORS enabled for cross-device access

---

## Core Principles

### Authority Levels
1. **Evidence** (ConversationEvidence) - Raw audit trail
2. **Facts** (ExtractedContext) - Transient LLM output
3. **State** (CustomerProfile) - Single source of truth
4. **Rules** (ActionRules) - Deterministic logic
5. **Search** (FAISS Index) - Display only, no authority

### Key Guarantees
- ✅ All actions are rule-based with provenance
- ✅ No AI-generated summaries
- ✅ All state changes logged (audit trail)
- ✅ Semantic search isolated (display only)
- ✅ Deterministic and auditable

---

## Endpoints

### Health Check

#### `GET /health`
Check system status and available services.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T10:00:00",
  "services": {
    "extraction": "ready",
    "memory": "ready",
    "customer": "ready",
    "action": "ready"
  },
  "models": {
    "llama": "llama3",
    "whisper": "medium",
    "embeddings": "all-MiniLM-L6-v2"
  }
}
```

---

### Conversation Management

#### `POST /conversation`
Ingest a new customer conversation with authority-separated flow.

**Flow**: Evidence → Extract Facts → Update State → Generate Rules → Index for Search

**Request Body**:
```json
{
  "customer_id": "optional-existing-id",
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "customer_phone": "+1234567890",
  "channel": "chat",
  "text": "I'm interested in your premium plan with advanced features."
}
```

**Fields**:
- `customer_id` (optional): Existing customer ID, or omit to create new
- `channel`: One of: "chat", "email", "call", "sms"
- `text`: Conversation transcript

**Response**:
```json
{
  "status": "success",
  "conversation_id": "uuid-here",
  "customer_id": "uuid-here",
  "extracted_context": {
    "preferences": ["premium plan", "advanced features"],
    "issues": [],
    "commitments": [],
    "signals": {
      "intent": "purchase_inquiry",
      "sentiment": "positive",
      "urgency": "medium"
    }
  },
  "recommended_action": {
    "type": "lead",
    "priority": "high",
    "details": {
      "opportunity": "Multiple preferences detected",
      "preferences": ["premium plan", "advanced features"]
    },
    "rule_id": "R005",
    "rule_reason": "Customer expressed 2+ preferences (premium plan, advanced features) - sales opportunity"
  },
  "authority_flow": "Evidence → Facts → State → Rules → Search"
}
```

---

### Customer Context

#### `GET /customer/{customer_id}/context?include_audit=false`
Retrieve complete customer context with authority separation.

**Parameters**:
- `customer_id` (path): Customer identifier
- `include_audit` (query, optional): Include state change audit trail (default: false)

**Response**:
```json
{
  "authority_model": "State + Evidence + Search (separated)",
  "customer_profile": {
    "customer_id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "preferences": ["premium plan", "advanced features", "API access"],
    "issues": [
      {
        "description": "Payment declined",
        "status": "OPEN",
        "reported_at": "2026-01-30T09:30:00",
        "conversation_id": "conv-uuid"
      }
    ],
    "commitments": ["Follow up next week"],
    "last_interaction": "2026-01-30T10:00:00",
    "created_at": "2026-01-15T08:00:00",
    "updated_at": "2026-01-30T10:00:00"
  },
  "recent_evidence": [
    {
      "conversation_id": "uuid",
      "timestamp": "2026-01-30T10:00:00",
      "channel": "chat",
      "raw_text": "First 200 chars of conversation..."
    }
  ],
  "search_results": {
    "warning": "⚠️ DISPLAY ONLY - Not authoritative, use for context hints only",
    "results": [
      {
        "text": "Similar past conversation...",
        "similarity_score": 0.85,
        "conversation_id": "uuid"
      }
    ]
  },
  "statistics": {
    "total_preferences": 3,
    "open_issues": 1,
    "total_commitments": 1,
    "evidence_count": 5
  }
}
```

**Authority Notes**:
- `customer_profile`: **AUTHORITATIVE** - Single source of truth
- `recent_evidence`: Raw data for display, not processed
- `search_results`: **DISPLAY ONLY** - Semantic hints, no authority

---

### Action Recommendations

#### `POST /action/recommend?customer_id={customer_id}`
Get rule-based action recommendation (deterministic, no AI).

**Parameters**:
- `customer_id` (query): Customer identifier

**Response**:
```json
{
  "status": "success",
  "action": {
    "type": "ticket",
    "priority": "high",
    "details": {
      "issue": "Payment declined",
      "conversation_id": "uuid"
    },
    "rule_id": "R001",
    "rule_reason": "Customer has 1 unresolved issue(s) requiring support"
  },
  "provenance": {
    "customer_id": "uuid",
    "rule_id": "R001",
    "reason": "Customer has 1 unresolved issue(s) requiring support",
    "deterministic": true,
    "ai_involved": false
  }
}
```

**Rules**:
- **R001**: Unresolved issues → Create support ticket
- **R002**: Purchase intent + preferences → Create lead
- **R003**: Commitments with follow-up → Create reminder
- **R004**: Budget-sensitive inquiry → Create lead
- **R005**: Multiple preferences (2+) → Create lead

---

### Issue Management

#### `PUT /customer/{customer_id}/issue/resolve`
Mark a customer issue as resolved with audit logging.

**Request Body**:
```json
{
  "issue_description": "Payment declined",
  "resolution": "Updated payment method, processed successfully"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Issue resolved successfully",
  "customer_id": "uuid"
}
```

---

### Audit Trail

#### `GET /customer/{customer_id}/audit?limit=50`
Retrieve full audit trail of state changes for customer.

**Parameters**:
- `customer_id` (path): Customer identifier
- `limit` (query, optional): Max entries (default: 50)

**Response**:
```json
{
  "customer_id": "uuid",
  "audit_trail": [
    {
      "timestamp": "2026-01-30T10:00:00",
      "change_type": "UPDATED",
      "fields_changed": ["preferences", "issues"],
      "old_values": {
        "preferences": ["premium plan"]
      },
      "new_values": {
        "preferences": ["premium plan", "advanced features", "API access"]
      },
      "reason": "Facts extracted from conversation conv-uuid",
      "source_conversation_id": "conv-uuid"
    }
  ],
  "total_entries": 15
}
```

---

### Customer Listing

#### `GET /customers`
List all customers (authoritative state only).

**Response**:
```json
[
  {
    "customer_id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "last_interaction": "2026-01-30T10:00:00",
    "preferences_count": 3,
    "open_issues_count": 1,
    "commitments_count": 1
  }
]
```

---

### Audio Transcription

#### `POST /transcribe`
Transcribe audio file using Whisper and optionally create conversation.

**Request**: `multipart/form-data`
- `file`: Audio file (WAV, MP3, etc.)
- `customer_id` (optional): Customer ID to auto-create conversation

**Response**:
```json
{
  "status": "success",
  "transcript": "Full transcribed text here...",
  "language": "en",
  "conversation": {
    // Full conversation response if customer_id provided
  }
}
```

---

## Error Responses

All endpoints return consistent error format:

**4xx Client Errors**:
```json
{
  "detail": "Customer not found"
}
```

**5xx Server Errors**:
```json
{
  "detail": "Context extraction failed: Connection timeout"
}
```

---

## CORS Configuration

Cross-Origin Resource Sharing (CORS) is enabled for:
- `http://localhost:3000` (React dev)
- `http://localhost:5173` (Vite dev)
- All methods and headers allowed

**To access from another device**:
1. Server binds to `0.0.0.0:8000` (all interfaces)
2. Access via: `http://<server-ip>:8000`
3. Add device origin to `CORS_ORIGINS` in config if needed

---

## Architecture Guarantees

### Determinism
- ✅ All action recommendations use explicit rules (R001-R005)
- ✅ Customer updates use deterministic validation (4 rules)
- ✅ No AI in decision-making path

### Auditability
- ✅ All conversations stored as evidence (raw data)
- ✅ All state changes logged with provenance
- ✅ Full audit trail retrievable per customer

### Authority Separation
- ✅ LLM outputs transient facts only (no persistence)
- ✅ CustomerProfile is single source of truth
- ✅ Semantic search isolated (display only)
- ✅ Rules engine independent of AI

### Type Safety
- ✅ Pydantic v2 models with strict validation
- ✅ Datetime handling with isinstance checks
- ✅ Structured issues with IssueRecord model

---

## Example: Complete Conversation Flow

```bash
# 1. Ingest conversation
curl -X POST http://localhost:8000/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Jane Smith",
    "customer_email": "jane@example.com",
    "channel": "chat",
    "text": "My account has an error. I also want the enterprise plan."
  }'

# Response includes:
# - conversation_id (evidence stored)
# - extracted facts (preferences: ["enterprise plan"], issues: ["account error"])
# - rule-based action (R001: ticket due to issue)

# 2. Get customer context
curl http://localhost:8000/customer/<customer_id>/context

# Response shows:
# - Authoritative state (CustomerProfile)
# - Recent evidence (raw conversations)
# - Search hints (⚠️ display only)

# 3. Get action recommendation
curl -X POST http://localhost:8000/action/recommend?customer_id=<id>

# Returns rule R001 (ticket) with full provenance

# 4. Resolve issue
curl -X PUT http://localhost:8000/customer/<id>/issue/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "issue_description": "account error",
    "resolution": "Fixed database sync issue"
  }'

# 5. View audit trail
curl http://localhost:8000/customer/<id>/audit

# Shows all state changes with provenance
```

---

## Migration from Old API

### Deprecated Endpoints
- ❌ `/memory/add` → Use `/conversation`
- ❌ `/memory/search` → Use `/customer/{id}/context`
- ❌ `/actions/pending` → Use `/action/recommend` per customer
- ❌ `/action/trigger` → Use `/action/recommend` (now rule-based)

### Breaking Changes
1. ExtractedContext now uses `signals` dict instead of top-level intent/sentiment/urgency
2. CustomerProfile no longer has `history_summary` or `sentiment_trend`
3. Issues are now structured `IssueRecord` objects with status tracking
4. Actions include `rule_id` and `rule_reason` for provenance

---

## Performance & Scaling

### Current Configuration
- TinyDB for state/evidence (file-based JSON)
- FAISS for vector search (in-memory with persistence)
- LLaMA 3 via Ollama (local inference)

### Recommendations
- For > 10K customers: Migrate to PostgreSQL
- For > 100K vectors: Use FAISS IVF index
- For production: Deploy LLaMA on GPU

### Network Access
- Bind: `0.0.0.0:8000` (all interfaces)
- Access from network: `http://<server-ip>:8000`
- Firewall: Open port 8000

---

## Security Notes

1. **No Authentication**: Add OAuth2/JWT for production
2. **CORS**: Restrict origins in production
3. **Rate Limiting**: Implement per-endpoint limits
4. **Input Validation**: All inputs validated by Pydantic
5. **Audit Trail**: Immutable log of all changes

---

**Version**: 2.0.0 (Authority-Separated Architecture)  
**Last Updated**: January 30, 2026

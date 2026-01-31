# Context-Aware Customer Intelligence System
## Architecture Overview

### System Purpose
Real-time customer memory and context engine that captures conversations across chat, email, and calls, extracts structured context, stores long-term memory, and provides instant context recall for support agents.

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│  ┌──────────────────┐        ┌─────────────────────────┐   │
│  │ Agent Dashboard  │        │ Customer Interaction    │   │
│  │ - Context View   │        │ - Chat Input            │   │
│  │ - Actions        │        │ - Call Upload           │   │
│  └──────────────────┘        └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│                                                              │
│  API Layer                                                   │
│  ├── POST /conversation          - Ingest new interaction   │
│  ├── GET  /customer/{id}/context - Retrieve full context    │
│  ├── POST /transcribe             - Audio to text           │
│  ├── POST /action/trigger         - Execute action          │
│  └── GET  /health                 - System status           │
│                                                              │
│  Core Services                                               │
│  ├── Context Extraction Service   (LLaMA 3)                 │
│  ├── Memory Service               (Dual: Structured+Vector) │
│  ├── Whisper Service              (Speech-to-Text)          │
│  ├── Action Engine                (Automation)              │
│  └── Customer Service             (Profile Management)      │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI/NLP PIPELINE                           │
│                                                              │
│  1. Input Normalization                                      │
│     └─► Clean text, standardize format                      │
│                                                              │
│  2. Context Extraction (LLaMA 3)                            │
│     └─► Extract: Intent, Preferences, Issues, Sentiment     │
│                                                              │
│  3. Embedding Generation (all-MiniLM-L6-v2)                 │
│     └─► Convert to 384-dim vectors                          │
│                                                              │
│  4. Memory Storage                                           │
│     ├─► Structured DB (TinyDB/SQLite)                       │
│     └─► Vector Store (FAISS)                                │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                             │
│                                                              │
│  Structured State Store (TinyDB) — AUTHORITATIVE            │
│  ├── Customer Profiles (confirmed facts only)               │
│  ├── Action Logs (deterministic records)                    │
│  └── Rules Configuration                                     │
│                                                              │
│  Evidence Store (TinyDB) — RAW DATA ONLY                    │
│  ├── Raw Conversation Text                                   │
│  ├── Timestamps                                              │
│  └── Channel Metadata                                        │
│                                                              │
│  Semantic Search Index (FAISS) — READ-ONLY SEARCH          │
│  ├── Text Embeddings (raw text only)                        │
│  ├── Conversation ID mapping                                │
│  └── Used for agent-initiated search ONLY                   │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Component Details

### 1. Backend Services

#### Context Extraction Service
- **Purpose**: Extract FACTS ONLY from conversations
- **Technology**: LLaMA 3 via Ollama
- **Output**: JSON with preferences, issues, commitments, signals (sentiment, urgency)
- **NOT Output**: No action recommendations, no summaries, no inferences
- **Constraint**: LLM never reads database state, only processes raw text
- **Anti-hallucination**: Strict prompt engineering with examples

#### Memory Service
- **Storage Separation**:
  - **Structured State**: TinyDB for confirmed facts only (preferences, issues, commitments)
  - **Evidence Store**: TinyDB for raw conversations (never read by rules)
  - **Search Index**: FAISS for agent-initiated semantic search ONLY
- **Conflict Resolution**: Latest explicit fact overwrites (never inferred)
- **Retrieval**: State store ONLY for operations (search index for display only)

#### Whisper Service
- **Model**: Whisper Medium (local)
- **Device**: CUDA if available, else CPU
- **Preprocessing* (Deterministic Rules Only)
- **Input**: Structured state ONLY (never LLM output directly, never embeddings)
- **Rules**: Deterministic, auditable, reversible
- **Actions**: Create tickets, sales leads, follow-up reminders
- **Triggering**: Based on state conditions OR manual agent override
- **Constraint**: LLM never sees rules, rules never see embeddings
- **Logging**: All actions with rule provenance and timestamps
- **Triggering**: AutomAuthoritative State)
```json
{
  "customer_id": "unique_id",
  "name": "string",
  "email": "string",
  "phone": "string",
  "preferences": [],
  "issues": [],
  "commitments": [],
  "last_interaction": "timestamp",
  "last_sentiment": "string"
}
```
**REMOVED**: `history_summary` (AI-generated), `sentiment_trend` (inference)
**CONSTRAINT**: All fields are explicit facts only, never inferredcommitments": [],
  "history_summary": "string",
  "last_interaction": "timestamp",
  "sentiment_tren (Evidence Store - Raw Only)
```json
{
  "conversation_id": "uuid",
  "customer_id": "string",
  "timestamp": "iso8601",
  "channel": "chat|email|call",
  "raw_text": "string"
}
```
**REMOVED**: `extracted_context` (stored separately), `embedding` (stored in FAISS only)
**PURPOSE**: Evidence only, never read by rules or LLMraw_text": "string",
  "extracted_context": {},
  "embedding": [384-dim vector]
}
```

#### Action
```json
{
  "action_id": "uuid",
  "type": "ticket|lead|reminder",
  "customer_id": "string",
  "status": "pending|completed|cancelled",
  "details": {},
  "created_at": "timest (Authority Separated)

```
                        Raw Text Input
                              ▼
                        ┌─────────┐
                        │ Evidence│──► Store raw (TinyDB)
                        │  Store  │
                        └─────────┘
                              ▼
                    ┌──────────────────┐
                    │   LL (No Inference)

```
Customer ID → Retrieve State → Display Structured Facts
                  ▼                    ▼
              TinyDB            UI Assembly (no AI)

Optional:
Agent Search → FAISS Query → Show Similar Conversations
    ▼               ▼                    ▼
 User Input    Embeddings         Display Only (no merge)
```

**FORBIDDEN**: Merging semantic results into state, AI-generated summaries                 │ (Deterministic)  │
                    └──────────────────┘
                              ▼
                    ┌──────────────────┐
                    │   Rule Engine    │──► Suggest actions
                    │ (Reads state)    │
                    └──────────────────┘
                              ▼
                    ┌──────────────────┐
                    │  Search Index    │──► Store embeddings (FAISS)
                    │ (Write-only from │     [For agent search only]
                    │  raw text)       │
                    └──────────────────┘
```
Input → Normalize → Extract Context → Generate Embedding → Store
         ▼              ▼                    ▼              ▼
    Clean text    LLaMA 3 JSON        384-dim vec    TinyDB+FAISS
```

### 4. Context Recall Flow

```
Customer ID → Retrieve Profile → Top-K Semantic Search → Merge → Generate Summary
                  ▼                      ▼                 ▼           ▼
              TinyDB                  FAISS            Combine    Agent-ready text
```

## 📁 Project Structure

```
BeachHack/
├── ai_server/                  # Backend application
│   ├── app.py                  # Main FastAPI application
│   ├── config.py               # Configuration management
│   ├── requirements.txt        # Python dependencies
│   │
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   ├── customer.py         # Customer profile model
│   │   ├── conversation.py     # Conversation model
│   │   └── action.py           # Action model
│   │
│   ├── services/               # Core business logic
│   │   ├── __init__.py
│   │   ├── context_extraction.py   # LLaMA 3 extraction
│   │   ├── customer_service.py     # Customer management
│   │   ├── memory_service.py       # Dual memory implementation
│   │   ├── embed_service.py        # Embedding generation
│   │   ├── llm_service.py          # LLM interactions
│   │   ├── whisper_service.py      # Speech-to-text
│   │   └── action_service.py       # Action engine
│   │
│   ├── utils/                  # Utilities
│   │   ├── __init__.py
│   │   ├── audio_utils.py      # Audio preprocessing
│   │   └── prompt_templates.py # AI prompts
│   │
│   ├── data/                   # Persistent data
│   │   ├── customers.json      # TinyDB customer profiles
│   │   ├── conversations.json  # TinyDB conversations
│   │   ├── actions.json        # TinyDB actions
│   │   └── faiss.index         # FAISS vector store
│   │
│   └── uploads/                # Temporary audio file storage
│
├── frontend/                   # React application
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AgentDashboard.jsx
│   │   │   ├── CustomerInteraction.jsx
│   │   │   ├── ContextPanel.jsx
│   │  Strict Authority Separation
- **Principle**: LLM = compiler, DB = state, Rules = logic, Vectors = search
- **Enforcement**: No component crosses roles
- **Result**: Deterministic, auditable, testable

### 2. LLM Produces Facts Only
- **Input**: Raw text only (never database state)
- **Output**: Structured facts (preferences, issues, commitments, signals)
- **Forbidden**: Action recommendations, summaries, inferences
- **Reason**: LLMs are probabilistic; actions must be deterministic

### 3. Database is State Machine (Not Intelligence)
- **Purpose**: Store confirmed facts, enforce continuity
- **NOT Purpose**: Infer meaning, reason, combine data
- **Strategy**: Latest explicit fact overwrites (never inferred defaults)
- **Reason**: Single source of truth

### 4. Semantic Search is Read-Only Display
- **Purpose**: Agent-initiated search for similar conversations
- **Constraint**: Never merged into state, never triggers actions
- **Storage**: FAISS for embeddings of raw text only
- **Reason**: Similarity ≠ correctness

### 5. Actions from Deterministic Rules Only
- **Input**: Structured state only
- **Process**: Auditable rules, no AI involvement
- **Output**: Suggested actions with provenance
- **Reason**: Actions must be explainable and reversible

### Backend
- **Framework**: FastAPI (Python)
- **Database**: TinyDB (JSON-based, simple, local)
- **Vector Store**: FAISS
- **AI Models**:
  - LLaMA 3 (via Ollama)
  - Whisper Medium
  - all-MiniLM-L6-v2

### Frontend
- **Framework**: React
- **HTTP Client**: Axios
- **Styling**: CSS (minimal)

## 🔐 Key Design Decisions

### 1. TinyDB over SQLite
- **Reason**: Zero setup, JSON-based, human-readable, sufficient for hackathon scale
- **Trade-off**: Not suitable for production at scale

### 2. Single Unified Profile
- **Reason**: Simplifies lookup, avoids duplication
- **Strategy**: Incremental updates with conflict resolution

### 3. Local Model Deployment
- **Reason**: No API costs, privacy, offline capability
- **Trade-off**: Requires capable hardware (GPU recommended)

### 4. FAISS for Vectors
- **Reason**: Fast, CPU-only option, simple persistence
- **Trade-off**: No distributed setup

## 🎯 Demo Flow

1. **Customer initiates chat** → Preferences captured
2. **System extracts context** → Stored in dual memory
3. **Customer reconnects via call** → Upload audio
4. **Agent views dashboard** → Full context displayed instantly
5. **System recommends action** → "Create sales follow-up"
6. **Agent triggers action** → Lead created and logged

## 🔒 Database Access Control (Non-Negotiable)

| Component | Evidence Store | State Store | Search Index |
|-----------|----------------|-------------|--------------|
| **LLM Extractor** | ❌ read / ❌ write | ❌ read / ❌ write | ❌ |
| **State Updater** | ❌ | ✅ write | ❌ |
| **Rule Engine** | ❌ | ✅ read | ❌ |
| **Embedding Service** | ✅ read | ❌ | ✅ write |
| **Search Service** | ❌ | ❌ | ✅ read |
| **UI** | ✅ read | ✅ read | ✅ read |
| **Action Logger** | ❌ | ✅ write | ❌ |

**Critical Rule**: LLM never reads any database.

## ⚙️ Non-Functional Requirements

- **Determinism**: Same input → same state update
- **Auditability**: Every state change traceable to source
- **Authority Separation**: Clear roles (see AUTHORITY_MODEL.md)
- **Local-first**: All processing on local machine
- **Modular**: Clear separation of concerns
- **Logging**: State changes with provenance
- **Error Handling**: Graceful degradation
- **Environment Config**: .env for sensitive settings

## 🎓 Engineering Principles

- **Simplicity**: Choose straightforward solutions
- **Demo-first**: Prioritize visible, working features
- **Extensibility**: Easy to add channels/actions
- **Testability**: Simple test data generation

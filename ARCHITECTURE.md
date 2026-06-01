# ShopMind AI — Architecture Document

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Layer Breakdown](#3-layer-breakdown)
4. [LangGraph Agent Pipeline](#4-langgraph-agent-pipeline)
5. [Database Design](#5-database-design)
6. [API Design](#6-api-design)
7. [Key Design Decisions & Trade-offs](#7-key-design-decisions--trade-offs)
8. [Data Flow: Search Request](#8-data-flow-search-request)
9. [Data Flow: Price Alert](#9-data-flow-price-alert)
10. [Security Model](#10-security-model)
11. [Production Upgrade Path](#11-production-upgrade-path)

---

## 1. System Overview

ShopMind AI is a multi-agent product recommendation and price intelligence platform. Users describe what they want in natural language; the system discovers products, analyses pricing and reviews, ranks results with explainable scores, and monitors watchlists for price drops.

**Core capabilities:**
- Natural language product search → ranked recommendations with AI explanations
- Price-drop monitoring via scheduled background jobs
- WhatsApp alerts when products hit user-defined target prices
- User preference learning (budget, brands, categories)

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser / Streamlit UI  (localhost:8501)                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────────┐
│  FastAPI Application  (localhost:8000)                           │
│                                                                  │
│  POST /search         POST /search/watch                         │
│  GET  /watchlist/…    PATCH /watchlist/…   DELETE /watchlist/…  │
│  POST /users          PUT  /users/…/preferences                  │
│  GET  /health         GET  /health/ready                         │
│                                              ▲                   │
│  APScheduler (daily 08:00 UTC) ──────────────┘                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ graph.ainvoke(state, config)
┌──────────────────────────────▼──────────────────────────────────┐
│  LangGraph StateGraph                                            │
│                                                                  │
│  START → [orchestrator] → route_intent()                         │
│                │                  │                              │
│           "search"            "watch"                            │
│                │                  │                              │
│         [preference]    [save_watchlist] → END                   │
│                │                                                 │
│    [product_intelligence] ←── SerpAPI / mock_data                │
│                │                                                 │
│        [recommendation] ←── Groq LLM / templates                │
│                │                                                 │
│               END                                                │
│                                                                  │
│  [alert_checker] (APScheduler only) → Twilio → END              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ SQLAlchemy async ORM
┌──────────────────────────────▼──────────────────────────────────┐
│  PostgreSQL 16                                                   │
│  users │ user_preferences │ products (cache)                    │
│  watchlist │ search_history │ alert_logs                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Breakdown

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| **Frontend** | Streamlit | User interface — search, watchlist, history, settings |
| **API** | FastAPI + Uvicorn | HTTP routing, request validation, response serialisation |
| **Orchestration** | LangGraph 0.2 (StateGraph) | Agent workflow management, conditional routing |
| **LLM** | Groq (llama-3.3-70b-versatile) | Intent classification, recommendation explanations |
| **Product Search** | SerpAPI (Google Shopping) | Real-time product discovery |
| **Mock Layer** | `mock_data/products.json` | Dev/test fallback — full pipeline without paid APIs |
| **Scoring** | Pure Python | deal/review/relevance scoring without LLM |
| **Notifications** | Twilio WhatsApp | Price-drop alerts |
| **Scheduling** | APScheduler | Daily price-check background job |
| **Database** | PostgreSQL + SQLAlchemy async | Persistent storage, product cache, audit trail |
| **Migrations** | Alembic | Schema versioning and rollback |

---

## 4. LangGraph Agent Pipeline

### GraphState — The Pipeline Contract

All agents share a single `GraphState` TypedDict. Defining it before any agent code establishes the contract between agents — analogous to designing a database schema before writing queries.

```python
class GraphState(TypedDict):
    # Input
    user_id: str
    raw_query: str
    session_id: str
    use_mock: bool

    # Orchestrator output
    intent: str                    # "search" | "watch" | "unknown"
    product_query: str
    extracted_budget: float | None
    extracted_constraints: list[str]

    # Preference Agent output
    user_preferences: dict | None

    # Product Intelligence output
    raw_products: list[dict]
    cache_hit: bool

    # Recommendation Agent output
    recommendations: list[dict]

    # Watch path output
    watchlist_item_id: str | None

    # Error propagation
    error: str | None
    error_node: str | None
```

### Agent Responsibilities

| Agent | Input | Output | LLM? | DB? |
|-------|-------|--------|------|-----|
| **Orchestrator** | `raw_query` | `intent`, `product_query`, `extracted_budget` | ✅ Groq structured output | ❌ |
| **Preference** | `user_id` | `user_preferences` | ❌ | ✅ Read |
| **Product Intelligence** | `product_query`, `user_preferences` | `raw_products`, `cache_hit` | ❌ | ✅ Read+Write (cache) |
| **Recommendation** | `raw_products`, `user_preferences` | `recommendations` | ✅ Groq (explanations) | ❌ |
| **Alert Agent** | Watchlist (via scheduler) | Alert logs, Twilio messages | ❌ | ✅ Read+Write |

### Routing Logic

```
orchestrator → route_intent()
    "search"  → preference → product_intelligence → recommendation → END
    "watch"   → save_watchlist → END
    "unknown" → END
    (error)   → END
```

### Error Handling Strategy

No node throws unhandled exceptions. Each node wraps its logic in `try/except` and writes failure information to `state["error"]` and `state["error_node"]`. Downstream nodes receive the partial state and can decide whether to continue or degrade gracefully. The API layer surfaces the `error` field to clients.

---

## 5. Database Design

### Entity Relationship Summary

```
users (1) ─────────────── (1) user_preferences
  │
  ├── (1) ──── (many) search_history
  ├── (1) ──── (many) watchlist
  │                       │
  │               alert_logs (many) ─── watchlist (1)
  │
  └── (independent) products  [search result cache]
```

### Table Purposes

| Table | Purpose |
|-------|---------|
| `users` | Identity. Stores name, email, phone for alerts. No auth in this version. |
| `user_preferences` | Budget, preferred brands/categories. Loaded by Preference Agent. |
| `products` | TTL cache for SerpAPI results. Prevents redundant API calls. |
| `watchlist` | User-defined price monitors with target prices. |
| `search_history` | Audit trail. Used to personalise future searches. |
| `alert_logs` | Immutable record of every Twilio message sent. Used for deduplication. |

### Product Cache Design

Products are stored with a `fetched_at` timestamp and a `search_query` foreign key. The Product Intelligence Agent checks for cache hits before calling SerpAPI:

```
Cache hit condition: search_query = ? AND fetched_at >= (now - TTL_hours)
Cache miss: call SerpAPI, delete old rows for this query, insert new rows
```

TTL is configurable via `PRODUCT_CACHE_TTL_HOURS` (default: 6 hours).

---

## 6. API Design

### Endpoint Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/health/ready` | Readiness check (DB connection) |
| `POST` | `/users` | Create user account |
| `GET` | `/users/{id}` | Get user by ID |
| `PUT` | `/users/{id}/preferences` | Upsert user preferences |
| `GET` | `/users/{id}/preferences` | Get user preferences |
| `GET` | `/users/{id}/history` | Search history (last N) |
| `POST` | `/search` | **Run full AI pipeline** |
| `POST` | `/search/watch` | Add product to watchlist |
| `GET` | `/watchlist/{user_id}` | List watchlist items |
| `GET` | `/watchlist/{user_id}/{id}` | Get one item |
| `PATCH` | `/watchlist/{user_id}/{id}` | Update target price / active status |
| `DELETE` | `/watchlist/{user_id}/{id}` | Remove item |

### Request/Response Flow

```
POST /search
    ↓
SearchRequest (Pydantic validation)
    ↓
execute_search() [service layer]
    ↓
graph.ainvoke(initial_state, config={"configurable": {"db": session}})
    ↓
[orchestrator → preference → product_intelligence → recommendation]
    ↓
SearchResponse (Pydantic serialisation)
    ↓
HTTP 200
```

---

## 7. Key Design Decisions & Trade-offs

### Why LangGraph instead of plain Python?

| Plain function chain | LangGraph |
|---------------------|-----------|
| Manual data passing | Shared state object |
| Hard to add conditional paths | `add_conditional_edges()` |
| No built-in visualisation | `graph.get_graph().draw_mermaid()` |
| Sync only unless explicitly async | Async native |

LangGraph makes the workflow explicit, testable, and extensible. Adding a new agent means adding a node and an edge — no refactoring of existing nodes.

### Why PostgreSQL as a product cache (not Redis)?

- PostgreSQL is already in the stack — no extra infrastructure
- Product data is structured (price, rating, brand) — queryable, not just key-value
- TTL is implemented with a `fetched_at` timestamp + query-time filter
- At this scale, PostgreSQL read latency (1-5ms) is negligible vs API call latency (1-3s)

**Trade-off:** Redis would be faster for pure key-value lookups, but adds operational complexity.

### Why APScheduler over Celery?

- APScheduler runs inside the FastAPI process — zero additional infrastructure
- The only scheduled job is a simple daily query → alert loop
- Celery adds Redis dependency, worker process management, monitoring

**Trade-off:** If the FastAPI process restarts mid-job, the job is lost. APScheduler's `misfire_grace_time=3600` handles late starts, but for true reliability in production, migrate to Celery + Redis + persistent job store.

### Why Groq over OpenAI?

- Groq's inference speed is 5-10x faster than OpenAI for the same model class
- `llama-3.3-70b-versatile` is capable for structured output and explanation generation
- Free tier is sufficient for a portfolio project
- Easy swap: replace `ChatGroq` with `ChatOpenAI` — same LangChain interface

### Scoring Formula Rationale

```
final_score = deal_score × 0.40 + review_score × 0.35 + relevance_score × 0.25
```

- **Deal (0.40):** ShopMind's core value is price intelligence — deal quality has the highest weight
- **Review (0.35):** Social proof is the most reliable proxy for product quality
- **Relevance (0.25):** Pre-filtering ensures all candidates are broadly relevant, so this is a tiebreaker

### Mock Mode Design

`USE_MOCK_DATA` auto-enables when API keys contain placeholder values. This means:
1. The full LangGraph pipeline runs (orchestrator, preference, product_intelligence, recommendation)
2. Mock data provides 15 realistic products across 5 categories
3. Template-based explanations replace LLM calls
4. Zero paid API calls needed to demonstrate the system

---

## 8. Data Flow: Search Request

```
User types: "best wireless headphones under $100"
     │
     ▼
FastAPI POST /search
     │
     ▼
execute_search(db, user_id, query)
     │
     ▼  [GraphState built with use_mock=True/False]
graph.ainvoke(state, config={"configurable": {"db": db}})
     │
     ▼
[orchestrator]
  - Intent: "search"
  - product_query: "wireless headphones"
  - extracted_budget: 100.0
     │
     ▼
[preference]
  - Loads DB: max_budget=None, preferred_brands=[]
  - Merges: effective_budget = 100.0 (query wins)
     │
     ▼
[product_intelligence]
  - Cache check: no hit for "wireless headphones"
  - Calls mock_search_products("wireless headphones", budget=100)
  - Returns 5 products: Anker Q30 ($59.99), JBL Live 660NC ($79.99), ...
  - Saves to DB cache with trust scores
     │
     ▼
[recommendation]
  - Scores each product:
      Anker Q30: deal=0.82, review=0.71, relevance=0.68 → final=0.742
      JBL Live: deal=0.68, review=0.65, relevance=0.71 → final=0.679
  - Generates explanation: "At $59.99 — 40% below your $100 budget — the Anker Q30
    delivers hybrid ANC and a 40-hour battery, with 4.4/5 from 28k+ reviews."
     │
     ▼
SearchResponse { recommendations: [...], cache_hit: false, intent: "search" }
     │
     ▼
search_history row saved to DB
     │
     ▼
HTTP 200 → Streamlit renders ranked cards
```

---

## 9. Data Flow: Price Alert

```
08:00 UTC daily
     │
     ▼
APScheduler fires _run_price_check_job()
     │
     ▼
get_async_session() → DB session
     │
     ▼
run_alert_check(db)
     │
     ▼  [for each active WatchlistItem]
_fetch_current_price(query, title)
  → mock_search_products() or SerpAPI
     │
     ▼
if current_price <= target_price AND not already_alerted_today:
     │
     ▼
send_whatsapp_alert(user.phone, product, price, target_price)
  → Twilio API
     │
     ▼
AlertLog row saved: triggered_price, twilio_sid, status="sent"
WatchlistItem.alert_sent_count += 1
     │
     ▼
Commit transaction
```

---

## 10. Security Model

### Current (Portfolio)
- No authentication — `user_id` is a plain request parameter
- All PostgreSQL queries use SQLAlchemy ORM (parameterised — no SQL injection)
- Secrets in `.env` (gitignored); `.env.example` shows shape without values
- CORS restricted to explicit localhost origins in development

### Production Requirements
- Add JWT authentication (FastAPI OAuth2PasswordBearer)
- Rate limiting per IP + per user (fastapi-limiter + Redis)
- Input sanitisation beyond Pydantic validators
- HTTPS termination at reverse proxy (Nginx/Caddy)
- Secret management via AWS Secrets Manager / HashiCorp Vault
- CORS restricted to specific domains

---

## 11. Production Upgrade Path

| Current | Production |
|---------|-----------|
| APScheduler (in-process) | Celery + Redis + Beat |
| SQLite for tests | Dedicated test PostgreSQL (docker-compose.test.yml) |
| No auth | JWT + OAuth2 |
| No rate limiting | fastapi-limiter |
| No observability | LangSmith tracing + Prometheus metrics |
| Single Uvicorn process | Gunicorn with multiple Uvicorn workers |
| Docker Compose | Kubernetes (or ECS Fargate) |
| Manual migrations | CI-automated Alembic migrations |

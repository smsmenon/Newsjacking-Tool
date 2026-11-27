# TADA Content Intelligence Platform — System Architecture

**Version:** 1.0.0
**Date:** 2026-06-16
**Author:** @architect (CC_GodMode)
**Classification:** Internal Architecture Document

---

## 1. Executive Summary

TADA is an institutional intelligence layer — not a content generator or social media automation tool. It is a market-grade signal processing and strategic decision-support system that continuously monitors 50+ industry sources, detects meaningful signals, validates them across multiple inputs, generates strategic insights, and routes everything through human review before any output reaches stakeholders.

The platform operationalizes TADA's proprietary **Detect → Decide → Do** framework:

- **Detect:** Continuously ingest, classify, and validate signals from the market landscape
- **Decide:** Apply TADA perspective, score relevance, generate strategic recommendations
- **Do:** Surface insights to the right person at the right time via the right channel — with human approval at every gate

---

## 2. Architectural Principles

1. **Human-in-the-loop always.** No content, alert, or recommendation is auto-published. Every output routes through the Human Review System before reaching any stakeholder.
2. **Permanent, never-delete knowledge store.** The Knowledge Repository is append-only. Soft deletion only — records are archived, never erased.
3. **Signal fidelity over volume.** Quality gates (Source Quality Engine, Multi-Source Validation, Relevance Scoring) reduce noise before insights are generated.
4. **Modularity with clear contracts.** Each of the 21 modules exposes a well-defined API contract. Modules communicate via events (internal message bus) or direct API calls.
5. **Observability first.** Every agent invocation, workflow execution, and API call is traced via OpenTelemetry → Langfuse (AI traces) and Prometheus → Grafana (infrastructure metrics).
6. **Separation of concerns.** Data collection, processing, intelligence generation, and presentation are distinct layers with no cross-cutting concerns.

---

## 3. High-Level Architecture Narrative

### 3.1 The Four Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 4: PRESENTATION                                              │
│  Next.js 14 (Vercel)                                                │
│  - Market Intelligence Explorer    - Executive Portal               │
│  - Knowledge Repository UI         - Human Review Workspace         │
│  - Advanced Search                 - Trend Timeline                 │
│  - Knowledge Graph Viewer          - Content Calendar               │
└─────────────────────┬───────────────────────────────────────────────┘
                      │ HTTPS / REST / WebSocket
┌─────────────────────▼───────────────────────────────────────────────┐
│  LAYER 3: INTELLIGENCE & API                                        │
│  FastAPI (Railway)                                                   │
│  - REST API (versioned, auth-gated)                                 │
│  - WebSocket server (live alerts)                                   │
│  - LangGraph agent orchestration                                    │
│  - Langfuse observability hooks                                     │
└───────┬──────────────────────────────────────────┬──────────────────┘
        │ Internal HTTP / Event Bus                 │ Postgres + pgvector
┌───────▼──────────────────────┐  ┌────────────────▼─────────────────┐
│  LAYER 2: WORKFLOW ENGINE    │  │  LAYER 1: DATA INFRASTRUCTURE    │
│  n8n (Railway, self-hosted)  │  │  PostgreSQL (Railway)             │
│  - 10 core workflows         │  │  pgvector extension               │
│  - Cron + webhook triggers   │  │  Supabase Storage (files/media)  │
│  - Error handling + retries  │  │  Redis (cache + pub/sub)          │
│  - Alerting dispatch         │  │  S3-compatible object store       │
└──────────────────────────────┘  └──────────────────────────────────┘
```

### 3.2 The 21 Modules Grouped by Function

**Collection & Extraction (Modules 1–3)**
These modules form the raw data pipeline. The Data Collection Engine pulls from 50+ sources on scheduled and event-driven triggers. The Source Quality Engine scores each source's trust, authority, and influence. The Content Extraction Engine uses LLMs to produce structured summaries, keywords, entities, and semantic embeddings.

**Signal Intelligence (Modules 4–7)**
Raw extracted content passes through the Signal Detection Engine (anomaly and event detection), Multi-Source Validation Engine (cross-source confirmation), Trend Engine (frequency/momentum/velocity), and Customer Pain Point Detection (community sentiment mining). Only validated, scored signals proceed downstream.

**Intelligence Generation (Modules 8–10)**
The Relevance Scoring Engine applies TADA's five-dimensional scoring rubric. The TADA Perspective Engine generates the six-part insight frame (What/Why/Impact/Traditional Response/TADA Response/D-D-D). The Strategic Recommendation Engine produces persona-specific recommendations for Marketing, Sales, Leadership, CS, and Product.

**Content & Calendar (Modules 11–12)**
The Content Strategy Engine maps approved insights to content formats (LinkedIn posts, articles, newsletters, executive briefings). The Content Calendar Engine schedules and sequences across weekly/monthly/quarterly horizons.

**Knowledge Infrastructure (Modules 13–17)**
The Knowledge Repository is the permanent, append-only store. The Market Intelligence Explorer provides a browsable portal. Advanced Search supports keyword, semantic, hybrid, and vector modalities. The Knowledge Graph maps entity relationships. The Trend Timeline provides longitudinal visualization.

**Decision Support & Operations (Modules 18–21)**
The Executive Portal surfaces top risks, opportunities, trends, and actions. The Alerting System dispatches breaking events to Slack/Teams/email. The Human Review System manages the full approval workflow (Draft → Under Review → Approved → Rejected → Published). The AI Agent Architecture coordinates 13 specialized agents.

---

## 4. Module Interaction Map

```
 EXTERNAL SOURCES
 RSS / APIs / Web / Social / Podcasts / Video
        │
        ▼
┌───────────────────┐
│ 01. DATA          │──── Source metadata ────►┌──────────────────────┐
│    COLLECTION     │                          │ 02. SOURCE QUALITY   │
│    ENGINE         │◄── Quality scores ───────│    ENGINE            │
└────────┬──────────┘                          └──────────────────────┘
         │ Raw content
         ▼
┌───────────────────┐
│ 03. CONTENT       │──── Embeddings ──────────► pgvector store
│    EXTRACTION     │──── Entities ────────────► Entity registry
│    ENGINE         │──── Summaries ───────────► Raw content DB
└────────┬──────────┘
         │ Structured content
         ▼
┌───────────────────┐    ┌───────────────────┐
│ 04. SIGNAL        │◄──►│ 05. MULTI-SOURCE  │
│    DETECTION      │    │    VALIDATION     │
│    ENGINE         │    │    ENGINE         │
└────────┬──────────┘    └───────────────────┘
         │ Validated signals
    ┌────┴──────┐
    ▼           ▼
┌────────┐  ┌────────────────┐
│ 06.    │  │ 07. CUSTOMER   │
│ TREND  │  │    PAIN POINT  │
│ ENGINE │  │    DETECTION   │
└────┬───┘  └───────┬────────┘
     │               │
     └──────┬────────┘
            │ Enriched signals
            ▼
┌───────────────────┐
│ 08. RELEVANCE     │
│    SCORING        │
│    ENGINE         │
└────────┬──────────┘
         │ Scored & prioritized signals
         ▼
┌───────────────────┐
│ 09. TADA          │
│    PERSPECTIVE    │
│    ENGINE         │
└────────┬──────────┘
         │ Framed insights (What/Why/Impact/D-D-D)
         ▼
┌───────────────────┐
│ 10. STRATEGIC     │◄──── Persona profiles (Marketing/Sales/Leadership/CS/Product)
│    RECOMMENDATION │
│    ENGINE         │
└────────┬──────────┘
         │ Strategic recommendations
    ┌────┴──────────────────────────────────┐
    ▼                                       ▼
┌────────────────────┐            ┌──────────────────────┐
│ 11. CONTENT        │            │ 18. EXECUTIVE        │
│    STRATEGY        │            │    PORTAL            │
│    ENGINE          │            │    (aggregation)     │
└────────┬───────────┘            └──────────────────────┘
         │
         ▼
┌───────────────────┐
│ 12. CONTENT       │
│    CALENDAR       │
│    ENGINE         │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐    ┌─────────────────────────────────────────┐
│ 20. HUMAN REVIEW  │───►│ 13. KNOWLEDGE REPOSITORY (permanent)    │
│    SYSTEM         │    │     → 14. MI Explorer                   │
│ (Draft→Review     │    │     → 15. Advanced Search               │
│  →Approved→       │    │     → 16. Knowledge Graph               │
│  Published)       │    │     → 17. Trend Timeline                │
└────────┬──────────┘    └─────────────────────────────────────────┘
         │
         ▼
┌───────────────────┐
│ 19. ALERTING      │──── Slack / Teams / Email
│    SYSTEM         │
└───────────────────┘
```

---

## 5. Data Flow Description

### 5.1 Primary Flow: Source → Signal → Insight → Review

**Step 1 — Ingestion (every 15 min for RSS/API, 4hr for web scrape, 1hr for social)**
- n8n Daily Collection Workflow triggers Collection Agent
- Collection Agent fetches raw content from 50+ sources
- Content fingerprinted (SHA-256) — duplicates rejected at intake
- Raw content stored in `raw_content` table with source metadata

**Step 2 — Quality Gate**
- Source Quality Engine evaluates source on: trust score, domain authority, influence score, historical accuracy, recency
- Content below quality threshold (< 40/100) quarantined, not discarded
- Quality score stored with content record

**Step 3 — Extraction**
- Content Extraction Engine runs LLM pipeline:
  - Named entity recognition (companies, people, products, locations)
  - Keyword extraction (TF-IDF + LLM)
  - Summary generation (3-sentence + 1-paragraph)
  - Embedding generation (text-embedding-3-large → 3072 dimensions → pgvector)
- Structured record upserted to `content_items` table

**Step 4 — Signal Detection**
- Signal Detection Agent evaluates content against:
  - Anomaly patterns (statistical deviation from baseline)
  - Event taxonomies (funding, acquisition, product launch, regulation, executive change)
  - Semantic similarity to known signal patterns
- Signals with confidence ≥ 0.65 flagged, below threshold stored as `low_confidence`

**Step 5 — Cross-Source Validation**
- Multi-Source Validation Engine queries: "Has this signal appeared in ≥ 2 independent sources within 48hr?"
- Validated signals get `multi_source_confirmed = true`
- Validation increases relevance score multiplier

**Step 6 — Trend & Pain Point Enrichment**
- Trend Engine calculates frequency (mentions/day), momentum (rate of change), velocity (acceleration)
- Pain Point Detection scans Reddit/LinkedIn/X for related community signals
- Both outputs appended to signal record

**Step 7 — Relevance Scoring**
- Five-dimension scoring applied:
  - Supply Chain relevance (30%)
  - Executive relevance (20%)
  - Business Impact potential (20%)
  - Technology relevance (15%)
  - TADA alignment (15%)
- Weighted score 0–100; signals below 45 archived without further processing

**Step 8 — TADA Perspective Generation**
- TADA Perspective Engine generates six-part frame:
  1. What is happening
  2. Why it matters
  3. Business impact
  4. Traditional industry response
  5. TADA's differentiated response
  6. Detect → Decide → Do action frame
- Draft insight record created with status `DRAFT`

**Step 9 — Strategic Recommendations**
- Recommendation Engine generates persona-specific actions:
  - Marketing: messaging angles, content opportunities, positioning shifts
  - Sales: talking points, objection handling, opportunity signals
  - Leadership: strategic decisions, risk assessments, priority shifts
  - Customer Success: retention risks, upsell triggers, health signals
  - Product: feature requests, competitive gaps, roadmap inputs

**Step 10 — Human Review**
- Full insight package routes to Review Queue
- Reviewer assigned based on topic domain
- Status transitions: DRAFT → UNDER_REVIEW → APPROVED | REJECTED → PUBLISHED
- Published insights land in Knowledge Repository (permanent)

---

## 6. Integration Points

### 6.1 External Data Sources
| Source Type | Integration Method | Frequency | Volume |
|-------------|-------------------|-----------|--------|
| RSS/Atom feeds | Native RSS parsing (feedparser) | 15 min | 200–500 items/day |
| REST APIs (news, financial) | HTTP polling with rate limiting | 1 hr | 100–300/day |
| Twitter/X | Twitter API v2 (Academic) | 30 min | 500–1000/day |
| LinkedIn | Proxycurl API / manual export | 4 hr | 50–100/day |
| Reddit | Reddit API (PRAW) | 1 hr | 200–400/day |
| Web scraping | Playwright + Crawl4AI | 6 hr | 50–100/day |
| Podcasts | RSS + Whisper transcription | 24 hr | 10–20/day |
| YouTube | YouTube Data API v3 + Whisper | 24 hr | 10–20/day |
| Analyst reports | PDF extraction (pdfplumber) | 24 hr | 5–10/day |
| Newsletters | Email ingestion (IMAP) | 4 hr | 20–30/day |

### 6.2 Internal Integrations
| System | Protocol | Purpose |
|--------|----------|---------|
| n8n → FastAPI | HTTP webhook + REST | Workflow → API triggers |
| FastAPI → LangGraph | Python in-process | Agent orchestration |
| FastAPI → PostgreSQL | asyncpg / SQLAlchemy | Primary data store |
| FastAPI → pgvector | pgvector Python client | Semantic search |
| FastAPI → Supabase | Supabase Python SDK | File/media storage |
| FastAPI → Redis | aioredis | Cache + pub/sub alerts |
| FastAPI → Langfuse | Langfuse SDK | AI observability |
| Next.js → FastAPI | REST + WebSocket | Frontend data layer |
| Next.js → Clerk | Clerk Next.js SDK | Authentication |
| n8n → Slack | Slack node | Alert delivery |
| n8n → Teams | Microsoft Teams node | Alert delivery |
| n8n → Email | SMTP node | Alert delivery |

### 6.3 Authentication & Authorization
- **Frontend:** Clerk handles user authentication (JWT)
- **API:** Clerk JWT verified on every FastAPI request via middleware
- **n8n:** Internal API key authentication (not user-facing)
- **RBAC Roles:**
  - `admin` — full system access
  - `analyst` — read all, write drafts, submit for review
  - `reviewer` — read all, approve/reject insights
  - `executive` — read Executive Portal + approved insights only
  - `viewer` — read-only access to published insights

---

## 7. Scalability Considerations

### 7.1 Database Scaling Strategy
- **pgvector indexes:** IVFFlat index with 100 lists for initial scale; migrate to HNSW at 1M+ embeddings
- **Table partitioning:** `raw_content` and `content_items` partitioned by ingestion month
- **Read replicas:** Separate read replicas for search and analytics queries
- **Connection pooling:** PgBouncer in transaction mode (Railway managed)

### 7.2 Agent Scaling
- LangGraph agents run as async tasks within FastAPI
- CPU-bound extraction tasks offloaded to Celery workers (Redis broker)
- Agent concurrency limit: 10 parallel agent invocations per workflow trigger
- LLM cost control: GPT-4o for perspective/recommendation, GPT-4o-mini for extraction/classification

### 7.3 n8n Scaling
- n8n runs in queue mode (not webhook mode) for production
- Separate n8n worker instances for collection vs. processing workflows
- Dead-letter queue for failed workflow executions

### 7.4 Frontend Scaling
- Next.js on Vercel with Edge Runtime for low-latency API routes
- ISR (Incremental Static Regeneration) for Knowledge Repository browse pages
- React Query for client-side caching and background refetch
- Infinite scroll with cursor-based pagination for all list views

### 7.5 Future Scale Points
- At 10M+ knowledge items: Elasticsearch layer for full-text search alongside pgvector
- At 100+ concurrent users: CDN caching for public knowledge views
- At 1000+ sources: distributed collection workers (Kubernetes job queue)
- Multi-tenancy: Clerk organization model + PostgreSQL row-level security

---

## 8. Security Architecture

- All inter-service communication over TLS 1.3
- Secrets managed via Railway environment variables + Doppler (not in code)
- n8n credentials encrypted at rest (n8n built-in vault)
- PostgreSQL: encrypted at rest (Railway managed), SSL-only connections
- Supabase: RLS policies aligned to Clerk user IDs
- Rate limiting: FastAPI middleware (slowapi) — 100 req/min per user
- Input sanitization: Pydantic models at all API boundaries
- Audit log: every state transition in Human Review System logged with user + timestamp

---

## 9. Observability Stack

```
Application Layer
  └── OpenTelemetry SDK (traces, metrics, logs)
        ├── AI traces → Langfuse (LLM calls, token usage, latency, quality scores)
        └── Infrastructure traces → Prometheus
              └── Dashboards → Grafana
                    ├── Collection pipeline health
                    ├── Signal detection rates
                    ├── Agent performance metrics
                    ├── Review queue throughput
                    └── Cost tracking (LLM spend/day)
```

Key metrics tracked:
- `signals_detected_total` — counter by signal type
- `insights_in_review_gauge` — current review queue depth
- `agent_invocation_duration_histogram` — p50/p95/p99 by agent
- `collection_source_health` — success/failure rate per source
- `embedding_generation_duration` — latency for pgvector operations
- `relevance_score_distribution` — histogram of scores (quality signal)

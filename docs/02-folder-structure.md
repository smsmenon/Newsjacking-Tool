# TADA Content Intelligence Platform — Monorepo Folder Structure

**Version:** 1.0.0
**Date:** 2026-06-16

This document describes the complete folder structure for the `tada-intelligence` monorepo. Every directory is annotated with its purpose and key files.

---

## Complete Structure

```
tada-intelligence/
│
│   # Root config files
├── .env.example                    # Template for all required environment variables
├── .gitignore                      # Global gitignore (node_modules, __pycache__, .env, etc.)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # CI: lint + test on every PR
│   │   ├── deploy-frontend.yml     # CD: deploy Next.js to Vercel on main merge
│   │   ├── deploy-api.yml          # CD: deploy FastAPI to Railway on main merge
│   │   └── deploy-agents.yml       # CD: deploy LangGraph agents to Railway
│   └── PULL_REQUEST_TEMPLATE.md
├── turbo.json                      # Turborepo pipeline config (build/test/lint ordering)
├── package.json                    # Root workspace package.json (pnpm workspaces)
├── pnpm-workspace.yaml             # pnpm workspace definition
├── pyproject.toml                  # Root Python tooling config (ruff, mypy, pytest)
│
│
├── apps/
│   │
│   ├── web/                        # Next.js 14 frontend (App Router) — deployed to Vercel
│   │   ├── .env.local.example
│   │   ├── next.config.js          # Next.js config (env vars, image domains, rewrites)
│   │   ├── tailwind.config.ts      # Tailwind CSS config
│   │   ├── tsconfig.json
│   │   ├── package.json
│   │   │
│   │   ├── public/                 # Static assets
│   │   │   ├── logo.svg
│   │   │   ├── favicon.ico
│   │   │   └── og-image.png
│   │   │
│   │   └── src/
│   │       │
│   │       ├── app/                # Next.js App Router pages
│   │       │   ├── layout.tsx      # Root layout (Clerk provider, theme)
│   │       │   ├── page.tsx        # Landing / redirect to dashboard
│   │       │   ├── globals.css
│   │       │   │
│   │       │   ├── (auth)/         # Auth route group
│   │       │   │   ├── sign-in/
│   │       │   │   │   └── [[...sign-in]]/
│   │       │   │   │       └── page.tsx
│   │       │   │   └── sign-up/
│   │       │   │       └── [[...sign-up]]/
│   │       │   │           └── page.tsx
│   │       │   │
│   │       │   ├── (dashboard)/    # Protected dashboard route group
│   │       │   │   ├── layout.tsx  # Dashboard layout (sidebar, topbar)
│   │       │   │   ├── page.tsx    # Dashboard home (summary widgets)
│   │       │   │   │
│   │       │   │   ├── intelligence/           # Market Intelligence Explorer
│   │       │   │   │   ├── page.tsx            # Browse all insights (filterable list)
│   │       │   │   │   ├── [id]/
│   │       │   │   │   │   └── page.tsx        # Single insight detail view
│   │       │   │   │   └── loading.tsx
│   │       │   │   │
│   │       │   │   ├── signals/                # Signal feed
│   │       │   │   │   ├── page.tsx            # All detected signals
│   │       │   │   │   └── [id]/
│   │       │   │   │       └── page.tsx        # Signal detail + evidence chain
│   │       │   │   │
│   │       │   │   ├── trends/                 # Trend Timeline
│   │       │   │   │   ├── page.tsx            # Trend overview (cards + timeline)
│   │       │   │   │   └── [slug]/
│   │       │   │   │       └── page.tsx        # Trend deep-dive with timeline chart
│   │       │   │   │
│   │       │   │   ├── knowledge/              # Knowledge Repository
│   │       │   │   │   ├── page.tsx            # Browsable knowledge base
│   │       │   │   │   ├── search/
│   │       │   │   │   │   └── page.tsx        # Advanced search UI
│   │       │   │   │   └── graph/
│   │       │   │   │       └── page.tsx        # Knowledge graph visualization
│   │       │   │   │
│   │       │   │   ├── executive/              # Executive Portal
│   │       │   │   │   ├── page.tsx            # Executive summary (risks, opps, trends)
│   │       │   │   │   ├── briefings/
│   │       │   │   │   │   ├── page.tsx        # All executive briefings
│   │       │   │   │   │   └── [id]/
│   │       │   │   │   │       └── page.tsx    # Single briefing view
│   │       │   │   │   └── alerts/
│   │       │   │   │       └── page.tsx        # Alert history + config
│   │       │   │   │
│   │       │   │   ├── review/                 # Human Review System
│   │       │   │   │   ├── page.tsx            # Review queue (Draft/Under Review)
│   │       │   │   │   └── [id]/
│   │       │   │   │       └── page.tsx        # Review workspace (diff, approve, reject)
│   │       │   │   │
│   │       │   │   ├── calendar/               # Content Calendar Engine UI
│   │       │   │   │   ├── page.tsx            # Monthly calendar view
│   │       │   │   │   └── weekly/
│   │       │   │   │       └── page.tsx        # Weekly agenda view
│   │       │   │   │
│   │       │   │   ├── competitors/            # Competitive Intelligence
│   │       │   │   │   ├── page.tsx            # Competitor landscape
│   │       │   │   │   └── [id]/
│   │       │   │   │       └── page.tsx        # Competitor profile
│   │       │   │   │
│   │       │   │   ├── sources/                # Source management
│   │       │   │   │   ├── page.tsx            # Source registry (all 50+ sources)
│   │       │   │   │   └── [id]/
│   │       │   │   │       └── page.tsx        # Source health + history
│   │       │   │   │
│   │       │   │   └── settings/               # Platform settings
│   │       │   │       ├── page.tsx
│   │       │   │       ├── alerts/
│   │       │   │       │   └── page.tsx        # Alert routing config
│   │       │   │       ├── team/
│   │       │   │       │   └── page.tsx        # Team management (Clerk org)
│   │       │   │       └── integrations/
│   │       │   │           └── page.tsx        # Slack/Teams/email config
│   │       │   │
│   │       │   └── api/                        # Next.js API Routes (thin proxies)
│   │       │       └── [...path]/
│   │       │           └── route.ts            # Proxy to FastAPI (auth header injection)
│   │       │
│   │       ├── components/
│   │       │   ├── ui/                         # Shadcn/ui base components (auto-generated)
│   │       │   │   ├── button.tsx
│   │       │   │   ├── card.tsx
│   │       │   │   ├── dialog.tsx
│   │       │   │   ├── input.tsx
│   │       │   │   ├── badge.tsx
│   │       │   │   ├── table.tsx
│   │       │   │   ├── tabs.tsx
│   │       │   │   └── ...
│   │       │   │
│   │       │   ├── layout/
│   │       │   │   ├── Sidebar.tsx             # Navigation sidebar
│   │       │   │   ├── Topbar.tsx              # Top navigation bar
│   │       │   │   └── PageHeader.tsx
│   │       │   │
│   │       │   ├── intelligence/
│   │       │   │   ├── InsightCard.tsx         # Insight summary card
│   │       │   │   ├── InsightDetail.tsx       # Full insight view
│   │       │   │   ├── SignalBadge.tsx          # Signal type/strength indicator
│   │       │   │   ├── RelevanceScore.tsx      # Score breakdown widget
│   │       │   │   └── TadaPerspective.tsx     # What/Why/Impact/D-D-D display
│   │       │   │
│   │       │   ├── review/
│   │       │   │   ├── ReviewQueue.tsx         # Sortable/filterable queue
│   │       │   │   ├── ReviewWorkspace.tsx     # Full review editor
│   │       │   │   ├── StatusBadge.tsx         # Draft/Review/Approved etc.
│   │       │   │   └── ApprovalDialog.tsx      # Confirm approve/reject
│   │       │   │
│   │       │   ├── search/
│   │       │   │   ├── SearchBar.tsx           # Unified search input
│   │       │   │   ├── SearchResults.tsx       # Result list with highlighting
│   │       │   │   ├── SearchFilters.tsx       # Date, topic, type filters
│   │       │   │   └── SemanticToggle.tsx      # Keyword vs. semantic mode
│   │       │   │
│   │       │   ├── graph/
│   │       │   │   ├── KnowledgeGraph.tsx      # D3/Sigma.js graph canvas
│   │       │   │   ├── GraphControls.tsx       # Zoom, filter, cluster controls
│   │       │   │   └── NodePopup.tsx           # Node detail on click
│   │       │   │
│   │       │   ├── trends/
│   │       │   │   ├── TrendTimeline.tsx       # Recharts/Observable timeline
│   │       │   │   ├── TrendCard.tsx           # Trend summary card
│   │       │   │   └── MomentumIndicator.tsx   # Velocity/momentum visual
│   │       │   │
│   │       │   ├── executive/
│   │       │   │   ├── RiskMatrix.tsx          # 2x2 risk/impact matrix
│   │       │   │   ├── OpportunityList.tsx     # Ranked opportunity list
│   │       │   │   ├── BriefingViewer.tsx      # Executive briefing reader
│   │       │   │   └── AlertFeed.tsx           # Live alert stream
│   │       │   │
│   │       │   └── calendar/
│   │       │       ├── CalendarView.tsx        # Monthly calendar grid
│   │       │       ├── ContentSlot.tsx         # Scheduled content item
│   │       │       └── WeeklyAgenda.tsx        # Weekly list view
│   │       │
│   │       ├── hooks/
│   │       │   ├── useInsights.ts              # Insights data fetching
│   │       │   ├── useSignals.ts               # Signals feed
│   │       │   ├── useSearch.ts                # Search with debounce
│   │       │   ├── useReviewQueue.ts           # Review queue polling
│   │       │   ├── useAlerts.ts                # WebSocket alert stream
│   │       │   └── useKnowledgeGraph.ts        # Graph data loading
│   │       │
│   │       ├── lib/
│   │       │   ├── api.ts                      # Typed API client (fetch wrapper)
│   │       │   ├── auth.ts                     # Clerk auth helpers
│   │       │   ├── constants.ts                # App-wide constants
│   │       │   └── utils.ts                    # cn(), formatDate(), etc.
│   │       │
│   │       └── types/
│   │           ├── insight.ts                  # Insight type definitions
│   │           ├── signal.ts                   # Signal type definitions
│   │           ├── source.ts                   # Source type definitions
│   │           └── index.ts                    # Re-exports
│   │
│   │
│   ├── api/                        # FastAPI backend — deployed to Railway
│   │   ├── .env.example
│   │   ├── pyproject.toml          # Python project (uv/pip)
│   │   ├── Dockerfile
│   │   ├── railway.json            # Railway deployment config
│   │   │
│   │   └── src/
│   │       └── tada_api/
│   │           ├── main.py         # FastAPI app factory, middleware registration
│   │           ├── config.py       # Settings (pydantic-settings, env var loading)
│   │           ├── deps.py         # FastAPI dependency injection (DB, auth, cache)
│   │           │
│   │           ├── routers/        # API route handlers (one file per resource domain)
│   │           │   ├── __init__.py
│   │           │   ├── insights.py         # GET/POST/PATCH /insights
│   │           │   ├── signals.py          # GET /signals, POST /signals/detect
│   │           │   ├── sources.py          # CRUD /sources
│   │           │   ├── search.py           # POST /search (keyword/semantic/hybrid)
│   │           │   ├── trends.py           # GET /trends, GET /trends/{id}/timeline
│   │           │   ├── knowledge.py        # GET /knowledge (repository browse)
│   │           │   ├── review.py           # GET /review/queue, PATCH /review/{id}/status
│   │           │   ├── executive.py        # GET /executive/briefings, /risks, /opportunities
│   │           │   ├── calendar.py         # GET/POST /calendar/entries
│   │           │   ├── alerts.py           # GET /alerts, POST /alerts/config
│   │           │   ├── competitors.py      # GET /competitors, /competitors/{id}
│   │           │   ├── graph.py            # GET /graph/nodes, /graph/edges
│   │           │   ├── agents.py           # POST /agents/trigger (manual agent runs)
│   │           │   └── webhooks.py         # POST /webhooks/n8n (n8n → API callbacks)
│   │           │
│   │           ├── models/         # SQLAlchemy ORM models
│   │           │   ├── __init__.py
│   │           │   ├── base.py             # Base model (id, created_at, updated_at)
│   │           │   ├── source.py           # Source, SourceQualityScore
│   │           │   ├── raw_content.py      # RawContent
│   │           │   ├── content_item.py     # ContentItem (extracted, embedded)
│   │           │   ├── signal.py           # Signal, SignalValidation
│   │           │   ├── trend.py            # Trend, TrendDataPoint
│   │           │   ├── insight.py          # Insight, InsightRecommendation
│   │           │   ├── review.py           # ReviewRecord, ReviewComment
│   │           │   ├── knowledge_item.py   # KnowledgeItem (permanent store)
│   │           │   ├── entity.py           # Entity, EntityRelationship (knowledge graph)
│   │           │   ├── calendar_entry.py   # CalendarEntry
│   │           │   ├── alert.py            # Alert, AlertConfig
│   │           │   └── competitor.py       # Competitor, CompetitorActivity
│   │           │
│   │           ├── schemas/        # Pydantic request/response schemas
│   │           │   ├── __init__.py
│   │           │   ├── insight.py
│   │           │   ├── signal.py
│   │           │   ├── source.py
│   │           │   ├── search.py
│   │           │   ├── trend.py
│   │           │   ├── review.py
│   │           │   ├── executive.py
│   │           │   ├── calendar.py
│   │           │   ├── alert.py
│   │           │   └── graph.py
│   │           │
│   │           ├── services/       # Business logic (called by routers)
│   │           │   ├── __init__.py
│   │           │   ├── collection_service.py       # Module 01: source fetching orchestration
│   │           │   ├── quality_service.py          # Module 02: source quality scoring
│   │           │   ├── extraction_service.py       # Module 03: content extraction
│   │           │   ├── signal_service.py           # Module 04: signal detection
│   │           │   ├── validation_service.py       # Module 05: multi-source validation
│   │           │   ├── trend_service.py            # Module 06: trend tracking
│   │           │   ├── pain_point_service.py       # Module 07: pain point detection
│   │           │   ├── relevance_service.py        # Module 08: relevance scoring
│   │           │   ├── perspective_service.py      # Module 09: TADA perspective
│   │           │   ├── recommendation_service.py   # Module 10: strategic recs
│   │           │   ├── content_strategy_service.py # Module 11: content strategy
│   │           │   ├── calendar_service.py         # Module 12: calendar management
│   │           │   ├── knowledge_service.py        # Module 13: repository operations
│   │           │   ├── search_service.py           # Module 15: advanced search
│   │           │   ├── graph_service.py            # Module 16: knowledge graph
│   │           │   ├── review_service.py           # Module 20: human review workflow
│   │           │   └── alert_service.py            # Module 19: alert dispatch
│   │           │
│   │           ├── agents/         # LangGraph agent definitions (imported by services)
│   │           │   ├── __init__.py
│   │           │   ├── base.py                 # Base agent class, common tools
│   │           │   ├── research_agent.py       # Research Agent
│   │           │   ├── collection_agent.py     # Collection Agent
│   │           │   ├── signal_agent.py         # Signal Detection Agent
│   │           │   ├── trend_agent.py          # Trend Agent
│   │           │   ├── competitive_agent.py    # Competitive Intelligence Agent
│   │           │   ├── pain_point_agent.py     # Pain Point Agent
│   │           │   ├── perspective_agent.py    # TADA Perspective Agent
│   │           │   ├── content_strategy_agent.py  # Content Strategy Agent
│   │           │   ├── sales_agent.py          # Sales Intelligence Agent
│   │           │   ├── executive_agent.py      # Executive Briefing Agent
│   │           │   ├── qa_agent.py             # QA Agent
│   │           │   ├── repository_agent.py     # Repository Agent
│   │           │   └── recommendation_agent.py # Recommendation Agent
│   │           │
│   │           ├── tools/          # LangGraph tool definitions
│   │           │   ├── __init__.py
│   │           │   ├── web_tools.py            # fetch_url, search_web, scrape_page
│   │           │   ├── db_tools.py             # query_knowledge, store_content, etc.
│   │           │   ├── search_tools.py         # semantic_search, keyword_search
│   │           │   ├── llm_tools.py            # summarize, extract_entities, embed
│   │           │   ├── social_tools.py         # fetch_reddit, fetch_twitter, fetch_linkedin
│   │           │   └── validation_tools.py     # cross_source_check, confidence_score
│   │           │
│   │           ├── db/
│   │           │   ├── __init__.py
│   │           │   ├── database.py             # SQLAlchemy async engine + session factory
│   │           │   ├── migrations/             # Alembic migrations
│   │           │   │   ├── env.py
│   │           │   │   ├── script.py.mako
│   │           │   │   └── versions/
│   │           │   │       ├── 0001_initial_schema.py
│   │           │   │       ├── 0002_add_pgvector.py
│   │           │   │       ├── 0003_add_knowledge_graph.py
│   │           │   │       └── ...
│   │           │   └── seeds/
│   │           │       ├── sources.py          # Seed 50+ initial sources
│   │           │       └── categories.py       # Seed topic categories
│   │           │
│   │           ├── middleware/
│   │           │   ├── auth.py                 # Clerk JWT verification
│   │           │   ├── rate_limit.py           # slowapi rate limiting
│   │           │   ├── logging.py              # Structured logging (structlog)
│   │           │   └── telemetry.py            # OpenTelemetry instrumentation
│   │           │
│   │           ├── tasks/          # Celery async task definitions
│   │           │   ├── __init__.py
│   │           │   ├── celery_app.py           # Celery app factory
│   │           │   ├── extraction_tasks.py     # Async embedding + extraction
│   │           │   ├── alert_tasks.py          # Async alert dispatch
│   │           │   └── sync_tasks.py           # Knowledge repository sync
│   │           │
│   │           └── utils/
│   │               ├── __init__.py
│   │               ├── fingerprint.py          # SHA-256 content deduplication
│   │               ├── text.py                 # Text cleaning utilities
│   │               ├── date.py                 # Date parsing utilities
│   │               └── scoring.py              # Weighted scoring utilities
│   │
│   │
│   └── agents/                     # LangGraph agent runner — deployed to Railway
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── railway.json
│       └── src/
│           └── tada_agents/
│               ├── main.py         # Agent runner entrypoint (FastAPI server for agent triggers)
│               ├── config.py
│               ├── graphs/         # LangGraph graph definitions
│               │   ├── collection_graph.py     # Collection pipeline graph
│               │   ├── signal_graph.py         # Signal detection graph
│               │   ├── intelligence_graph.py   # Insight generation graph
│               │   └── briefing_graph.py       # Executive briefing graph
│               └── checkpointer/
│                   └── postgres_checkpointer.py  # LangGraph state persistence
│
│
├── packages/
│   │
│   ├── shared/                     # Shared TypeScript types and utilities
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── types/
│   │       │   ├── insight.ts
│   │       │   ├── signal.ts
│   │       │   ├── source.ts
│   │       │   ├── review.ts
│   │       │   ├── trend.ts
│   │       │   ├── executive.ts
│   │       │   └── index.ts
│   │       └── utils/
│   │           ├── format.ts       # Date, number, score formatting
│   │           └── constants.ts    # Shared constants
│   │
│   └── ui/                         # Shared component library
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── components/         # Reusable cross-app components
│           └── index.ts
│
│
├── infrastructure/
│   │
│   ├── docker/
│   │   ├── docker-compose.yml          # Local dev: all services
│   │   ├── docker-compose.prod.yml     # Production compose (Railway reference)
│   │   ├── Dockerfile.api              # FastAPI Dockerfile
│   │   ├── Dockerfile.agents           # LangGraph agents Dockerfile
│   │   └── Dockerfile.n8n              # n8n Dockerfile (custom with extra nodes)
│   │
│   ├── n8n/
│   │   ├── workflows/                  # Exported n8n workflow JSON files
│   │   │   ├── 01-daily-collection.json
│   │   │   ├── 02-signal-detection.json
│   │   │   ├── 03-trend-analysis.json
│   │   │   ├── 04-competitive-intelligence.json
│   │   │   ├── 05-pain-point-detection.json
│   │   │   ├── 06-executive-briefing.json
│   │   │   ├── 07-content-calendar.json
│   │   │   ├── 08-alert-trigger.json
│   │   │   ├── 09-human-review-notification.json
│   │   │   └── 10-repository-sync.json
│   │   ├── credentials/                # Encrypted credential templates
│   │   │   └── credentials.example.json
│   │   └── config/
│   │       └── n8n-config.json         # n8n instance configuration
│   │
│   ├── terraform/                  # Infrastructure as Code (Railway + Vercel)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── railway/
│   │   │   │   ├── main.tf         # Railway project, services, envvars
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   └── vercel/
│   │   │       ├── main.tf         # Vercel project, domains, env
│   │   │       ├── variables.tf
│   │   │       └── outputs.tf
│   │   └── environments/
│   │       ├── staging.tfvars
│   │       └── production.tfvars
│   │
│   ├── postgres/
│   │   ├── init.sql                # Initial DB setup + pgvector extension
│   │   ├── indexes.sql             # IVFFlat + HNSW indexes for pgvector
│   │   └── rls-policies.sql        # Row-level security policies
│   │
│   └── scripts/
│       ├── setup-dev.sh            # Local dev environment setup
│       ├── seed-sources.py         # Seed 50+ initial sources into DB
│       ├── import-n8n-workflows.sh # Import all workflow JSON into n8n
│       ├── health-check.sh         # Check all services are healthy
│       └── rotate-secrets.sh       # Rotate API keys across all services
│
│
├── docs/
│   ├── 01-system-architecture.md       # This system (you are here)
│   ├── 02-folder-structure.md          # This file
│   ├── 03-api-reference.md             # Auto-generated FastAPI OpenAPI docs
│   ├── 04-data-dictionary.md           # All DB tables/columns explained
│   ├── 05-source-registry.md           # 50+ sources with metadata
│   ├── 06-relevance-scoring-guide.md   # How to tune the 5-dimension scoring
│   ├── 07-review-workflow.md           # Human review process guide
│   ├── 08-alert-configuration.md       # How to configure alerts
│   ├── 09-onboarding.md                # New team member onboarding
│   └── 10-runbooks.md                  # Operational runbooks
│
│
├── architecture/
│   ├── mermaid-diagrams.md         # All 8 Mermaid diagrams
│   ├── agent-architecture.md       # All 13 AI agents defined
│   └── workflow-architecture.md    # All 10 n8n workflows defined
│
│
└── tests/
    ├── api/                        # FastAPI integration tests
    │   ├── conftest.py
    │   ├── test_insights.py
    │   ├── test_signals.py
    │   ├── test_search.py
    │   └── test_review.py
    ├── agents/                     # Agent unit tests
    │   ├── test_collection_agent.py
    │   ├── test_signal_agent.py
    │   └── test_perspective_agent.py
    ├── services/                   # Service unit tests
    │   ├── test_relevance_scoring.py
    │   ├── test_source_quality.py
    │   └── test_extraction.py
    └── e2e/                        # End-to-end tests (Playwright)
        ├── review-workflow.spec.ts
        ├── search.spec.ts
        └── executive-portal.spec.ts
```

---

## Key Technology Decisions by Directory

| Directory | Technology | Rationale |
|-----------|-----------|-----------|
| `apps/web/` | Next.js 14, App Router, Tailwind, shadcn/ui | SSR for SEO on public pages, RSC for data-heavy dashboards |
| `apps/api/` | FastAPI, asyncpg, SQLAlchemy 2.0 | Async-first Python for I/O-bound agent workloads |
| `apps/agents/` | LangGraph, LangChain | Stateful agent graphs with checkpointing and human-in-the-loop |
| `infrastructure/n8n/` | n8n self-hosted | Visual workflow orchestration, rich connector library, no per-execution cost |
| `infrastructure/terraform/` | Terraform | Reproducible infra across staging/production |
| `tests/e2e/` | Playwright | Cross-browser E2E testing for critical workflows |

---

## Environment Variables (Key)

All environment variables follow the pattern `TADA_{SERVICE}_{NAME}`:

```
# Database
TADA_DB_URL=postgresql+asyncpg://...
TADA_DB_POOL_SIZE=20

# AI
TADA_OPENAI_API_KEY=sk-...
TADA_OPENAI_MODEL_LARGE=gpt-4o
TADA_OPENAI_MODEL_SMALL=gpt-4o-mini
TADA_EMBEDDING_MODEL=text-embedding-3-large

# Auth
TADA_CLERK_SECRET_KEY=sk_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...

# Storage
TADA_SUPABASE_URL=https://...
TADA_SUPABASE_SERVICE_KEY=...

# Observability
TADA_LANGFUSE_PUBLIC_KEY=pk-lf-...
TADA_LANGFUSE_SECRET_KEY=sk-lf-...
TADA_OTEL_ENDPOINT=http://...

# Alerts
TADA_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TADA_SLACK_BOT_TOKEN=xoxb-...
TADA_TEAMS_WEBHOOK_URL=https://...

# Social APIs
TADA_TWITTER_BEARER_TOKEN=...
TADA_REDDIT_CLIENT_ID=...
TADA_REDDIT_CLIENT_SECRET=...
TADA_PROXYCURL_API_KEY=...

# Internal
TADA_N8N_WEBHOOK_SECRET=...
TADA_API_INTERNAL_KEY=...
TADA_REDIS_URL=redis://...
```

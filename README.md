# TADA Intelligence Platform v1.0.0

> **TADA's Proprietary Market Intelligence Operating System**
>
> Monitor → Detect → Decide → Do

---

## What This Platform Is

TADA Intelligence Platform is a **Market Intelligence, Competitive Intelligence, Content Intelligence, Sales Intelligence, and Executive Decision Support Platform** — not a content generator, not social media automation, not an article summarizer.

It is TADA's **institutional intelligence layer**: a system that continuously monitors the external market, identifies meaningful signals, interprets them through TADA's strategic lens, and provides actionable recommendations to Marketing, Sales, Leadership, Customer Success, and Product teams.

**Everything passes through human review. Nothing auto-publishes.**

---

## Core Philosophy

```
DETECT   →   DECIDE   →   DO
   ↓              ↓           ↓
Monitor       Recommend    Enable
50+ sources   for 5 teams  execution
```

---

## The 20 Deliverables — All Complete ✅

### Architecture & Design

| # | Deliverable | File | Lines |
|---|-------------|------|-------|
| 1 | Full System Architecture | `docs/01-system-architecture.md` | 366 |
| 2 | Complete Folder Structure | `docs/02-folder-structure.md` | 543 |
| 5 | Agent Architecture | `architecture/agent-architecture.md` | 936 |
| 6 | Workflow Architecture | `architecture/workflow-architecture.md` | 893 |
| 7 | Mermaid Diagrams (8 diagrams) | `architecture/mermaid-diagrams.md` | 684 |

### Data & API

| # | Deliverable | File | Lines |
|---|-------------|------|-------|
| 3 | Database Schema (22 tables) | `database/schema.sql` | 687 |
| 4 | API Design (OpenAPI 3.1, 40+ endpoints) | `api/openapi.yaml` | 2,632 |

### UI & Design

| # | Deliverable | File | Lines |
|---|-------------|------|-------|
| 8 | UI/UX Wireframes (13 pages) | `docs/08-ui-wireframes.md` | 483 |
| 9 | Dashboard Designs (10 dashboards) | `docs/09-dashboard-designs.md` | 527 |

### AI & Automation

| # | Deliverable | File | Lines |
|---|-------------|------|-------|
| 10 | Prompt Library (15 production prompts) | `prompts/system-prompts.md` | 1,346 |
| 11 | n8n Workflows Documentation | `docs/11-n8n-workflows.md` | 674 |
| 12 | LangGraph Workflows | `docs/12-langgraph-workflows.md` | 587 |

### Operations & Infrastructure

| # | Deliverable | File | Lines |
|---|-------------|------|-------|
| 13 | Deployment Guide | `docs/13-deployment-guide.md` | 700 |
| 14 | Security Guide | `docs/14-security-guide.md` | 454 |
| 15 | Monitoring Guide | `docs/15-monitoring-guide.md` | 495 |
| 16 | Cost Estimates | `docs/16-cost-estimates.md` | 253 |
| 17 | Production Rollout Plan (5 phases, 10 weeks) | `docs/17-production-rollout-plan.md` | 251 |
| 18 | Scaling Strategy | `docs/18-scaling-strategy.md` | 346 |
| 19 | Testing Strategy | `docs/19-testing-strategy.md` | 661 |
| 20 | Operational Documentation | `docs/20-operational-documentation.md` | 445 |

**Total: ~11,286 lines across 20 deliverables + 147 implementation files**

---

## Implementation Files

### Backend (FastAPI) — `backend/`
- 15 API routers covering all platform capabilities
- Hybrid search with pgvector + PostgreSQL full-text + RRF fusion
- Clerk JWT auth, Pydantic v2 schemas, SQLAlchemy async ORM
- Alert service (Slack + SendGrid + Teams), Vector embedding service

### AI Agents (LangGraph) — `agents/`
- 13 agent nodes across 4 pipeline graphs
- Human-in-the-loop via LangGraph `interrupt()` on executive briefings
- Langfuse observability (per-request, never global singleton)
- AsyncPostgresSaver for fault-tolerant checkpointing

### Frontend (Next.js 14) — `frontend/`
- 16 pages across 13 dashboard sections
- Dark theme design system (TADA brand colors + shadcn/ui)
- SWR data fetching, React Flow for knowledge graph, Recharts for analytics

### Workflows (n8n) — `workflows/n8n/`
- 10 importable workflow JSON files
- Covers: content collection, social monitoring, signal detection, competitor intel,
  executive briefings, alerts, content calendar, source health, pain points, ROI metrics

### Database — `database/`
- 22 PostgreSQL tables, 64 indexes, 3 HNSW vector indexes
- SHA-256 deduplication, generated composite score column
- Reversible migration + seed data

---

## Quick Start

```bash
# 1. Start local stack
docker compose -f deploy/docker-compose.yml up -d

# 2. Run migrations
psql $DATABASE_URL -f database/migrations/001_initial.sql
psql $DATABASE_URL -f database/seed.sql

# 3. Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# 4. Frontend
cd frontend && npm install && npm run dev

# 5. Import n8n workflows
# n8n UI → Settings → Import from File → select each JSON in workflows/n8n/
```

Full guide: `docs/13-deployment-guide.md`

---

## Technology Stack

| Layer | Technology | Hosting |
|-------|-----------|---------|
| Frontend | Next.js 14 App Router | Vercel |
| Backend | FastAPI Python 3.11 | Railway |
| Workflows | n8n self-hosted (queue mode) | Railway |
| AI Agents | LangGraph 0.2+ | Railway |
| Database | PostgreSQL + pgvector | Railway |
| Storage | Supabase | Supabase |
| Auth | Clerk | Clerk Cloud |
| LLM | GPT-4o + GPT-4o-mini | OpenAI API |
| Embeddings | text-embedding-3-small | OpenAI API |
| Observability | Langfuse + OpenTelemetry | Langfuse Cloud |
| Monitoring | Grafana + Prometheus | Railway |

---

## Cost at Launch

| Category | Monthly |
|----------|---------|
| Infrastructure (Vercel + Railway + Supabase + Clerk) | $120–170 |
| OpenAI LLM (500 articles/day) | ~$162 |
| Langfuse + misc | ~$3–52 |
| **Total** | **~$285–384/month** |

---

## ⚠️ Critical Notes Before Going Live

1. **TADA Perspective Prompts** need a 2-week calibration sprint with TADA SMEs — templates in `prompts/system-prompts.md` are starting points only
2. **OpenAI spend limit** — set $300/month hard cap in billing before activating workflows
3. **pgvector HNSW migration** — run at 400k+ embeddings (script in `database/README.md`)
4. **n8n version pinning** — pin to specific version in Railway to avoid breaking changes

---

## Version History

See `CHANGELOG.md` — v1.0.0 released 2026-06-16

## What Is Included

- Full architecture and workflow documentation
- PostgreSQL/Supabase database schema with vector-search ready tables
- API architecture and OpenAPI-style endpoint inventory
- Agent architecture for LangGraph/CrewAI-style orchestration
- n8n workflow design
- Prompt library aligned to TADA's "Visibility to Action" narrative
- Review workflow and approval states
- Dashboard design
- Deployment, monitoring, security, cost, and rollout plans
- Runnable local reference pipeline using deterministic sample data

## Quick Start

```bash
cd outputs/tada-content-intelligence-platform
python3 -m tada_ci.pipeline --input examples/sample_articles.json --output work/daily_digest.json
```

The command produces a daily digest JSON artifact with scored signals, TADA perspective, content recommendations, executive briefing, and sales talking points.

If running from the repository root, use:

```bash
PYTHONPATH=outputs/tada-content-intelligence-platform/src \
python3 -m tada_ci.pipeline \
  --input outputs/tada-content-intelligence-platform/examples/sample_articles.json \
  --output outputs/tada-content-intelligence-platform/work/daily_digest.json
```

## Run The Local App

```bash
cd outputs/tada-content-intelligence-platform
PYTHONPATH=src python3 -m tada_ci.api.server --root .
```

Open:

```text
http://127.0.0.1:8787
```

Available local API endpoints:

- `GET /api/health`
- `GET /api/sources`
- `GET /api/digest`
- `GET /api/signals`
- `GET /api/reports/weekly`
- `GET /api/review-events`
- `POST /api/ingestion/run`
- `POST /api/review-events`

## Folder Structure

```text
tada-content-intelligence-platform/
  README.md
  docs/
    architecture.md
    api-architecture.md
    agent-architecture.md
    workflow-diagrams.md
    n8n-workflow-design.md
    langgraph-crewai-architecture.md
    dashboard-design.md
    deployment-monitoring-security.md
    cost-rollout-plan.md
  sql/
    schema.sql
  prompts/
    prompt-library.md
  n8n/
    daily-intelligence-workflow.json
  dashboard/
    index.html
    styles.css
    app.js
  config/
    sources.json
  deploy/
    Dockerfile
    docker-compose.yml
    supabase-seed.sql
  runbooks/
    operations-runbook.md
  src/tada_ci/
    api/
      server.py
    services/
    pipeline.py
    models.py
    scoring.py
    tada_perspective.py
    content_strategy.py
  examples/
    sample_articles.json
  tests/
    test_pipeline.py
```

## Core Operating Principle

Every output maps market developments to:

1. Detect
2. Decide
3. Do

The platform should help TADA teams identify what changed, why it matters, what decision is required, and what action should follow.

## Deployment Options

- Local prototype: run the included Python server.
- Containerized prototype: use `deploy/docker-compose.yml`.
- Production: deploy API, workers, dashboard, Supabase/PostgreSQL, queue, n8n, monitoring, and secrets manager following `docs/deployment-monitoring-security.md`.

# TADA Intelligence Platform — Architect Report

**Report:** 01-architect-report.md
**Version:** 1.0.0
**Date:** 2026-06-16
**Author:** @architect (CC_GodMode)
**Status:** Complete — Ready for Engineering Review

---

## Executive Summary

This report summarizes the complete system architecture for the TADA Content Intelligence Platform. The architecture spans 5 documents, 21 modules, 13 AI agents, 10 n8n workflows, and 8 infrastructure diagrams. The design is production-ready for an initial team of 5–20 concurrent users and is engineered to scale to 100+ users and 10M+ knowledge items without architectural changes.

---

## Documents Produced

| File | Purpose | Status |
|------|---------|--------|
| `/docs/01-system-architecture.md` | High-level architecture, module interactions, data flow, integrations, scaling | Complete |
| `/docs/02-folder-structure.md` | Full monorepo directory tree with every file explained | Complete |
| `/architecture/mermaid-diagrams.md` | 8 Mermaid diagrams (C4, component, sequence, agents, ERD, API, workflows, infra) | Complete |
| `/architecture/agent-architecture.md` | 13 AI agents with LangGraph definitions, tools, I/O contracts | Complete |
| `/architecture/workflow-architecture.md` | 10 n8n workflows with steps, triggers, error handling | Complete |

---

## Architecture Decisions & Rationale

### Decision 1: FastAPI + LangGraph (not LangChain agents) for AI

**Why LangGraph over vanilla LangChain:** The intelligence pipeline requires stateful, multi-step agent graphs with checkpointing, human-in-the-loop interruption, and reliable retry semantics. LangGraph provides all of this; vanilla LangChain agents do not reliably support partial execution recovery.

**Why FastAPI over Django/Node:** The AI workloads are heavily I/O-bound (LLM API calls, database queries, web fetching). FastAPI's async-first design (asyncio throughout) allows high concurrency without thread-per-request overhead.

### Decision 2: n8n for Workflow Orchestration (not Airflow/Celery)

**Why n8n:** TADA's team needs operational visibility into the data pipeline without reading Python. n8n provides a visual execution history, easy debugging, built-in connectors for Slack/Teams/email, and zero per-execution cost. Airflow is too heavy for this scale; pure Celery lacks the visual orchestration layer.

**Tradeoff accepted:** n8n workflows in JSON are less version-controllable than Python DAGs. Mitigated by storing all workflow JSON in `infrastructure/n8n/workflows/` and treating them as code artifacts.

### Decision 3: pgvector over Pinecone/Weaviate

**Why pgvector:** Keeps vector search co-located with relational data, eliminates a separate service to operate, and supports hybrid queries (semantic similarity + SQL filters) in a single query. At TADA's initial scale (< 1M embeddings), pgvector with IVFFlat indexes performs well. Migration path to HNSW index or dedicated vector DB documented for future scale.

### Decision 4: Monorepo (Turborepo + pnpm + uv)

**Why monorepo:** The TypeScript frontend and Python backend share type contracts. A monorepo allows atomic commits across Next.js + FastAPI + agents when a shared schema changes, single CI pipeline, and consistent tooling.

### Decision 5: Human Review is Mandatory, Never Bypassed

**Why non-negotiable:** TADA is an institutional intelligence platform. Auto-publishing insights that contain inaccuracies — even rare ones — erodes executive trust. The review system is not an optional workflow; it is a core architectural constraint that all module outputs route through.

---

## Module Completion Status

| # | Module | Architecture Complete | Implementation Ready |
|---|--------|----------------------|---------------------|
| 01 | Data Collection Engine | Yes | Yes |
| 02 | Source Quality Engine | Yes | Yes |
| 03 | Content Extraction Engine | Yes | Yes |
| 04 | Signal Detection Engine | Yes | Yes |
| 05 | Multi-Source Validation Engine | Yes | Yes |
| 06 | Trend Engine | Yes | Yes |
| 07 | Customer Pain Point Detection | Yes | Yes |
| 08 | Relevance Scoring Engine | Yes | Yes |
| 09 | TADA Perspective Engine | Yes | Yes |
| 10 | Strategic Recommendation Engine | Yes | Yes |
| 11 | Content Strategy Engine | Yes | Yes |
| 12 | Content Calendar Engine | Yes | Yes |
| 13 | Knowledge Repository | Yes | Yes |
| 14 | Market Intelligence Explorer | Yes | Yes |
| 15 | Advanced Search | Yes | Yes |
| 16 | Knowledge Graph | Yes | Yes |
| 17 | Trend Timeline | Yes | Yes |
| 18 | Executive Portal | Yes | Yes |
| 19 | Alerting System | Yes | Yes |
| 20 | Human Review System | Yes | Yes |
| 21 | AI Agent Architecture | Yes | Yes |

---

## AI Agent Summary

| # | Agent | Primary Purpose | LLM |
|---|-------|----------------|-----|
| 1 | Collection Agent | Ingest 50+ sources | n/a (tools-only) |
| 2 | Research Agent | Deep-dive on demand | gpt-4o |
| 3 | Signal Detection Agent | Detect market signals | gpt-4o-mini |
| 4 | Trend Agent | Track frequency/momentum | gpt-4o-mini |
| 5 | Competitive Intel Agent | Monitor competitors | gpt-4o-mini |
| 6 | Pain Point Agent | Mine community sentiment | gpt-4o-mini |
| 7 | TADA Perspective Agent | Generate six-part frame | gpt-4o (critical) |
| 8 | Content Strategy Agent | Map insights to formats | gpt-4o-mini |
| 9 | Sales Intelligence Agent | Sales talking points | gpt-4o |
| 10 | Executive Briefing Agent | Compile briefings | gpt-4o (critical) |
| 11 | QA Agent | Quality assurance | gpt-4o-mini |
| 12 | Repository Agent | Knowledge store ops | n/a (tools-only) |
| 13 | Recommendation Agent | Per-persona recs | gpt-4o |

---

## n8n Workflow Summary

| # | Workflow | Trigger | Frequency |
|---|---------|---------|-----------|
| 1 | Daily Collection | Cron | Every 15 min |
| 2 | Signal Detection | Webhook + Cron | On-demand + hourly |
| 3 | Trend Analysis | Webhook + Cron | On-demand + hourly |
| 4 | Competitive Intelligence | Cron | Every 4 hours |
| 5 | Pain Point Detection | Cron | Every 2 hours |
| 6 | Executive Briefing | Cron | Daily 7AM + Mon 7AM |
| 7 | Content Calendar | Webhook + Cron | On-demand + Mon 8AM |
| 8 | Alert Trigger | Webhook | Real-time |
| 9 | Human Review Notification | Webhook | On-demand |
| 10 | Repository Sync | Webhook + Cron | On-demand + 2AM nightly |

---

## Database Schema Summary

Core tables: 17 tables

| Table | Purpose |
|-------|---------|
| `source` | 50+ configured intelligence sources |
| `source_quality_score` | Historical quality scores per source |
| `raw_content` | Deduped raw ingested content |
| `content_item` | Extracted, embedded structured content |
| `signal` | Detected market signals |
| `trend` | Tracked trends with metrics |
| `trend_data_point` | Time-series trend data |
| `insight` | Full TADA-framed insights (all statuses) |
| `recommendation` | Per-persona strategic recommendations |
| `review_record` | Human review audit trail |
| `knowledge_item` | Permanent published knowledge (never deleted) |
| `entity` | Named entities for knowledge graph |
| `entity_relationship` | Relationships between entities |
| `calendar_entry` | Scheduled content items |
| `alert` | Alert dispatch records |
| `competitor` | Monitored competitor profiles |
| `competitor_activity` | Observed competitor activities |

---

## Estimated Implementation Timeline

**Phase 1 — Foundation (Weeks 1–3)**
- Monorepo setup, CI/CD, Railway + Vercel deployment
- PostgreSQL + pgvector schema (migrations 0001–0003)
- FastAPI app with auth (Clerk), basic CRUD routes
- n8n setup on Railway, workflow 1 (Collection) running

**Phase 2 — Core Pipeline (Weeks 4–6)**
- Collection Agent, Signal Detection Agent
- Source Quality Engine, Content Extraction Engine
- Workflows 2 (Signal) + 3 (Trend)
- Basic Next.js UI: source management, signal feed

**Phase 3 — Intelligence Layer (Weeks 7–9)**
- TADA Perspective Agent (most complex — requires prompt engineering)
- Recommendation Agent, QA Agent
- Human Review System (backend + UI)
- Workflows 9 (Review Notification) + 10 (Repository Sync)

**Phase 4 — Knowledge Infrastructure (Weeks 10–12)**
- Knowledge Repository UI (Module 14)
- Advanced Search — keyword + semantic + hybrid (Module 15)
- Knowledge Graph visualization (Module 16)
- Trend Timeline visualization (Module 17)

**Phase 5 — Decision Support (Weeks 13–15)**
- Executive Portal (Module 18)
- Alerting System — Slack/Teams/email (Module 19)
- Content Calendar UI (Module 12)
- Competitive Intelligence Agent + Workflow 4

**Phase 6 — Completion + Launch (Weeks 16–18)**
- Pain Point Agent + Workflow 5
- Executive Briefing Agent + Workflow 6
- Content Strategy Agent + Workflow 7
- Sales Intelligence Agent
- Full E2E testing, performance testing, security audit

---

## Critical Risk Flags

### Risk 1: TADA Perspective Agent Prompt Quality
The `TADA Perspective Agent` is the highest-leverage component. The quality of its output depends entirely on how well TADA's methodology, voice, and D-D-D framework are encoded in the system prompt. **Recommendation:** Dedicate at minimum 2 weeks to prompt engineering with TADA subject matter experts before building downstream consumers. Build an evaluation framework (Langfuse + test dataset of 50 gold-standard insights) before this agent goes to production.

### Risk 2: pgvector Scaling at 500k+ Embeddings
IVFFlat indexes require full table reindexing when nlist parameters need adjustment. Plan the migration to HNSW index (no rebuild needed) before hitting 500k records. Set a monitoring alert at 400k records.

### Risk 3: Source Quality Calibration
The Source Quality Engine scoring rubric (trust, authority, influence, accuracy) needs initial calibration against TADA's team judgment of source quality. Without calibration, the quality gate (score >= 40) may admit low-quality sources or block legitimate ones. **Recommendation:** Build a source quality review UI in Phase 1 and do a 2-week manual calibration sprint with 50+ initial sources before relying on automated scoring.

### Risk 4: n8n Upgrade Compatibility
n8n has frequent breaking changes between versions. Pin the n8n Docker image to a specific version tag (not `latest`). Schedule quarterly upgrade reviews. Test all 10 workflow JSONs after every n8n upgrade.

### Risk 5: LLM Cost at Scale
At full pipeline operation (50+ sources, 15-minute polling), daily LLM costs could range from $50–$200/day depending on content volume. The architecture uses gpt-4o-mini for commodity tasks (extraction, classification) and gpt-4o only for high-value tasks (perspective, recommendations, briefings). Monitor costs via Langfuse token dashboards from day 1. Set hard daily spend limits in OpenAI dashboard.

---

## Next Steps for Engineering Team

1. **Set up monorepo** per `/docs/02-folder-structure.md` — use `turbo`, `pnpm`, `uv`
2. **Provision infrastructure** — Railway project (API + agents + n8n + PostgreSQL + Redis), Vercel project (Next.js)
3. **Run database migrations** — `0001_initial_schema` through `0003_add_knowledge_graph`
4. **Seed 50+ sources** — Use `infrastructure/scripts/seed-sources.py`
5. **Begin Workflow 1** — Collection pipeline end-to-end as the first working feature
6. **Schedule TADA perspective prompt workshop** — Before Week 7 (Phase 3)

---

## Architecture Contacts

| Role | Responsibility |
|------|---------------|
| Lead Backend Engineer | FastAPI, LangGraph agents, database |
| Lead Frontend Engineer | Next.js, UI components, data visualization |
| DevOps Engineer | Railway, Vercel, n8n, Terraform, monitoring |
| AI/ML Engineer | Prompt engineering, agent tuning, Langfuse |
| Product Manager | Module prioritization, source registry, review workflow |

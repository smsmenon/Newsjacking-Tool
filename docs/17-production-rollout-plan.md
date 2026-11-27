# TADA Intelligence Platform — Production Rollout Plan

## Overview

The rollout follows five two-week phases over 10 weeks. Each phase builds on the previous and has clear success metrics and a defined rollback plan. Teams should not advance to the next phase until all success criteria for the current phase are met.

**Timeline:** 10 weeks from kickoff to full production
**Owner:** Platform Engineering Lead
**Stakeholders:** Marketing, Sales, Leadership, Customer Success

---

## Phase 1 — Foundation (Weeks 1–2)

### Goals

Establish a working, secure infrastructure with reliable data collection from the 10 highest-priority sources.

### Deliverables

- [ ] PostgreSQL deployed on Railway with pgvector enabled and all migrations run
- [ ] FastAPI backend deployed and healthy (all dependency checks passing)
- [ ] Clerk authentication configured; admin user can log in
- [ ] Supabase storage buckets created
- [ ] n8n deployed with database persistence
- [ ] Redis deployed for caching
- [ ] 10 core sources configured and collecting articles
- [ ] Daily collection workflow running on schedule
- [ ] Basic monitoring in place (health endpoint, Railway metrics)

### Core Sources (Phase 1)

Select 10 from the source catalog that cover:
1. Industry flagship publication #1
2. Industry flagship publication #2
3. Competitor #1 press/news
4. Competitor #2 press/news
5. Competitor #3 press/news
6. Key analyst firm blog
7. Regulatory body RSS
8. LinkedIn Company Page (TADA)
9. Key technology vendor blog
10. General business news filter

### Success Metrics

| Metric | Target |
|---|---|
| API uptime | 99%+ over week 2 |
| Articles collected per day | 50+ |
| Collection success rate | 90%+ across 10 sources |
| Auth: admin can log in | Yes |
| Failed collections | < 2 sources per day |

### Rollback Plan

- All infrastructure can be torn down without data loss (data is not customer-facing yet)
- If Railway services are unstable, move backend to an alternative provider (Fly.io, Render)
- If Clerk has issues, fall back to API key auth temporarily

---

## Phase 2 — Intelligence (Weeks 3–4)

### Goals

LangGraph agents are deployed and producing signals. The TADA Perspective Engine generates insights. Executive Portal is available in read-only mode.

### Deliverables

- [ ] LangGraph agent service deployed on Railway
- [ ] Signal Detection Agent running on collected articles
- [ ] Signal scoring and tier assignment working (A/B/C tiers)
- [ ] TADA Perspective Engine generating insights
- [ ] Executive Portal frontend deployed on Vercel
- [ ] Executives can log in and view signals
- [ ] Langfuse tracing all agent runs
- [ ] Grafana dashboards showing agent performance

### Success Metrics

| Metric | Target |
|---|---|
| Signals detected per day | 5–20 |
| Agent success rate | 90%+ |
| Agent p95 latency | < 60s |
| Executive Portal loads | Yes, < 3s |
| Langfuse traces visible | Yes |
| LLM cost per day | < $10 |

### Rollback Plan

- If LangGraph agents are unstable: disable agent processing, continue collecting articles (articles accumulate for batch processing later)
- If Executive Portal frontend has issues: provide read-only API access while debugging
- Agent processing is async and non-blocking — failures don't break data collection

---

## Phase 3 — Content & Review (Weeks 5–6)

### Goals

Content Strategy Engine is producing content ideas. Human Review System is operational. Slack integration sends alerts.

### Deliverables

- [ ] Content Strategy Engine generating ideas from signals
- [ ] Human Review Queue populated with pending ideas
- [ ] Review workflow: analyst can approve/reject content ideas
- [ ] Content Calendar view in frontend
- [ ] Slack integration: signal alerts and weekly digest
- [ ] Review audit log functioning
- [ ] Reviewer and analyst roles configured for all team members
- [ ] Email notifications for review queue items

### Success Metrics

| Metric | Target |
|---|---|
| Content ideas generated per week | 10+ |
| Review queue items created | Yes |
| Review workflow: approve flow works | Yes |
| Slack alerts delivered | Yes |
| Content Calendar shows approved ideas | Yes |
| All team members can log in with correct roles | Yes |

### Rollback Plan

- Content idea generation is additive — disabling it doesn't affect existing signals or data
- If Slack integration fails, fall back to email notifications
- Review system can operate without Slack notifications

---

## Phase 4 — Advanced Features (Weeks 7–8)

### Goals

Knowledge Graph, advanced search (hybrid/semantic), Trend Timeline, and the full source set (50+ sources) are live.

### Deliverables

- [ ] Knowledge Graph populated and query API functional
- [ ] Semantic search operational (pgvector similarity search)
- [ ] Hybrid search (keyword + semantic) working in frontend
- [ ] Trend Timeline dashboard showing signal momentum over time
- [ ] 40 additional sources connected (total 50+)
- [ ] ROI Dashboard with initial metrics
- [ ] All n8n workflows active
- [ ] Competitive intelligence dashboard functional

### Success Metrics

| Metric | Target |
|---|---|
| Active sources | 50+ |
| Semantic search returns results | Yes, < 2s |
| Knowledge Graph entities | 100+ nodes |
| Articles collected per day | 400+ |
| Signals detected per day | 20–50 |
| Trend Timeline shows 30 days of data | Yes |
| ROI Dashboard loads | Yes |

### Rollback Plan

- Each advanced feature is independently deployable — roll back individual features without affecting the core
- Knowledge Graph is read-only (additive) — safe to disable
- If source collection errors increase at 50+ sources, reduce to 30 most reliable sources

---

## Phase 5 — Optimization (Weeks 9–10)

### Goals

Platform is tuned for performance and cost, all team members trained, and documentation is complete.

### Deliverables

- [ ] Performance profiling completed; p95 API response < 500ms
- [ ] LLM cost optimization implemented (two-stage model routing)
- [ ] Embedding cache reducing repeat embedding costs
- [ ] Redis caching for high-traffic API endpoints
- [ ] Source quality review: remove low-signal sources, add high-signal ones
- [ ] User training sessions completed for all teams
- [ ] Operational runbooks written and tested
- [ ] Final documentation reviewed and published
- [ ] Security audit completed
- [ ] Load testing completed

### Success Metrics

| Metric | Target |
|---|---|
| API p95 response time | < 500ms |
| Monthly LLM cost vs. Phase 2 baseline | < 80% (20%+ savings) |
| User training completion | 100% of target users |
| Security audit: critical findings | 0 |
| Uptime over Phase 5 | 99.5%+ |
| All runbooks documented and reviewed | Yes |

### Rollback Plan

- Optimization phase: all changes are backward-compatible
- If performance tuning causes issues, revert to previous configuration
- No new features in this phase — rollback surface is minimal

---

## Cross-Phase Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Railway service instability | Medium | High | Multi-provider backup plan (Fly.io) |
| OpenAI API rate limits | Low | Medium | Request limit increase in advance |
| pgvector performance degradation | Low | Medium | Index tuning plan ready |
| n8n workflow failures | Medium | Low | Monitoring alerts + runbooks |
| Source blocking scrapers | Medium | Medium | Respect robots.txt, add delays, user-agent |
| Clerk auth outage | Low | High | Session caching, graceful degradation |
| LLM cost spike | Low | Medium | Budget alerts + hard limits set |
| Team adoption resistance | Medium | High | Early stakeholder involvement, training |

---

## Communication Plan

| Week | Communication |
|---|---|
| Week 1 | Kickoff email to all stakeholders; infrastructure live confirmation |
| Week 2 | Phase 1 completion report; Phase 2 plan shared |
| Week 4 | First signal and insights demo to leadership |
| Week 6 | Review system demo to marketing and content teams |
| Week 8 | Full platform demo to all stakeholders |
| Week 10 | Launch announcement; training complete; go-live declaration |

---

## Go-Live Criteria (End of Phase 5)

The platform is considered production-ready when:

```
[ ] All 5 phases completed with success metrics met
[ ] Zero critical security findings from audit
[ ] All team members trained and onboarded
[ ] Monitoring alerts configured and tested
[ ] Runbooks documented for all known failure modes
[ ] Cost within projected range ($200-350/month)
[ ] 99.5%+ uptime demonstrated over 2 consecutive weeks
[ ] Executive sign-off received
```

# Deliverable Index

This package satisfies the requested final deliverables as follows:

1. Full System Architecture: `docs/architecture.md`
2. Database Schema: `sql/schema.sql`
3. API Architecture: `docs/api-architecture.md`
4. Agent Architecture: `docs/agent-architecture.md`
5. Workflow Diagrams: `docs/workflow-diagrams.md`
6. n8n Workflow Design: `docs/n8n-workflow-design.md` and `n8n/daily-intelligence-workflow.json`
7. LangGraph/CrewAI Architecture: `docs/langgraph-crewai-architecture.md`
8. Prompt Library: `prompts/prompt-library.md`
9. Data Models: `docs/data-models.md` and `src/tada_ci/models.py`
10. Review Workflow: `docs/review-workflow.md`
11. Dashboard Design: `docs/dashboard-design.md`
12. Deployment Plan: `docs/deployment-monitoring-security.md`
13. Monitoring Plan: `docs/deployment-monitoring-security.md`
14. Security Plan: `docs/deployment-monitoring-security.md`
15. Cost Estimation: `docs/cost-rollout-plan.md`
16. Production Rollout Strategy: `docs/cost-rollout-plan.md`

Reference implementation:

- Pipeline entrypoint: `src/tada_ci/pipeline.py`
- Local API server: `src/tada_ci/api/server.py`
- Scoring engine: `src/tada_ci/scoring.py`
- TADA perspective engine: `src/tada_ci/tada_perspective.py`
- Content strategy engine: `src/tada_ci/content_strategy.py`
- Dashboard: `dashboard/index.html`
- Source configuration: `config/sources.json`
- Deployment files: `deploy/Dockerfile`, `deploy/docker-compose.yml`, `deploy/supabase-seed.sql`
- Operations runbook: `runbooks/operations-runbook.md`
- Sample input: `examples/sample_articles.json`
- Sample generated digest: `work/daily_digest.json`

Verification performed:

- Ran the sample daily intelligence pipeline.
- Verified the surfaced signals meet the score gate.
- Verified all generated opportunities remain in `draft` review state.

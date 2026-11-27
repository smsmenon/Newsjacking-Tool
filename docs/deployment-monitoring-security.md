# Deployment, Monitoring, And Security Plan

## Deployment Architecture

Recommended stack:

- Frontend: Next.js or Retool for internal dashboard
- API: FastAPI or Node.js service
- Database: Supabase PostgreSQL with pgvector
- Queue: Celery + Redis, Cloud Tasks, or Temporal
- Object storage: S3-compatible bucket
- Workflow automation: n8n
- LLM provider: approved enterprise AI provider with audit controls
- Observability: OpenTelemetry, Grafana, Sentry

## Environments

- Local development
- Staging
- Production

Deployment gates:

- Schema migration check
- Prompt version check
- Integration tests
- Security scan
- Source connector smoke test

## Monitoring Plan

Application metrics:

- Articles ingested by source
- Processing success rate
- Average processing latency
- Signals surfaced
- Average score by category
- QA failure rate
- Review backlog size

Source health:

- Last success timestamp
- Failure count
- HTTP status
- Parse success rate
- Duplicate rate

Cost metrics:

- Tokens by pipeline stage
- Cost by source category
- Cost per surfaced signal
- Cost per approved content opportunity

Alerts:

- Source failure for more than 24 hours
- Processing error rate above 5%
- Review backlog older than 72 hours
- Daily digest not generated
- Unexpected cost spike

## Security Plan

Access controls:

- Single sign-on
- Role-based authorization
- Least-privilege service accounts
- Separate admin and reviewer roles

Data security:

- Encrypt database at rest
- TLS in transit
- Store secrets in vault
- Do not persist unnecessary credentials in n8n workflow JSON

AI governance:

- Prompt versioning
- Model version logging
- Source evidence retention
- Human approval before publication
- Hallucination QA checks

Compliance posture:

- Audit trail for review events
- Source attribution retention
- Data retention policy
- Export logs for internal review


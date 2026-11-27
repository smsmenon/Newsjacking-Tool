# TADA Intelligence Platform — Deployment Guide

## Overview

This guide walks through the complete deployment of the TADA Intelligence Platform from zero to a fully operational production system. Follow phases in order; each phase has validation steps before proceeding.

---

## Prerequisites

### Required Accounts

| Service | Purpose | URL |
|---|---|---|
| Vercel | Frontend hosting (Next.js) | https://vercel.com |
| Railway | Backend + n8n + PostgreSQL hosting | https://railway.app |
| Supabase | File storage + supplementary auth | https://supabase.com |
| Clerk | Primary authentication | https://clerk.com |
| OpenAI | LLM inference (GPT-4o, embeddings) | https://platform.openai.com |
| Langfuse | LLM observability | https://langfuse.com |
| GitHub | Source control + CI/CD | https://github.com |

### Required API Keys Checklist

Before starting deployment, collect all of the following:

```
[ ] OPENAI_API_KEY             — OpenAI platform key
[ ] CLERK_SECRET_KEY           — Clerk backend secret
[ ] CLERK_PUBLISHABLE_KEY      — Clerk frontend publishable key
[ ] SUPABASE_URL               — Supabase project URL
[ ] SUPABASE_SERVICE_ROLE_KEY  — Supabase service role key (backend only)
[ ] SUPABASE_ANON_KEY          — Supabase anon key (frontend)
[ ] LANGFUSE_SECRET_KEY        — Langfuse secret key
[ ] LANGFUSE_PUBLIC_KEY        — Langfuse public key
[ ] LANGFUSE_HOST              — Langfuse host URL
[ ] N8N_WEBHOOK_SECRET         — Self-generated random secret for webhook auth
[ ] DATABASE_URL               — PostgreSQL connection string (Railway)
[ ] REDIS_URL                  — Redis connection string (Railway)
```

### Local Development Requirements

```bash
# Required tools
node >= 18.17.0
python >= 3.11
docker >= 24.0
docker-compose >= 2.20
poetry >= 1.7
```

---

## Step 1 — Database Setup (PostgreSQL on Railway)

### 1.1 Create Railway Project

1. Log in to Railway and create a new project: **TADA Intelligence Platform**
2. Add a **PostgreSQL** plugin from the Railway marketplace
3. Copy the `DATABASE_URL` from the plugin's connection tab

### 1.2 Enable pgvector Extension

Connect to the database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### 1.3 Run Migrations

```bash
# From the backend directory
export DATABASE_URL="postgresql://..."

poetry run alembic upgrade head
```

Verify all tables created:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected tables: `articles`, `sources`, `signals`, `insights`, `content_ideas`, `reviews`, `users`, `audit_logs`, `embeddings`.

### 1.4 Seed Reference Data

```bash
poetry run python scripts/seed_sources.py
poetry run python scripts/seed_categories.py
```

---

## Step 2 — Supabase Setup

### 2.1 Create Supabase Project

1. Create a new project named **tada-intelligence**
2. Choose the nearest region to your Railway deployment
3. Note the Project URL and service role key

### 2.2 Create Storage Buckets

In Supabase Storage, create the following buckets:

| Bucket | Access | Purpose |
|---|---|---|
| `articles-raw` | Private | Raw scraped article HTML |
| `exports` | Private | User-generated exports |
| `briefings` | Private | Generated PDF briefings |
| `attachments` | Private | Review system attachments |

### 2.3 Set Storage Policies

For the `exports` bucket, allow authenticated users to read their own files:

```sql
CREATE POLICY "Users can read own exports"
ON storage.objects FOR SELECT
USING (auth.uid()::text = (storage.foldername(name))[1]);
```

### 2.4 Configure Auth (if using Supabase Auth as secondary)

Skip if using Clerk exclusively. If using Supabase for service-to-service auth, enable the service role key in your backend environment only.

---

## Step 3 — Backend Deployment (FastAPI on Railway)

### 3.1 Create Railway Service

1. In your Railway project, add a **New Service → GitHub Repo**
2. Connect to `tada-intelligence/backend`
3. Set the start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3.2 Backend Environment Variables

Set the following in Railway service settings:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/tada

# Redis
REDIS_URL=redis://default:pass@host:6379

# OpenAI
OPENAI_API_KEY=sk-...

# Clerk
CLERK_SECRET_KEY=sk_live_...
CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Langfuse
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# n8n
N8N_WEBHOOK_SECRET=your-random-32-char-secret
N8N_BASE_URL=https://n8n.railway.internal

# App
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-frontend.vercel.app
```

### 3.3 Add Redis Service

In Railway, add a **Redis** plugin. Copy the `REDIS_URL` to the backend service environment.

### 3.4 Validate Backend

```bash
curl https://your-backend.railway.app/health
# Expected: {"status": "healthy", "database": "ok", "redis": "ok"}
```

---

## Step 4 — n8n Deployment (Self-Hosted on Railway)

### 4.1 Create n8n Service

1. Add a new Railway service from Docker image: `n8nio/n8n:latest`
2. Set the port to `5678`
3. Add a persistent volume at `/home/node/.n8n`

### 4.2 n8n Environment Variables

```env
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your-strong-password
WEBHOOK_URL=https://n8n.your-domain.railway.app
N8N_ENCRYPTION_KEY=your-32-char-encryption-key
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres.railway.internal
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=postgres
DB_POSTGRESDB_PASSWORD=your-db-password
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=720
```

### 4.3 Configure n8n Credentials

In n8n UI (https://n8n.your-domain), add credentials:

1. **OpenAI** — API key from OpenAI platform
2. **PostgreSQL** — Railway database connection details
3. **HTTP Header Auth** — Name: `X-Webhook-Secret`, Value: your `N8N_WEBHOOK_SECRET`
4. **Supabase** — Project URL and service role key

### 4.4 Import Workflows

```bash
# Use n8n CLI or UI import
n8n import:workflow --input=./n8n/workflows/01-content-collection.json
n8n import:workflow --input=./n8n/workflows/02-signal-processing.json
n8n import:workflow --input=./n8n/workflows/03-agent-orchestration.json
n8n import:workflow --input=./n8n/workflows/04-content-distribution.json
```

Or import via n8n UI: Settings → Import from file for each workflow JSON.

---

## Step 5 — Frontend Deployment (Vercel)

### 5.1 Connect Repository

1. In Vercel, create a new project from GitHub
2. Select the `tada-intelligence/frontend` repository
3. Set the framework preset to **Next.js**

### 5.2 Frontend Environment Variables

In Vercel project settings → Environment Variables:

```env
# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/onboarding

# Backend API
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_WS_URL=wss://your-backend.railway.app

# Supabase (public)
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Analytics (optional)
NEXT_PUBLIC_POSTHOG_KEY=phc_...
```

### 5.3 Domain Configuration

1. In Vercel, add your custom domain: `app.tada-intelligence.com`
2. Add DNS records with your registrar (Vercel provides the values)
3. Enable automatic HTTPS (default on Vercel)

### 5.4 Build Configuration

Ensure `next.config.js` includes:

```js
module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ]
  },
}
```

---

## Step 6 — LangGraph Agent Deployment

### 6.1 Agent Service on Railway

Create a dedicated Railway service for the LangGraph agents:

- Start command: `python -m agents.runner`
- Same environment variables as the backend service
- Set memory: minimum 512MB (agents are memory-intensive)

### 6.2 Agent Configuration

```env
# In addition to standard backend vars:
AGENT_CONCURRENCY=3
AGENT_TIMEOUT_SECONDS=300
LANGGRAPH_CHECKPOINT_DB=postgresql+asyncpg://...
```

### 6.3 Validate Agents

```bash
curl -X POST https://your-backend.railway.app/api/v1/agents/test \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"agent": "signal_detector", "test_mode": true}'
```

---

## Step 7 — Clerk Authentication Setup

### 7.1 Create Clerk Application

1. Log in to Clerk dashboard
2. Create application: **TADA Intelligence Platform**
3. Enable **Email + Password** and **Google OAuth** sign-in methods

### 7.2 Configure JWT Template

In Clerk dashboard → JWT Templates, create a template named `tada-backend`:

```json
{
  "aud": "tada-backend",
  "role": "{{user.public_metadata.role}}",
  "org_id": "{{user.public_metadata.org_id}}"
}
```

### 7.3 Webhook Setup

In Clerk → Webhooks, add endpoint: `https://your-backend.railway.app/api/v1/webhooks/clerk`

Subscribe to events: `user.created`, `user.updated`, `user.deleted`

### 7.4 Set User Roles

Assign initial admin user via Clerk dashboard → Users → Edit public metadata:

```json
{
  "role": "admin",
  "org_id": "tada"
}
```

---

## Step 8 — Langfuse Observability Setup

### 8.1 Create Langfuse Project

1. Sign up at https://cloud.langfuse.com
2. Create project: **TADA Intelligence**
3. Copy public key and secret key to backend environment

### 8.2 Configure Traces

In the backend, Langfuse is initialized in `app/core/observability.py`. Verify the integration is working:

```bash
# Trigger a test agent run, then check Langfuse dashboard
curl -X POST https://your-backend.railway.app/api/v1/agents/signal-detector/run \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"article_id": "test-123"}'
```

Traces should appear in Langfuse within 30 seconds.

### 8.3 Configure Alerts

In Langfuse → Alerts, configure:
- Alert if p95 latency > 30 seconds
- Alert if error rate > 5% in any 15-minute window

---

## Step 9 — Grafana + Prometheus Monitoring Setup

### 9.1 Deploy Prometheus on Railway

Add a new Railway service from Docker image: `prom/prometheus:latest`

Create `prometheus.yml` config:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'tada-backend'
    static_configs:
      - targets: ['backend.railway.internal:8000']
    metrics_path: /metrics

  - job_name: 'n8n'
    static_configs:
      - targets: ['n8n.railway.internal:5678']
    metrics_path: /metrics
```

### 9.2 Deploy Grafana on Railway

Add Grafana from Docker: `grafana/grafana:latest`

Set environment:

```env
GF_SECURITY_ADMIN_PASSWORD=your-grafana-password
GF_SERVER_ROOT_URL=https://grafana.your-domain.com
```

### 9.3 Add Prometheus as Data Source

In Grafana → Data Sources, add Prometheus with URL: `http://prometheus.railway.internal:9090`

### 9.4 Import Dashboards

Import the JSON dashboard files from `./infrastructure/grafana/dashboards/`:
- `platform-health.json`
- `pipeline-health.json`
- `database-performance.json`
- `agent-performance.json`
- `business-metrics.json`

---

## Step 10 — n8n Workflow Activation Sequence

Activate workflows in this order to avoid dependency failures:

```
1. "Source Health Monitor"      → runs every 5 min
2. "Content Collection - RSS"   → runs every 30 min
3. "Content Collection - Web"   → runs every 60 min
4. "Signal Processing Pipeline" → triggered by collection
5. "Agent Orchestration"        → triggered by signal processing
6. "Content Distribution"       → triggered by agent completion
7. "Daily Digest"               → runs at 07:00 UTC
8. "Weekly Briefing"            → runs Monday 06:00 UTC
```

---

## Step 11 — First-Run Validation Checklist

### Infrastructure
```
[ ] PostgreSQL accessible, all tables present
[ ] Redis responding to PING
[ ] pgvector extension enabled
[ ] Supabase storage buckets created
[ ] All Railway services showing "healthy" status
```

### Backend
```
[ ] GET /health returns {"status": "healthy"}
[ ] GET /health/dependencies shows all deps healthy
[ ] Clerk JWT validation working (test with real user token)
[ ] Database read/write working via API
[ ] Redis caching working
```

### n8n
```
[ ] n8n UI accessible
[ ] All credentials configured and tested
[ ] All workflows imported
[ ] Source Health Monitor activated and running
[ ] First content collection triggered manually — articles appearing in DB
```

### Frontend
```
[ ] Frontend loads without console errors
[ ] Sign-in page works with Clerk
[ ] Dashboard loads after authentication
[ ] API calls from frontend succeed (check Network tab)
[ ] WebSocket connection established (if applicable)
```

### Observability
```
[ ] Langfuse receiving traces
[ ] Prometheus scraping metrics
[ ] Grafana dashboards showing data
[ ] Alert rules configured
```

---

## Docker Compose for Local Development

```yaml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: tada_dev
      POSTGRES_USER: tada
      POSTGRES_PASSWORD: tada_dev_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: admin
      N8N_BASIC_AUTH_PASSWORD: admin
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_PORT: 5432
      DB_POSTGRESDB_DATABASE: n8n_dev
      DB_POSTGRESDB_USER: tada
      DB_POSTGRESDB_PASSWORD: tada_dev_password
      WEBHOOK_URL: http://localhost:5678
      N8N_ENCRYPTION_KEY: dev-encryption-key-32-chars-long!
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - postgres

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://tada:tada_dev_password@postgres:5432/tada_dev
      REDIS_URL: redis://redis:6379
      ENVIRONMENT: development
      LOG_LEVEL: DEBUG
      # Add your real API keys in .env.local
    env_file:
      - .env.local
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    env_file:
      - ./frontend/.env.local
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    command: npm run dev

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./infrastructure/prometheus/prometheus.dev.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infrastructure/grafana/dashboards:/var/lib/grafana/dashboards
      - ./infrastructure/grafana/provisioning:/etc/grafana/provisioning

volumes:
  postgres_data:
  redis_data:
  n8n_data:
  grafana_data:
```

### Local Development Quick Start

```bash
# 1. Copy environment template
cp .env.example .env.local

# 2. Edit .env.local with your API keys
# (OpenAI, Clerk, Supabase, Langfuse)

# 3. Start all services
docker-compose up -d

# 4. Run migrations
docker-compose exec backend poetry run alembic upgrade head

# 5. Seed data
docker-compose exec backend poetry run python scripts/seed_sources.py

# 6. Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# n8n: http://localhost:5678
# Grafana: http://localhost:3001
```

---

## Environment Variables Reference

### Backend (FastAPI)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL async connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `CLERK_SECRET_KEY` | Yes | Clerk backend secret |
| `CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key |
| `CLERK_JWKS_URL` | Yes | Clerk JWKS endpoint for JWT validation |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role (backend only) |
| `LANGFUSE_SECRET_KEY` | Yes | Langfuse tracing secret |
| `LANGFUSE_PUBLIC_KEY` | Yes | Langfuse tracing public key |
| `LANGFUSE_HOST` | Yes | Langfuse host URL |
| `N8N_WEBHOOK_SECRET` | Yes | Shared secret for n8n webhook auth |
| `N8N_BASE_URL` | Yes | n8n internal URL for triggering workflows |
| `ENVIRONMENT` | Yes | `development` / `staging` / `production` |
| `LOG_LEVEL` | No | Default: `INFO` |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `AGENT_CONCURRENCY` | No | Default: `3` |
| `RATE_LIMIT_PER_MINUTE` | No | Default: `60` |

### Frontend (Next.js / Vercel)

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key |
| `CLERK_SECRET_KEY` | Yes | Clerk secret (server-side) |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | Yes | Sign-in route |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | Yes | Sign-up route |
| `NEXT_PUBLIC_API_URL` | Yes | Backend API base URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key |

### n8n

| Variable | Required | Description |
|---|---|---|
| `N8N_BASIC_AUTH_ACTIVE` | Yes | Enable basic auth |
| `N8N_BASIC_AUTH_USER` | Yes | n8n admin username |
| `N8N_BASIC_AUTH_PASSWORD` | Yes | n8n admin password |
| `WEBHOOK_URL` | Yes | Public webhook base URL |
| `N8N_ENCRYPTION_KEY` | Yes | 32-char key for credential encryption |
| `DB_TYPE` | Yes | `postgresdb` |
| `DB_POSTGRESDB_*` | Yes | PostgreSQL connection details |
| `EXECUTIONS_DATA_PRUNE` | No | Default: `true` |
| `EXECUTIONS_DATA_MAX_AGE` | No | Hours to retain executions, default: `720` |

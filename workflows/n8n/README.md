# TADA Intelligence Platform - n8n Workflows

This directory contains all n8n workflow definitions for the TADA Content Intelligence Platform. These workflows orchestrate content collection, AI agent invocation, alerting, and reporting.

---

## Quick Setup

### 1. Prerequisites

- n8n v1.30+ (self-hosted or cloud)
- PostgreSQL 15+ with TADA schema applied (see `/sql/`)
- FastAPI backend running at `TADA_API_BASE_URL`
- Slack workspace with bot token
- API credentials for Reddit, Twitter/X, LinkedIn

### 2. Environment Variables

Set these in your n8n environment (`Settings > Variables` or `.env`):

```env
# TADA Backend
TADA_API_BASE_URL=https://api.yourdomain.com
TADA_API_KEY=your-api-key-here
TADA_DASHBOARD_URL=https://app.yourdomain.com

# n8n Internal
N8N_BASE_URL=https://n8n.yourdomain.com
N8N_WEBHOOK_SECRET=your-webhook-secret

# Slack
SLACK_CHANNEL_ALERTS=#tada-alerts
SLACK_CHANNEL_CRITICAL_ALERTS=#tada-critical
SLACK_CHANNEL_ERRORS=#tada-errors
SLACK_CHANNEL_INTEL=#tada-intel
SLACK_CHANNEL_BRIEFINGS=#tada-briefings
SLACK_CHANNEL_CONTENT_TEAM=#content-team
SLACK_CHANNEL_LEADERSHIP=#leadership
SLACK_CHANNEL_OPS=#tada-ops

# Email
ALERT_FROM_EMAIL=alerts@yourdomain.com
LEADERSHIP_EMAIL_LIST=ceo@yourdomain.com,coo@yourdomain.com

# Social APIs
REDDIT_ACCESS_TOKEN=your-reddit-token
TWITTER_BEARER_TOKEN=your-twitter-bearer-token
LINKEDIN_ACCESS_TOKEN=your-linkedin-token
```

### 3. Credentials Setup in n8n

Create these credentials in `n8n > Credentials`:

| Credential ID | Type | Used In |
|---|---|---|
| `postgres-tada` | PostgreSQL | All DB workflows |
| `slack-tada` | Slack OAuth2 | All alert workflows |
| `smtp-tada` | SMTP | 06-alert-system (critical emails) |

### 4. Import Workflows

```bash
# Import all workflows via n8n CLI
for f in workflows/n8n/*.json; do
  n8n import:workflow --input="$f"
done

# Or import via n8n UI: Settings > Import from file
```

### 5. Activate Workflows

Activate in this order to ensure dependencies are met:
1. `06-alert-system` (error handler — activate first)
2. `08-source-health-check`
3. `01-daily-content-collection`
4. `02-social-monitoring`
5. `03-signal-detection-pipeline`
6. `04-competitive-intelligence`
7. `09-pain-point-detection`
8. `05-executive-briefing`
9. `07-content-calendar-generation`
10. `10-roi-metrics-tracker`

---

## Workflow Dependency Map

```
                    ┌─────────────────────────────────────────┐
                    │           TRIGGER LAYER                  │
                    │  Cron schedules & webhook triggers        │
                    └──────────────┬──────────────────────────┘
                                   │
              ┌────────────────────┼──────────────────────┐
              ▼                    ▼                       ▼
   ┌──────────────────┐  ┌─────────────────┐  ┌────────────────────┐
   │ 01-content-      │  │ 02-social-      │  │ 08-source-health   │
   │ collection       │  │ monitoring      │  │ (every 6h)         │
   │ (every 2h)       │  │ (every 4h)      │  └────────────────────┘
   └────────┬─────────┘  └────────┬────────┘
            │ webhook              │ DB write
            ▼                     ▼
   ┌──────────────────────────────────────────┐
   │        03-signal-detection-pipeline       │
   │   (webhook trigger OR hourly fallback)    │
   └────────────────────┬─────────────────────┘
                        │ signals detected
              ┌─────────┴──────────┐
              ▼                    ▼
   ┌──────────────────┐  ┌──────────────────────┐
   │ 06-alert-system  │  │ Signals stored in DB  │
   │ (webhook trigger)│  └──────────┬───────────┘
   └──────────────────┘             │
                                    │ (data available)
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                       ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐
   │ 04-competitive-  │  │ 05-executive-    │  │ 07-content-        │
   │ intelligence     │  │ briefing         │  │ calendar           │
   │ (daily 9 AM)     │  │ (daily 6AM +     │  │ (Monday 8 AM)      │
   └──────────────────┘  │  Monday 7AM)     │  └────────────────────┘
                         └──────────────────┘
              ┌─────────────────────────────────────────────┐
              ▼                                             ▼
   ┌──────────────────────────────────┐        ┌───────────────────┐
   │ 09-pain-point-detection          │        │ 10-roi-metrics    │
   │ (daily 10 AM, Friday report)     │        │ (daily midnight)  │
   └──────────────────────────────────┘        └───────────────────┘
```

### Webhook Connections

| Source Workflow | Fires Webhook To | Purpose |
|---|---|---|
| `01-content-collection` | `03-signal-detection` | Trigger signal detection after collection |
| `03-signal-detection` | `06-alert-system` | Alert on critical signals |
| All workflows | `06-alert-system` | Error handling (n8n error workflow) |

---

## Error Handling Strategy

### 1. Node-Level (`continueOnFail: true`)
- All HTTP requests to external APIs have `continueOnFail: true`
- Failed RSS fetches are silently skipped; other sources continue
- Source health check records failures per source

### 2. Retry Logic
- AI agent calls: 2 retries with 5-10s delay
- Webhook notifications: 3 retries with 2s delay
- Database operations: no auto-retry (immediate failure alert)

### 3. Workflow-Level Error Handler
- `06-alert-system` is set as the error workflow for all other workflows
- When a workflow fails completely, n8n automatically calls `06-alert-system`
- Errors are logged to the `workflow_errors` table and sent to `#tada-errors` Slack

### 4. Dead Letter Pattern
- Content that fails signal detection is marked `processed_no_signal` after 6 hours
- Prevents infinite reprocessing of problematic content

---

## Monitoring

### Key Metrics to Watch

| Metric | Table | Query |
|---|---|---|
| Articles collected per day | `raw_content` | `COUNT(*) WHERE DATE(collected_at) = TODAY` |
| Signals detected per day | `signals` | `COUNT(*) WHERE DATE(detected_at) = TODAY` |
| Processing backlog | `raw_content` | `COUNT(*) WHERE status = 'unprocessed'` |
| Source health | `content_sources` | `WHERE is_healthy = false` |
| Alert volume | `alerts` | `COUNT(*) WHERE DATE(sent_at) = TODAY` |

### n8n Execution Monitoring

Access at: `n8n > Executions` — filter by workflow and status.

Set up n8n's built-in email notifications for workflow failures:
`n8n > Settings > User Management > Email notifications`

### Recommended Dashboards

- **Operations Dashboard**: Source health + collection volumes
- **Intelligence Dashboard**: Signal counts + severity breakdown
- **ROI Dashboard**: Hours saved + value delivered (from `roi_metrics` table)

---

## Adding New Sources

### Adding an RSS Feed

1. Add the source to the `content_sources` table:
```sql
INSERT INTO content_sources (name, url, source_type, is_active)
VALUES ('New Publication', 'https://example.com/feed/', 'rss', true);
```

2. Add an RSS node to `01-daily-content-collection.json`:
```json
{
  "parameters": {
    "url": "https://example.com/feed/",
    "responseFormat": "string",
    "options": { "timeout": 10000 }
  },
  "id": "rss-new-publication",
  "name": "RSS: New Publication",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.1,
  "position": [340, 1100],
  "continueOnFail": true
}
```

3. Add a connection from `Every 2 Hours` to the new node and from the new node to `Parse RSS Feeds`.

4. Re-import the workflow in n8n.

### Adding a Social Source

Add the platform's API call to `02-social-monitoring.json` following the same pattern as existing Reddit/Twitter/LinkedIn nodes. Connect to `Normalize Social Posts`.

---

## Adding New Workflows

1. Create the workflow JSON file following the naming convention: `NN-workflow-name.json`
2. Use the standard node IDs pattern: descriptive kebab-case IDs
3. Set `errorWorkflow: "06-alert-system"` in settings
4. Set appropriate timezone: `America/New_York` (or match your team's TZ)
5. Add tags for categorization
6. Document the workflow in `/docs/11-n8n-workflows.md`
7. Update the dependency map in this README

---

## Workflow Schedule Summary

| Workflow | Schedule | Timezone |
|---|---|---|
| 01 - Content Collection | Every 2 hours | America/New_York |
| 02 - Social Monitoring | Every 4 hours | America/New_York |
| 03 - Signal Detection | Hourly + webhook | America/New_York |
| 04 - Competitive Intel | Daily 9:00 AM | America/New_York |
| 05 - Executive Briefing | Daily 6:00 AM + Monday 7:00 AM | America/New_York |
| 06 - Alert System | Webhook only | America/New_York |
| 07 - Content Calendar | Monday 8:00 AM | America/New_York |
| 08 - Source Health Check | Every 6 hours | America/New_York |
| 09 - Pain Point Detection | Daily 10:00 AM | America/New_York |
| 10 - ROI Metrics | Daily midnight | America/New_York |

---

## Troubleshooting

### Common Issues

**Content not being collected**
- Check source health: `SELECT * FROM content_sources WHERE is_healthy = false`
- Verify `TADA_API_BASE_URL` is reachable from n8n
- Check n8n execution logs for `01-daily-content-collection`

**Signal detection not running**
- Check webhook URL: `N8N_BASE_URL/webhook/signal-detection-trigger`
- Verify the webhook is receiving POST requests
- Check `raw_content` table for items stuck in `unprocessed` status

**Slack notifications not sending**
- Verify Slack OAuth2 credentials in n8n
- Check bot has been invited to the alert channels
- Test with a manual execution of `06-alert-system`

**Database connection errors**
- Verify `postgres-tada` credentials in n8n
- Check PostgreSQL connection string and network access
- Ensure TADA schema tables exist

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-16 | Initial implementation of all 10 workflows |

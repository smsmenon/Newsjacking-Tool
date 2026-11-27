# TADA Intelligence Platform — n8n Workflow Documentation
## Deliverable 11 of 20

All workflows live in `/workflows/n8n/`. Import via n8n UI → Settings → Import Workflow. Credentials are referenced by name — configure them once in n8n Credentials before activating.

---

## Workflow Dependency Map

```
                    ┌─────────────────────────┐
                    │  01-daily-content-       │
                    │  collection (every 2h)   │
                    └─────────┬───────────────┘
                              │ webhook: content-collected
                              ▼
                    ┌─────────────────────────┐
                    │  03-signal-detection-    │◄─── (hourly fallback)
                    │  pipeline               │
                    └─────────┬───────────────┘
                              │ webhook: alert-trigger
                              ▼
                    ┌─────────────────────────┐
                    │  06-alert-system         │
                    └─────────────────────────┘

  ┌──────────────────────┐    ┌──────────────────────────┐
  │ 02-social-monitoring │    │ 04-competitive-intel      │
  │ (every 4h)           │    │ (daily 9 AM)              │
  └──────────┬───────────┘    └──────────────────────────┘
             │
             ▼ (feeds signal detection)

  ┌──────────────────────┐    ┌──────────────────────────┐
  │ 05-executive-briefing│    │ 07-content-calendar       │
  │ (daily 6 AM /        │    │ (Monday 8 AM)             │
  │  weekly Mon 7 AM)    │    └──────────────────────────┘
  └──────────────────────┘

  ┌──────────────────────┐    ┌──────────────────────────┐
  │ 08-source-health     │    │ 09-pain-point-detection  │
  │ (every 6h)           │    │ (daily 10 AM)             │
  └──────────────────────┘    └──────────────────────────┘

  ┌──────────────────────┐
  │ 10-roi-metrics       │
  │ (daily midnight)     │
  └──────────────────────┘
```

---

## Workflow 01 — Daily Content Collection

**File:** `01-daily-content-collection.json`
**Trigger:** Cron — every 2 hours, 24/7
**Purpose:** Fetch fresh content from all 50+ approved sources, deduplicate, store, and hand off to signal detection.

### Flow (ASCII)

```
[Cron Trigger: */2 * * * *]
         │
         ▼
[Load Active Sources]  ← GET /api/v1/sources?is_active=true
         │
         ▼
[Split Into Batches]  ← 10 sources per batch (parallel)
         │
    ┌────┴────────────────────────────────────┐
    │ For each source (parallel execution):   │
    │                                         │
    │  [Fetch RSS / Call API / Scrape]        │
    │         │                               │
    │  [Parse & Normalize]                    │
    │  (title, author, url, content,          │
    │   published_at, metadata)               │
    │         │                               │
    │  [Compute SHA-256 content_hash]         │
    │         │                               │
    │  [Check Dedup] ← SELECT FROM raw_content│
    │  WHERE content_hash = $hash             │
    │         │                               │
    │    ┌────┴────┐                         │
    │  EXISTS   NOT EXISTS                   │
    │    │          │                         │
    │  [Skip]  [INSERT raw_content]           │
    │          [UPDATE source.last_collected] │
    └────────────────────────────────────────┘
         │ (all batches complete)
         ▼
[Count New Items]
         │
    ┌────┴────┐
  0 new    >0 new
    │          │
  [Log]   [POST /api/v1/webhooks/content-collected]
           {source_ids: [...], new_count: N}
                │
                ▼
         [Signal Detection Workflow triggered]
```

### Key Nodes
| Node | Type | Config |
|------|------|--------|
| Cron Trigger | Schedule | `0 */2 * * *` |
| HTTP Request (sources) | HTTP | GET `{{$env.API_BASE_URL}}/api/v1/sources` |
| SplitInBatches | Core | batchSize: 10 |
| HTTP Request (RSS) | HTTP | GET `{{$json.url}}`, timeout: 30s |
| RSS Parser | RSS | Parse feed items |
| Function (hash) | Code | `crypto.createHash('sha256').update(content).digest('hex')` |
| PostgreSQL (dedup) | DB | SELECT content_hash |
| PostgreSQL (insert) | DB | INSERT raw_content |
| HTTP Request (webhook) | HTTP | POST `/api/v1/webhooks/content-collected` |

### Error Handling
- Each source fetch wrapped in try/catch
- Failed source → log to `collection_jobs` table with error
- Source fails 3× consecutively → Slack alert to `#tada-ops`
- Global workflow failure → email to `ops@tada.com`

### Retry Config
- Max retries per HTTP node: 3
- Retry wait: 5s exponential backoff
- Overall workflow timeout: 45 minutes

---

## Workflow 02 — Social Media Monitoring

**File:** `02-social-monitoring.json`
**Trigger:** Cron — every 4 hours
**Purpose:** Monitor LinkedIn, X/Twitter, Reddit for industry conversations, competitor mentions, and pain point signals.

### Flow

```
[Cron Trigger: 0 */4 * * *]
         │
    ┌────┴──────────────────────────────────┐
    │ Parallel branches:                    │
    │                                       │
    │  [LinkedIn RSS/Search API]            │
    │  Keywords: supply chain, procurement, │
    │  manufacturing, tariff, AI adoption   │
    │                                       │
    │  [Twitter/X API v2 Search]            │
    │  Keywords + competitor handles        │
    │                                       │
    │  [Reddit API]                         │
    │  Subreddits: r/supplychain,           │
    │  r/manufacturing, r/procurement,      │
    │  r/scm, r/logistics                   │
    └────────────────────────────────────────┘
         │ (merge all results)
         ▼
[Normalize Post Schema]
(platform, post_id, content, author,
 engagement_count, url, posted_at)
         │
         ▼
[Keyword Relevance Filter]
Score each post: supply chain keywords × 2,
TADA competitor mentions × 3, pain words × 2
(filter: score >= 3)
         │
         ▼
[Deduplication Check]
         │
         ▼
[Store to raw_content]
(source_type: 'social')
         │
         ▼
[Flag High-Engagement Posts]
(engagement > 500 likes OR shares > 100)
         │
    ┌────┴──────┐
  Normal     High-Engagement
    │              │
  [Done]    [POST /webhooks/content-collected]
            (priority: high, trigger_signal_detection: true)
```

### Credentials Required
- `twitter-api-v2` — Bearer token
- `reddit-api` — Client ID + Secret (OAuth2)
- `linkedin-api` — OAuth2 access token (or Proxycurl for scraping)

---

## Workflow 03 — Signal Detection Pipeline

**File:** `03-signal-detection-pipeline.json`
**Trigger:** Webhook (`/api/v1/webhooks/content-collected`) OR Cron fallback (every 1 hour)
**Purpose:** Take batches of new content and run them through the LangGraph Signal Detection agent.

### Flow

```
[Webhook Trigger OR Cron Fallback]
         │
         ▼
[Fetch Unprocessed Content Batch]
SELECT * FROM raw_content
WHERE signal_detection_run = false
ORDER BY collected_at DESC
LIMIT 50
         │
         ▼
[Batch Check]
         │
    ┌────┴────┐
  Empty    Has items
    │          │
  [Done]       ▼
         [POST /api/v1/agents/signal-detection/run]
         {content_ids: [...], batch_size: 50}
                │
                ▼
         [Poll for Completion]  (max 10 min)
         GET /api/v1/agents/runs/{run_id}/status
                │
         ┌──────┴──────┐
       Failed       Completed
         │               │
    [Log Error]    [Fetch Detected Signals]
    [Slack Alert]  GET /api/v1/signals?run_id={id}
                        │
                        ▼
                [Check for Critical Signals]
                WHERE urgency_score > 90
                        │
                   ┌────┴────┐
                No Critical  Critical
                   │              │
                 [Done]   [POST /webhooks/alert-trigger]
                          {signal_ids: [...], severity: 'critical'}
```

### Configuration
- Batch size: 50 articles per run
- LangGraph timeout: 10 minutes
- Critical threshold: urgency_score >= 90

---

## Workflow 04 — Competitive Intelligence

**File:** `04-competitive-intelligence.json`
**Trigger:** Cron — Daily 9:00 AM
**Purpose:** Monitor all competitor websites, press pages, and news for meaningful changes.

### Flow

```
[Cron Trigger: 0 9 * * *]
         │
         ▼
[Load Competitor List]
SELECT * FROM competitors WHERE is_active = true
         │
         ▼
[For each competitor (parallel):]
    │
    ├─ [Fetch Press Release RSS]
    ├─ [Scrape /news or /blog page]
    │   (compare against last scraped hash)
    ├─ [Google News API search]
    │   query: "{competitor_name}" last 24h
    └─ [Fetch LinkedIn company posts via API]
         │
[Merge & Deduplicate]
         │
         ▼
[Filter: New content only]
(compare hashes, dates vs last_run)
         │
    ┌────┴────┐
  Nothing   New content
  new          │
    │          ▼
  [Done]  [POST /api/v1/agents/competitive-intel/run]
          {competitor_id, content: [...]}
               │
               ▼
          [Store competitor_events]
               │
               ▼
          [Check Event Significance]
          (launch / acquisition / funding = high)
               │
         ┌─────┴─────┐
       Normal      Significant
         │               │
    [Log & Done]   [POST /webhooks/alert-trigger]
                   [Notify Slack #competitive-intel]
```

---

## Workflow 05 — Executive Briefing Generation

**File:** `05-executive-briefing.json`
**Trigger:**
- Daily briefing: Cron `0 6 * * *` (6 AM daily)
- Weekly briefing: Cron `0 7 * * 1` (7 AM Monday)

### Flow

```
[Cron Trigger]
         │
         ▼
[Determine Briefing Type]
(daily vs weekly based on trigger)
         │
         ▼
[Gather Top Signals]
SELECT * FROM signals
WHERE detected_at > NOW() - INTERVAL '24 hours' (daily)
   OR detected_at > NOW() - INTERVAL '7 days' (weekly)
ORDER BY composite_score DESC LIMIT 10
         │
         ▼
[Gather Top Trends]
SELECT * FROM trends
ORDER BY momentum_score DESC LIMIT 5
         │
         ▼
[Gather Competitor Events]
SELECT * FROM competitor_events
WHERE detected_at > NOW() - INTERVAL '24 hours'
ORDER BY significance DESC LIMIT 5
         │
         ▼
[POST /api/v1/agents/executive-briefing/run]
{
  briefing_type: 'daily'|'weekly',
  signals: [...],
  trends: [...],
  competitor_events: [...]
}
         │
         ▼
[Wait for completion] (max 5 min)
         │
         ▼
[Store executive_briefing]
status = 'under_review'
         │
         ▼
[Create review_item]
item_type = 'briefing'
status = 'under_review'
         │
         ▼
[Notify Reviewers via Slack]
Channel: #tada-intel-review
Message: "📋 Daily Brief ready for review"
Link: {PLATFORM_URL}/review
```

---

## Workflow 06 — Alert System

**File:** `06-alert-system.json`
**Trigger:** Webhook (`/api/v1/webhooks/alert-trigger`)
**Purpose:** Route critical signals and events to the right people via the right channels.

### Flow

```
[Webhook Trigger]
{signal_ids, severity, alert_type}
         │
         ▼
[Load Signal Details]
GET /api/v1/signals/{id} for each
         │
         ▼
[Deduplication Check]
SELECT * FROM alerts
WHERE created_at > NOW() - INTERVAL '4 hours'
AND source_signal_id IN ({signal_ids})
         │
    ┌────┴────┐
  Duplicate  Not duplicate
    │              │
  [Skip]      [Create alert record]
              INSERT INTO alerts (...)
                    │
                    ▼
              [Route by Severity]
                    │
         ┌──────────┼──────────┐
       CRITICAL    HIGH      MEDIUM
         │          │           │
    [Slack #tada-intel-critical] │    [Slack #tada-intel]
    [Email: leadership@]    [Slack #tada-intel-high]
    [Teams: Leadership]          │
         │          │           │
         └──────────┴──────────┘
                    │
                    ▼
              [Dashboard notification]
              POST /api/v1/notifications
              (real-time via Server-Sent Events)
```

### Alert Routing Rules
| Severity | Slack Channel | Email | Teams |
|----------|--------------|-------|-------|
| CRITICAL | #tada-intel-critical | leadership team | Leadership channel |
| HIGH | #tada-intel-high | - | - |
| MEDIUM | #tada-intel | - | - |
| LOW | Dashboard only | - | - |

### Deduplication Window
- Same signal/topic within 4 hours → skip
- Same competitor within 2 hours → skip

---

## Workflow 07 — Content Calendar Generation

**File:** `07-content-calendar-generation.json`
**Trigger:** Cron — Every Monday 8:00 AM
**Purpose:** Generate a content calendar for the week based on top signals and approved content ideas.

### Flow

```
[Cron Trigger: 0 8 * * 1]
         │
         ▼
[Get Top Signals (Last 7 Days)]
ORDER BY composite_score DESC LIMIT 15
         │
         ▼
[Get Approved Content Ideas]
WHERE status = 'approved'
AND scheduled_date IS NULL
ORDER BY priority DESC
         │
         ▼
[Get Upcoming Industry Events]
(from events calendar if configured)
         │
         ▼
[POST /api/v1/agents/content-strategy/calendar]
{signals, approved_ideas, week_start: '...'}
         │
         ▼
[Store content_calendar record]
         │
         ▼
[Create review_item] (status: under_review)
         │
         ▼
[Notify Content Team]
Slack #tada-content:
"📅 Weekly content calendar generated — needs review"
```

---

## Workflow 08 — Source Health Check

**File:** `08-source-health-check.json`
**Trigger:** Cron — Every 6 hours
**Purpose:** Verify all sources are reachable and collecting correctly.

### Flow

```
[Cron Trigger: 0 */6 * * *]
         │
         ▼
[Load All Active Sources]
         │
         ▼
[For each source (parallel):]
    │
    ├─ [HTTP HEAD request to source URL]
    │   timeout: 10s
    │
    ├─ [Check last_collected timestamp]
    │   Flag if > 3h ago (for 2h sources)
    │
    └─ [Validate RSS feed format]
         │
[Merge Health Results]
         │
         ▼
[Classify Health Status]
- healthy: response 200 + recent collection
- degraded: slow response OR stale collection
- down: timeout or 4xx/5xx
         │
         ▼
[Update source health in DB]
UPDATE sources SET health_status = $status,
last_health_check = NOW()
         │
         ▼
[Check for Degraded/Down Sources]
         │
    ┌────┴────┐
  All OK   Issues found
    │           │
  [Done]   [Group by severity]
                │
           [Slack #tada-ops alert]
           "⚠️ 2 sources degraded: [names]"
```

---

## Workflow 09 — Pain Point Detection

**File:** `09-pain-point-detection.json`
**Trigger:** Cron — Daily 10:00 AM
**Purpose:** Analyze social content for customer pain points, challenges, and complaints.

### Flow

```
[Cron Trigger: 0 10 * * *]
         │
         ▼
[Fetch Social Content from Last 24h]
SELECT * FROM raw_content
WHERE source_type = 'social'
AND collected_at > NOW() - INTERVAL '24 hours'
         │
         ▼
[Filter to Pain Point Signals]
(posts containing: "struggling", "can't", "problem",
"challenge", "frustrated", "broken", "failure",
"doesn't work", "where do I", "how do I", etc.)
         │
         ▼
[POST /api/v1/agents/pain-point/run]
{content_batch: [...]}
         │
         ▼
[Store / Update pain_points]
(increment frequency for existing, insert new)
         │
         ▼
[Check Day of Week]
         │
    ┌────┴────────┐
  Mon-Thu        Friday
    │                │
  [Done]    [Generate Weekly Pain Point Report]
            POST /api/v1/agents/executive-briefing/pain-points
                 │
            [Create review_item]
            [Notify #tada-intel-review]
```

---

## Workflow 10 — ROI Metrics Tracker

**File:** `10-roi-metrics-tracker.json`
**Trigger:** Cron — Daily midnight `0 0 * * *`
**Purpose:** Calculate and store daily ROI metrics for the analytics dashboard.

### Flow

```
[Cron Trigger: 0 0 * * *]
         │
         ▼
[Query Yesterday's Metrics]

  articles_collected:
  SELECT COUNT(*) FROM raw_content
  WHERE DATE(collected_at) = CURRENT_DATE - 1

  signals_detected:
  SELECT COUNT(*) FROM signals
  WHERE DATE(detected_at) = CURRENT_DATE - 1

  trends_updated:
  SELECT COUNT(*) FROM trends
  WHERE DATE(last_updated_at) = CURRENT_DATE - 1

  content_ideas_generated:
  SELECT COUNT(*) FROM content_ideas
  WHERE DATE(created_at) = CURRENT_DATE - 1

  sources_monitored:
  SELECT COUNT(*) FROM sources WHERE is_active = true

  briefings_generated:
  SELECT COUNT(*) FROM executive_briefings
  WHERE DATE(created_at) = CURRENT_DATE - 1
         │
         ▼
[Calculate Derived Metrics]
research_hours_saved =
  (articles_collected × 0.5)
  + (signals_detected × 2.0)
  + (briefings_generated × 4.0)

dollar_value_saved = research_hours_saved × 150
         │
         ▼
[INSERT roi_metrics record]
         │
         ▼
[Check for Milestone Achievements]
(e.g., 10,000th article, 1,000th signal)
         │
    ┌────┴────────┐
  No milestone  Milestone!
    │                │
  [Done]      [Notify #tada-team Slack]
              "🎉 TADA hit 10,000 articles collected!"
```

---

## Environment Variables Required

```bash
# Core
API_BASE_URL=https://api.tada-intelligence.com
N8N_ENCRYPTION_KEY=<generate-256-bit-key>
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<strong-password>

# Database
DB_HOST=
DB_PORT=5432
DB_NAME=tada_intelligence
DB_USER=
DB_PASSWORD=

# Notification
SLACK_WEBHOOK_CRITICAL=https://hooks.slack.com/services/...
SLACK_WEBHOOK_HIGH=https://hooks.slack.com/services/...
SLACK_WEBHOOK_OPS=https://hooks.slack.com/services/...
SLACK_WEBHOOK_CONTENT=https://hooks.slack.com/services/...

# Social APIs
TWITTER_BEARER_TOKEN=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# Email
SENDGRID_API_KEY=
ALERT_EMAIL_TO=leadership@tada.com
OPS_EMAIL_TO=ops@tada.com
```

## Setup Checklist

1. [ ] Configure all credentials in n8n Settings → Credentials
2. [ ] Set all environment variables
3. [ ] Import workflows in order (01 → 10)
4. [ ] Activate workflows in order (08 first for health baseline)
5. [ ] Trigger workflow 01 manually to test first collection
6. [ ] Verify webhook endpoints respond from n8n test
7. [ ] Set up Slack channel webhooks
8. [ ] Test alert pipeline with a manual trigger
9. [ ] Enable all cron schedules
10. [ ] Monitor n8n execution log for 24h before declaring healthy

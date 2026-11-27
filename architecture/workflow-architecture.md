# TADA Content Intelligence Platform — n8n Workflow Architecture

**Version:** 1.0.0
**Date:** 2026-06-16

This document defines all 10 n8n workflows that orchestrate the TADA intelligence pipeline. n8n runs self-hosted on Railway in **queue mode** with dedicated worker processes. All workflows call FastAPI endpoints — n8n does not contain business logic, only orchestration.

---

## n8n Infrastructure Configuration

```
n8n Server: queue mode (not webhook mode)
Workers: 2 dedicated worker processes
Database: PostgreSQL (shared with main app, separate schema: n8n_*)
Redis: shared Redis instance for queue management
Execution Timeout: 30 minutes per workflow
Max Concurrency: 5 parallel executions per workflow
Retry Policy: 3 retries with exponential backoff (base: 2s, max: 60s)
Error Notification: Slack #platform-alerts channel
Webhook base URL: https://n8n.tada-intelligence.railway.app
```

---

## Workflow 1: Daily Collection Workflow

**Purpose:** Triggers the Collection Agent to ingest new content from all 50+ sources on a rolling schedule.

**Trigger:** Cron — `*/15 * * * *` (every 15 minutes)

**Workflow Steps:**

```
START
  │
  ▼
[1] Cron Trigger (*/15 * * * *)
  │
  ▼
[2] Check System Health
    HTTP GET → /health
    Assert: status = "healthy"
    If unhealthy → Skip → Send alert → END
  │
  ▼
[3] Fetch Active Sources
    HTTP GET → /api/v1/sources?is_active=true&due_for_fetch=true
    Returns: list of source objects with fetch schedules
  │
  ▼
[4] Split by Source Type
    Node: Switch (RSS | API | Social | Web | Podcast | PDF)
  │
  ├─► [5a] RSS/API Sources (batch of 20)
  │         HTTP POST → /agents/run
  │         body: { agent: "collection", source_ids: [...], type: "rss_api" }
  │
  ├─► [5b] Social Sources (Twitter/X, Reddit, LinkedIn)
  │         HTTP POST → /agents/run
  │         body: { agent: "collection", source_ids: [...], type: "social" }
  │
  ├─► [5c] Web Scraping (only on 4hr schedule check)
  │         HTTP POST → /agents/run
  │         body: { agent: "collection", source_ids: [...], type: "web" }
  │
  └─► [5d] Podcast/Video (only on 24hr schedule check)
            HTTP POST → /agents/run
            body: { agent: "collection", source_ids: [...], type: "podcast" }
  │
  ▼
[6] Wait for Agent Runs (poll /agents/status every 30s, timeout 10min)
  │
  ▼
[7] Process Results
    - Log items_fetched, items_new, items_quarantined per source
    - Update source.last_fetched_at
    - Update source health scores
  │
  ▼
[8] Trigger Signal Detection (if items_new > 0)
    HTTP POST → /webhooks/n8n
    body: { workflow: "signal_detection", raw_content_ids: [...] }
  │
  ▼
[9] Update Collection Metrics
    Prometheus counter: tada_items_collected_total
    Prometheus gauge: tada_sources_health_score
  │
  ▼
END
```

**Error Handling:**
- Failed source fetch: Log error, increment `source.failure_count`. After 3 failures: set `source.status = "degraded"`, send Slack alert to #platform-alerts.
- Agent run timeout (>10min): Log, send alert, mark run as failed, sources remain in queue for next cycle.
- Database connection failure: Exponential backoff retry (2s, 4s, 8s), then alert.

**Retry Logic:**
- HTTP requests: 3 retries, 2s/4s/8s backoff
- Entire workflow: Does NOT retry — next cron tick handles missed items

---

## Workflow 2: Signal Detection Workflow

**Purpose:** Processes new content items through signal detection and validation pipeline.

**Trigger:**
- Webhook: `POST /n8n/webhooks/signal-detection` (called by Workflow 1)
- Fallback Cron: `0 * * * *` (every hour) — catches any missed content items

**Workflow Steps:**

```
START
  │
  ▼
[1] Webhook / Cron Trigger
  │
  ▼
[2] Load Unprocessed Content Items
    HTTP GET → /api/v1/content-items?status=extraction_complete&signal_status=unprocessed&limit=100
  │
  ▼
[3] Check: Items Available?
    If 0 items → Log "nothing to process" → END
  │
  ▼
[4] Batch into Groups of 50
    SplitInBatches node → batches of 50 content_item_ids
  │
  ▼
[5] Run Signal Detection Agent
    HTTP POST → /agents/run
    body: { agent: "signal_detection", content_item_ids: [...batch...] }
    Wait: poll /agents/status, timeout 5min
  │
  ▼
[6] Parse Agent Results
    For each detected signal:
      - signal_type, confidence, signal_id
  │
  ▼
[7] High-Confidence Signals (confidence >= 0.65)?
    Split: high_confidence | low_confidence
  │
  ├─► [8a] High Confidence → Run Multi-Source Validation
  │         HTTP POST → /api/v1/signals/{signal_id}/validate
  │         Returns: multi_source_confirmed, source_count
  │
  └─► [8b] Low Confidence → Archive
            HTTP PATCH → /api/v1/signals/{signal_id}
            body: { status: "low_confidence" }
  │
  ▼
[9] Validated Signals → Relevance Scoring
    HTTP POST → /api/v1/signals/{signal_id}/score
    Returns: relevance_score, score_breakdown
  │
  ▼
[10] High Relevance (score >= 45)?
    If yes → Trigger TADA Perspective Webhook
    HTTP POST → /webhooks/n8n
    body: { workflow: "perspective_generation", signal_id: ... }

    If no → Archive signal
    HTTP PATCH → /api/v1/signals/{signal_id}
    body: { status: "archived_low_relevance" }
  │
  ▼
[11] Trigger Trend Analysis for All Validated Signals
    HTTP POST → /webhooks/n8n
    body: { workflow: "trend_analysis", signal_ids: [...] }
  │
  ▼
[12] Update Metrics
    Prometheus: tada_signals_detected_total (by type)
    Prometheus: tada_signals_validated_total
  │
  ▼
END
```

**Error Handling:**
- Signal detection agent failure: Retry batch after 2min. If third failure, quarantine batch and alert.
- Validation API failure: Treat as `multi_source_confirmed = false` (conservative), log for manual review.
- Relevance scoring failure: Default score to 0 (safe — prevents junk from proceeding), alert analyst.

---

## Workflow 3: Trend Analysis Workflow

**Purpose:** Updates trend tracking data whenever new validated signals arrive, and runs comprehensive trend recalculation hourly.

**Trigger:**
- Webhook: `POST /n8n/webhooks/trend-analysis` (called by Workflow 2)
- Cron: `0 * * * *` (hourly comprehensive recalculation)

**Workflow Steps:**

```
START
  │
  ▼
[1] Trigger (webhook or cron)
  │
  ▼
[2] Run Trend Agent
    HTTP POST → /agents/run
    body: {
        agent: "trend",
        lookback_window_days: 30,
        min_signal_count: 3,
        signal_ids: [...] // from webhook, or null for full recalculation
    }
    Wait: poll /agents/status, timeout 5min
  │
  ▼
[3] Parse Trend Results
    - trends_updated list
    - new_trends_created count
    - trends_archived count
  │
  ▼
[4] Check for Significant Trend Changes
    For each updated trend:
      - momentum_delta > 0.2 (significant momentum change)?
      - direction changed (rising → falling or vice versa)?
      - new trend created with momentum_score > 0.7?
  │
  ▼
[5] Significant Change Detected?
    If yes → Fire Alert Trigger Workflow
    HTTP POST → /webhooks/n8n
    body: { workflow: "alert_trigger", alert_type: "trending", trend_ids: [...] }
  │
  ▼
[6] Update Trend Timeline Data
    HTTP POST → /api/v1/trends/datapoints
    body: { date: today, trend_metrics: [...] }
  │
  ▼
[7] Update Metrics
    Prometheus: tada_active_trends_gauge
    Prometheus: tada_trend_velocity_histogram
  │
  ▼
END
```

**Error Handling:**
- Trend agent failure: Retry once after 5min. If second failure, skip this cycle (non-critical — hourly cron will catch up).
- No new signals: Normal condition — log and END without alerts.

---

## Workflow 4: Competitive Intelligence Workflow

**Purpose:** Monitors competitor activity and updates competitor profiles with new activities.

**Trigger:** Cron — `0 */4 * * *` (every 4 hours)

**Workflow Steps:**

```
START
  │
  ▼
[1] Cron Trigger (0 */4 * * *)
  │
  ▼
[2] Load Active Competitors
    HTTP GET → /api/v1/competitors?is_active=true
    Returns: list of competitors with monitoring config
  │
  ▼
[3] Run Competitive Intelligence Agent
    HTTP POST → /agents/run
    body: {
        agent: "competitive",
        competitor_ids: [...all active...],
        lookback_hours: 4
    }
    Wait: poll /agents/status, timeout 10min
  │
  ▼
[4] Parse Results
    - competitor_activities list
    - high_significance_count
  │
  ▼
[5] Filter High-Significance Activities
    significance = "high"?
  │
  ├─► [6a] High Significance → Fire Alert
  │         HTTP POST → /webhooks/n8n
  │         body: { workflow: "alert_trigger", alert_type: "competitive", activity_ids: [...] }
  │
  └─► [6b] Medium/Low → Store only (no immediate alert)
  │
  ▼
[7] Update Competitor Profiles
    HTTP PATCH → /api/v1/competitors/{id}/last_activity
    body: { last_checked_at: now, activity_count: N }
  │
  ▼
[8] If activities include content publish (blog/whitepaper):
    → Trigger Signal Detection for those content items
    HTTP POST → /webhooks/n8n
    body: { workflow: "signal_detection", content_item_ids: [...] }
  │
  ▼
END
```

**Error Handling:**
- Competitor website unavailable: Log, skip competitor for this cycle, increment failure count.
- API rate limit (Proxycurl/LinkedIn): Pause 60s, retry. If still rate limited: skip, schedule catch-up.

---

## Workflow 5: Pain Point Detection Workflow

**Purpose:** Scans Reddit, LinkedIn, and Twitter/X for customer pain points and buying signals.

**Trigger:** Cron — `0 */2 * * *` (every 2 hours)

**Workflow Steps:**

```
START
  │
  ▼
[1] Cron Trigger (0 */2 * * *)
  │
  ▼
[2] Load Platform Config
    HTTP GET → /api/v1/settings/pain-point-config
    Returns: {
        subreddits: [...],
        twitter_keywords: [...],
        linkedin_keywords: [...],
        lookback_hours: 2
    }
  │
  ▼
[3] Run Pain Point Agent in Parallel (3 branches)

    Branch A: Reddit
    HTTP POST → /agents/run
    body: { agent: "pain_point", platform: "reddit", lookback_hours: 2 }

    Branch B: Twitter/X
    HTTP POST → /agents/run
    body: { agent: "pain_point", platform: "twitter", lookback_hours: 2 }

    Branch C: LinkedIn
    HTTP POST → /agents/run
    body: { agent: "pain_point", platform: "linkedin", lookback_hours: 4 }

    Merge all branches → Combine results
  │
  ▼
[4] Parse Combined Results
    - Total pain_points found
    - High urgency count (urgency_score > 0.8)
    - Buying signals count
  │
  ▼
[5] Aggregate Themes
    HTTP POST → /api/v1/pain-points/aggregate-themes
    Returns: top 5 themes for this cycle
  │
  ▼
[6] Buying Signals Detected?
    If buying_signals > 0 → Notify Sales Intelligence Team
    HTTP POST → /webhooks/n8n
    body: { workflow: "alert_trigger", alert_type: "buying_signal", pain_point_ids: [...] }
  │
  ▼
[7] Update Pain Point Metrics
    Prometheus: tada_pain_points_detected_total
    Prometheus: tada_buying_signals_gauge
  │
  ▼
END
```

**Error Handling:**
- Reddit API rate limit (429): Back off 120s, retry. Reddit scraper fallback if API fails.
- Twitter API error: Log, skip this cycle. Twitter data is additive — missed cycles acceptable.
- LinkedIn: Proxycurl is pay-per-request — only call on 4hr schedule to control costs.

---

## Workflow 6: Executive Briefing Generation Workflow

**Purpose:** Compiles and distributes daily and weekly executive intelligence briefings.

**Trigger:**
- Cron Daily: `0 7 * * *` (7:00 AM for daily briefing)
- Cron Weekly: `0 7 * * 1` (Monday 7:00 AM for weekly briefing)

**Workflow Steps:**

```
START
  │
  ▼
[1] Cron Trigger (determine briefing type: daily|weekly)
  │
  ▼
[2] Check: Minimum Content Available?
    HTTP GET → /api/v1/insights?status=published&since=yesterday&count=true
    If count = 0 → Skip briefing, log "No new content" → END
  │
  ▼
[3] Run Executive Briefing Agent
    HTTP POST → /agents/run
    body: {
        agent: "executive_briefing",
        briefing_type: "daily" | "weekly",
        date: today,
        audience: ["CEO", "CRO", "CPO", "CTO"],
        lookback_days: 1 | 7
    }
    Wait: poll /agents/status, timeout 15min
  │
  ▼
[4] Parse Briefing Output
    - briefing_id
    - executive_summary
    - top_risks count
    - top_opportunities count
  │
  ▼
[5] Human Review Gate
    HTTP POST → /api/v1/review/queue
    body: { content_type: "executive_briefing", content_id: briefing_id }
    Returns: review_id, assigned_reviewer
  │
  ▼
[6] Notify Reviewer
    Slack: "New executive briefing ready for review" → #content-review
    Email: Reviewer email with review link
  │
  ▼
[7] Wait for Review Approval
    Poll: HTTP GET → /api/v1/review/{review_id}/status every 5min
    Timeout: 4 hours (if not reviewed, escalate)
    If Approved → Step 8
    If Rejected → Log + END (will regenerate next cycle)
  │
  ▼
[8] Distribute Approved Briefing
    For each distribution channel:

    Email: Send HTML briefing to executive distribution list
    (SMTP node → configured recipient list)

    Slack: Post executive summary to #executive-intelligence
    (Slack node → executive channel)

    Teams: Post to Executive Intelligence team
    (Teams node → if configured)
  │
  ▼
[9] Store Distribution Record
    HTTP POST → /api/v1/briefings/{briefing_id}/distribution
    body: { channels: [...], sent_at: now, recipient_count: N }
  │
  ▼
[10] Update Metrics
    Prometheus: tada_briefings_sent_total
  │
  ▼
END
```

**Error Handling:**
- Briefing agent failure: Retry once. If second failure: send "Briefing generation failed" alert to admin, skip distribution.
- Review timeout (4hr): Escalate to backup reviewer, send Slack alert to team lead.
- Email delivery failure: Retry 3x, log failed recipients.

---

## Workflow 7: Content Calendar Workflow

**Purpose:** Generates and manages the content calendar based on approved insights, scheduling content across weekly, monthly, and quarterly horizons.

**Trigger:**
- Cron Weekly: `0 8 * * 1` (Monday 8:00 AM — week planning)
- Cron Monthly: `0 8 1 * *` (1st of month — monthly planning)
- Webhook: `POST /n8n/webhooks/content-calendar` (triggered on insight approval)

**Workflow Steps:**

```
START
  │
  ▼
[1] Trigger (weekly/monthly cron or insight-approved webhook)
  │
  ▼
[2] Determine Planning Horizon
    If weekly cron → plan for next 7 days
    If monthly cron → plan for next 30 days
    If webhook → plan entry for approved insight
  │
  ▼
[3] Load Approved but Unscheduled Insights
    HTTP GET → /api/v1/insights?status=published&calendar_scheduled=false
    Returns: list of insights with recommendation priorities
  │
  ▼
[4] Load Calendar Availability
    HTTP GET → /api/v1/calendar?range={planning_horizon}
    Returns: existing slots and open slots per day
  │
  ▼
[5] Run Content Strategy Agent
    HTTP POST → /agents/run
    body: {
        agent: "content_strategy",
        insight_ids: [...],
        calendar_constraints: { existing_slots: [...], horizon_days: 7 }
    }
    Wait: poll /agents/status, timeout 5min
  │
  ▼
[6] Parse Content Plan
    - content_type per insight (linkedin, article, newsletter, briefing)
    - suggested_week per item
    - priority ordering
  │
  ▼
[7] Create Calendar Entries
    For each content plan item:
    HTTP POST → /api/v1/calendar/entries
    body: { insight_id, content_type, title, scheduled_date, persona_target, status: "planned" }
  │
  ▼
[8] Notify Content Team
    Slack: "Content calendar updated — {N} items planned for next {horizon} days"
    → #content-strategy channel
    Include: link to calendar view
  │
  ▼
[9] Generate Weekly Content Brief (weekly cron only)
    Compile: all items scheduled this week with angles and personas
    HTTP POST → /api/v1/briefings/content-brief
    Email: content team distribution list
  │
  ▼
END
```

**Error Handling:**
- Agent failure: Log, skip calendar generation for this cycle. Cron will retry next week/month.
- Calendar conflicts (double-booked slot): Agent automatically resolves by shifting +1 day. If unable to resolve: flag for manual review.

---

## Workflow 8: Alert Trigger Workflow

**Purpose:** Dispatches breaking alerts to Slack, Microsoft Teams, and email based on signal significance and configured routing rules.

**Trigger:** Webhook — `POST /n8n/webhooks/alert-trigger` (called by multiple workflows)

**Webhook Payload:**
```json
{
    "alert_type": "breaking|trending|competitive|buying_signal|review_needed",
    "priority": "critical|high|medium|low",
    "entity_ids": ["uuid"],
    "entity_type": "signal|trend|competitor_activity|pain_point|insight",
    "summary": "string",
    "detail_url": "string"
}
```

**Workflow Steps:**

```
START
  │
  ▼
[1] Webhook Trigger
  │
  ▼
[2] Load Alert Configuration
    HTTP GET → /api/v1/alerts/config
    Returns: routing rules (which type → which channels → which recipients)
  │
  ▼
[3] Match Alert to Routing Rules
    If alert_type = "breaking" AND priority = "critical":
        channels: [slack_executive, teams_leadership, email_ceo]
    If alert_type = "breaking" AND priority = "high":
        channels: [slack_intelligence, teams_marketing]
    If alert_type = "competitive":
        channels: [slack_sales, slack_intelligence]
    If alert_type = "buying_signal":
        channels: [slack_sales]
    If alert_type = "trending":
        channels: [slack_intelligence]
    If alert_type = "review_needed":
        channels: [slack_content_review]
  │
  ▼
[4] Fetch Alert Content
    HTTP GET → /api/v1/{entity_type}/{entity_id}
    Build rich alert payload: title, summary, key points, action link
  │
  ▼
[5] Check Rate Limiting
    HTTP GET → /api/v1/alerts/rate-check?type={alert_type}&window=60min
    If > 5 alerts of same type in last 60min → bundle into digest
    If <= 5 → dispatch individually
  │
  ▼
[6] Dispatch in Parallel

    Branch A: Slack Channels (if configured)
    Post to each configured Slack channel:
    - Rich block format: title, summary, signal score, action buttons
    - Attachment: link to full insight in platform

    Branch B: Microsoft Teams (if configured)
    Post adaptive card to Teams channels

    Branch C: Email (if configured and priority = critical|high)
    Send HTML email to recipient list
    Include: full alert content + action link

    Branch D: WebSocket Push
    HTTP POST → /api/v1/alerts/push (internal WebSocket broadcast)
    For all logged-in users per permission level
  │
  ▼
[7] Record Alert Dispatch
    HTTP POST → /api/v1/alerts
    body: { alert_type, entity_id, channels_dispatched, dispatched_at, recipient_count }
  │
  ▼
[8] Update Alert Metrics
    Prometheus: tada_alerts_dispatched_total (by type, by channel)
  │
  ▼
END
```

**Error Handling:**
- Slack API failure: Retry 3x (2s/4s/8s). If still failing: fall back to email. Log Slack outage.
- Teams webhook failure: Retry 3x. Log, skip — non-critical.
- Email SMTP failure: Retry 3x. If all fail: log critical error, trigger backup SMTP if configured.
- All channels fail: Store alert with status "failed", retry in 5min, alert system admin.

---

## Workflow 9: Human Review Notification Workflow

**Purpose:** Manages the human review queue — assigns reviewers, sends notifications, and tracks review SLAs.

**Trigger:** Webhook — `POST /n8n/webhooks/review-notification` (called whenever a DRAFT insight is created)

**Workflow Steps:**

```
START
  │
  ▼
[1] Webhook Trigger
    Payload: { insight_id, insight_type, priority, topic_categories }
  │
  ▼
[2] Determine Reviewer Assignment
    HTTP GET → /api/v1/team/reviewers?available=true&expertise={topic_categories}
    Assignment logic:
    - Priority "critical" → assign to lead reviewer (specific user ID)
    - Match topic category to reviewer expertise
    - Round-robin if multiple qualified reviewers
    - Fallback to admin if no match
  │
  ▼
[3] Create Review Record
    HTTP POST → /api/v1/review
    body: {
        insight_id,
        reviewer_id: assigned_reviewer,
        priority,
        due_at: now + SLA_hours[priority],
        status: "pending_assignment"
    }
  │
  ▼
[4] Assign to Reviewer
    HTTP PATCH → /api/v1/review/{review_id}
    body: { status: "under_review", reviewer_id }
  │
  ▼
[5] Notify Reviewer

    Slack DM to reviewer:
    "New insight awaiting your review: {title}
    Priority: {priority} | Due: {due_at}
    [Review Now] → {platform_link}"

    Email to reviewer (if priority = critical or high):
    Full insight preview + review action buttons
  │
  ▼
[6] Schedule SLA Reminder
    If not reviewed in SLA_warning_threshold (e.g., 75% of SLA time):

    Sub-workflow: SLA Monitor
    Schedule: HTTP GET → /api/v1/review/{review_id}/status
    At: due_at - 2 hours
    If still pending → Send reminder Slack DM
    At: due_at
    If still pending → Escalate to team lead + admin
  │
  ▼
[7] Update Review Queue Metrics
    Prometheus: tada_review_queue_depth_gauge
    Prometheus: tada_review_assignments_total
  │
  ▼
END

Post-Review (webhook from Human Review System on status change):

    WEBHOOK: review_completed
    Payload: { review_id, insight_id, action: "approved|rejected|revision_requested" }

    If approved → Trigger Repository Sync Workflow
    If rejected → Notify original author/agent, log reason
    If revision → Re-trigger Perspective Agent with reviewer notes
```

**SLA Definitions:**
| Priority | Review SLA | Warning At |
|----------|------------|-----------|
| critical | 2 hours | 90 min |
| high | 8 hours | 6 hours |
| medium | 24 hours | 20 hours |
| low | 72 hours | 60 hours |

---

## Workflow 10: Repository Sync Workflow

**Purpose:** Syncs approved, published insights into the permanent Knowledge Repository, updates the knowledge graph, and refreshes search indexes.

**Trigger:**
- Webhook: `POST /n8n/webhooks/repository-sync` (called when insight APPROVED)
- Cron Nightly: `0 2 * * *` (2:00 AM — full consistency sync)

**Workflow Steps:**

```
START
  │
  ▼
[1] Trigger (webhook or nightly cron)
  │
  ▼
[2] Determine Sync Scope
    If webhook → sync single insight (insight_id from payload)
    If nightly cron → fetch all insights published in last 24hr
    HTTP GET → /api/v1/insights?status=published&since=yesterday&synced_to_knowledge=false
  │
  ▼
[3] Run Repository Agent
    HTTP POST → /agents/run
    body: {
        agent: "repository",
        action: "publish",
        insight_ids: [...]
    }
    Wait: poll /agents/status, timeout 10min
  │
  ▼
[4] Parse Repository Agent Results
    - knowledge_item_ids created
    - entities_extracted list
    - relationships_created count
  │
  ▼
[5] Update Knowledge Graph
    HTTP POST → /api/v1/graph/sync
    body: { entity_ids: [...], relationship_ids: [...] }
  │
  ▼
[6] Refresh Search Index
    HTTP POST → /api/v1/search/reindex
    body: { knowledge_item_ids: [...] }
    (This triggers async embedding upsert into pgvector)
  │
  ▼
[7] Update Insight Record
    HTTP PATCH → /api/v1/insights/{id}
    body: { synced_to_knowledge: true, knowledge_item_id: uuid }
  │
  ▼
[8] Nightly Cron Only — Full Consistency Check
    HTTP POST → /api/v1/knowledge/consistency-check
    Validates:
    - All published insights have knowledge_item records
    - All knowledge_items have embeddings
    - Knowledge graph has no orphaned nodes
    - Search index count matches DB count
    Returns: inconsistency_count
  │
  ▼
[9] Inconsistencies Found?
    If inconsistency_count > 0:
    → Send Slack alert to #platform-health
    → HTTP POST → /api/v1/knowledge/repair (auto-repair if possible)
  │
  ▼
[10] Update Repository Metrics
    Prometheus: tada_knowledge_items_total
    Prometheus: tada_graph_nodes_total
    Prometheus: tada_graph_edges_total
    Prometheus: tada_search_index_size_gauge
  │
  ▼
END
```

**Error Handling:**
- Repository agent failure: Retry once. If fails again: mark insight as `sync_failed`, alert admin. The insight is still PUBLISHED and visible — sync failure doesn't roll back publication.
- Search reindex failure: Log, schedule retry in 10min. Search degrades gracefully (old index still serves queries).
- Knowledge graph error: Log, skip graph update for this item, flag for manual graph repair.

---

## Workflow Dependency Map

```
WF1 (Collection) ──► WF2 (Signal Detection) ──► WF3 (Trend Analysis)
                                            ──► WF8 (Alert Trigger)
                                            ──► WF4 (Competitive Intel) ──► WF8
WF2 ──► [Relevance Score >= 45] ──► Perspective Agent
                                ──► WF9 (Review Notification)
WF9 ──► [Approved] ──► WF10 (Repository Sync)
                   ──► WF7 (Content Calendar)
                   ──► WF8 (Alert Trigger)
WF5 (Pain Point) ──► [Buying Signal] ──► WF8
WF6 (Executive Briefing) ──► WF9 (Review) ──► WF8 (Distribution)
WF7 (Content Calendar) ──► WF8 (Notification)
```

---

## n8n Error Handling Standards

All workflows implement these standard error handling patterns:

### 1. HTTP Request Errors
```
On HTTP error (4xx/5xx):
  Retry: 3 times
  Backoff: 2s → 4s → 8s
  On 3rd failure:
    - Log error with full context (workflow_id, node_name, response_body)
    - Send Slack alert to #platform-alerts
    - Increment Prometheus counter: tada_workflow_errors_total
```

### 2. Workflow-Level Error Catch
Every workflow has a global error handler node:
```
Error Trigger Node → HTTP POST /api/v1/system/workflow-error
body: { workflow_name, error_message, stack_trace, execution_id }
→ Slack alert: #platform-alerts
→ Log to PostgreSQL: workflow_error_log table
```

### 3. Data Validation
Before calling any agent:
- Validate required fields in payload
- Check entity IDs exist in DB
- Log and skip invalid items (do not fail entire batch)

### 4. Circuit Breaker Pattern
If any external API returns > 3 errors in 5 minutes:
- Mark source/API as "circuit_open"
- Skip all calls to that API for next 15 minutes
- Send alert to #platform-alerts
- Automatically retry after cooldown period

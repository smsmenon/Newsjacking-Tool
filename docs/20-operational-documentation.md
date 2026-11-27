# TADA Intelligence Platform — Operational Documentation

## Overview

This guide covers day-to-day operations, team workflows, and incident runbooks for the TADA Intelligence Platform.

---

## 1. Daily Operations

### Morning Checklist (09:00 local time)

Run this checklist every business morning:

```
INFRASTRUCTURE
[ ] Grafana Platform Health dashboard: all green?
    → If red: check Railway service status, investigate logs
[ ] Langfuse: any agent errors in last 8 hours?
    → If yes: check agent logs, assess impact

DATA COLLECTION
[ ] n8n: did overnight collection workflows succeed?
    Path: n8n UI → Executions → filter by last 12 hours
    Expected: "Content Collection" workflows 95%+ success rate
[ ] Articles collected overnight vs. previous night baseline?
    Expected: within 20% of 7-day average
[ ] Source Health Dashboard: any sources showing "stale" (red)?
    → If yes: check source availability, escalate if unavailable

SIGNAL PIPELINE
[ ] New signals created overnight? (check Signal Dashboard)
    Expected: at least 5 signals for normal news cycles
[ ] Any Tier A signals requiring immediate attention?
    → If yes: notify relevant stakeholder via Slack

REVIEW QUEUE
[ ] Review queue depth? (check Review Queue Dashboard)
    Goal: queue should not exceed 50 unreviewed items
    → If over 50: notify review team to prioritize
```

### Review Queue Management

**Priority levels for review items:**

| Priority | Trigger | Target Review Time |
|---|---|---|
| P1 | Tier A signal, competitor crisis, regulatory change | 2 hours |
| P2 | Tier B signal, significant industry news | Same business day |
| P3 | Tier C signal, content ideas | Within 2 business days |
| P4 | Tier D signals, low-priority ideas | Within 1 week |

**Queue balancing:** If a single reviewer has more than 20 P2+ items, redistribute to other available reviewers. Analysts can re-assign items via the Review Queue dashboard.

### Alert Triage Procedure

When an alert fires in Slack (#tada-alerts):

1. **Acknowledge** the alert by replying in the thread: "On it — [Name]"
2. **Identify severity:**
   - API down / data loss risk → P1 (escalate immediately)
   - Degraded performance / single workflow failing → P2 (resolve within 2 hours)
   - Cost spike / source failure → P3 (resolve within 4 hours)
3. **Investigate** using the appropriate runbook (see Runbooks section)
4. **Resolve** and post resolution summary in the alert thread
5. **Log** in the incident log if P1 or P2

### Source Health Monitoring

Check the Source Health Dashboard weekly (or when alerts fire):

**Indicators:**
- **Green:** Collected articles in last 24 hours, within expected volume
- **Yellow:** No articles in 12–24 hours, or volume 50% below average
- **Red:** No articles in 24+ hours

**Common causes for red status:**
- Source website changed structure (selector updates needed)
- Source blocked our requests (add delay, update user-agent)
- Source RSS feed temporarily down
- Source paywalled content change

---

## 2. Weekly Operations

### Weekly Operations Checklist (Monday Morning)

```
ROI METRICS
[ ] Review ROI Dashboard: signals per week trend up or flat?
[ ] Content ideas generated vs. last week?
[ ] Articles collected total vs. last week?
[ ] Review queue throughput: items approved/rejected this week?

SOURCE QUALITY
[ ] Review Source Health Dashboard for chronic yellow/red sources
[ ] Check signal volume per source: are some sources over/underperforming?
[ ] Identify any new potential sources to add
[ ] Review collection error logs for patterns

AGENT PERFORMANCE (Langfuse)
[ ] Check agent success rate (target: 95%+)
[ ] Check p95 latency by agent type (target: <60s)
[ ] Check cost per week vs. budget ($25/week baseline)
[ ] Any prompt quality issues? (check golden set accuracy if run)

SYSTEM
[ ] Check Railway resource usage: CPU, memory, storage trending?
[ ] Check PostgreSQL storage used (baseline: ~350MB/week)
[ ] Check Supabase storage used
[ ] Review any dependency vulnerability scan results
```

### Source Quality Review

For each source showing anomalies:

1. Visit the source URL manually to confirm it's accessible
2. Check the n8n collection workflow execution logs for that source
3. If scraping issue: update CSS selectors in source configuration
4. If rate limited: reduce collection frequency for that source
5. If persistently low signal: consider removing and replacing with better source

### Adding New Sources

1. Research candidate source for signal density (at least 5 relevant articles/week)
2. Check if RSS feed is available (preferred over scraping)
3. If scraping required: verify `robots.txt` allows it
4. Add source via the admin panel: Settings → Sources → Add Source
5. Run manual collection test: Sources → [Source Name] → Collect Now
6. Monitor for 1 week before marking as permanent

---

## 3. Monthly Operations

### Monthly Operations Checklist

```
COST REVIEW
[ ] Pull monthly cost report from Railway, Vercel, Clerk, Supabase, OpenAI
[ ] Compare to previous month and budget
[ ] Identify any cost spikes and root cause
[ ] Update cost projections for next month
[ ] Evaluate optimization opportunities (see Cost Estimates doc)

MODEL PERFORMANCE REVIEW
[ ] Run golden set evaluation (50 labeled articles through signal detection)
[ ] Compare accuracy to baseline (target: 85%+)
[ ] Review any prompt failures from Langfuse
[ ] Assess whether model version updates are available
[ ] Update prompts if accuracy has degraded

SECURITY REVIEW
[ ] Review audit logs for anomalous activity
[ ] Check dependency vulnerability scan results
[ ] Rotate any API keys due for quarterly rotation
[ ] Review access list: any departed employees need removal?
[ ] Check for security patches for infrastructure dependencies

INFRASTRUCTURE REVIEW
[ ] Database storage growth on track with projections?
[ ] Any Railway service plans need upgrading?
[ ] Review Grafana dashboards for any degrading trends
[ ] Check backup verification (confirm Railway backups are restorable)
```

---

## 4. Runbooks

### Runbook: n8n Workflow Failure

**Trigger:** n8n workflow failure alert fires, or morning checklist shows failed collection.

**Steps:**

```
1. IDENTIFY which workflow failed
   → n8n UI → Executions → filter by "Error" status
   → Note: workflow name, error message, failure time

2. CHECK error type
   a) "Cannot connect to database" → check PostgreSQL status (Railway)
   b) "Rate limit exceeded" → source API rate limiting; wait and retry
   c) "Connection timeout" → source temporarily unavailable
   d) "Invalid selector" → source HTML changed; needs selector update
   e) "OpenAI error" → check OpenAI status page (status.openai.com)

3. FIX based on error type
   a) Database down: check Railway dashboard, restart if needed
   b) Rate limit: set workflow to retry in 2 hours
   c) Timeout: manually retry, monitor source
   d) Selector issue: update source scraping config (see Source Config docs)
   e) OpenAI error: if widespread, pause signal processing; retry when resolved

4. RESTART workflow if needed
   → n8n UI → Workflows → [Workflow Name] → Execute Now

5. VERIFY workflow runs successfully

6. LOG in #tada-ops if outage > 2 hours
```

### Runbook: Database Connection Pool Exhaustion

**Trigger:** Alert "Database connections > 80%" or API returning 503 errors with "too many clients."

**Steps:**

```
1. VERIFY the alert
   → Grafana → Database Performance dashboard
   → Check "Active Connections" panel

2. IMMEDIATE MITIGATION
   → If > 95% pool used: restart the FastAPI service on Railway
     (This closes all connections and lets them re-establish at normal levels)

3. IDENTIFY ROOT CAUSE
   a) Check if a specific API endpoint is creating too many connections
      → Look for queries with duration > 5s in logs (connection being held open)
   b) Check if a new deployment caused a connection leak
   c) Check if background job queue is overwhelming the pool

4. FIXES
   a) Long-running queries: optimize or add index
   b) Connection leak: identify the code path, redeploy fix
   c) Job queue overload: reduce AGENT_CONCURRENCY setting temporarily

5. PREVENTIVE
   → Consider adding PgBouncer (see Scaling Strategy doc)
   → Set max connection limit per service via Railway env:
      SQLALCHEMY_POOL_SIZE=10 (down from 20)
```

### Runbook: API High Error Rate

**Trigger:** Alert "API error rate > 1%" or users reporting errors.

**Steps:**

```
1. CHECK error rate in Grafana
   → Platform Health dashboard → Error Rate panel
   → Identify: what % errors? what endpoints? started when?

2. CHECK logs for the error type
   → Railway backend service logs
   → Filter by "level: error"
   → Identify common error pattern

3. COMMON SCENARIOS
   a) 500 errors from database query → check DB health, recent deployments
   b) 503 from upstream (OpenAI, Supabase) → check their status pages
   c) 401/403 spike → check Clerk status, JWT rotation issues
   d) 429 Too Many Requests → rate limiter triggered by legitimate load?

4. ESCALATE if
   → Error rate > 10% for > 5 minutes
   → All API endpoints returning errors (service down)
   → Database is unreachable

5. ROLLBACK if recent deployment is the cause
   → Railway: [Service] → Deployments → previous deploy → Deploy
```

### Runbook: Agent Cost Spike

**Trigger:** Alert "LLM cost > 2x baseline" in Langfuse or daily cost alert from OpenAI.

**Steps:**

```
1. IDENTIFY source of spike
   → Langfuse → Cost Dashboard → Group by agent type
   → Identify which agent consumed excess tokens

2. COMMON CAUSES
   a) Infinite loop in agent graph → agent retrying on failure indefinitely
   b) Large context article overwhelming token budget
   c) Prompt change causing longer outputs
   d) Sudden spike in article volume
   e) Bug causing same article processed multiple times

3. IMMEDIATE ACTIONS
   a) If active infinite loop: stop the agent service on Railway, investigate
   b) If large article: add max token truncation (5000 chars) to preprocessing
   c) If volume spike: confirm it's legitimate (news event) vs. collection bug

4. FIXES
   → Add token limit to each LLM call: max_tokens=1000
   → Add circuit breaker: if single article uses >5000 tokens, skip and log
   → Add deduplication check before processing: was this article already processed?

5. VERIFY cost returns to baseline after fix
```

### Runbook: New Source Onboarding

**Steps to add a new source:**

```
1. EVALUATE the source
   → At least 5 relevant articles per week
   → Publicly accessible (no paywall)
   → robots.txt allows collection (if scraping)
   → RSS feed available? (preferred)

2. CONFIGURE in admin panel
   → Settings → Sources → Add New Source
   → Fill: Name, URL, Type (RSS/Scrape), Collection Frequency
   → For scraping: configure selectors (title, content, date, author)
   → Set source tier (1=highest priority for signal weighting)
   → Set industry tags for filtering

3. TEST
   → Sources → [New Source] → Test Collection
   → Verify: articles appear, dates correct, content not empty

4. ACTIVATE
   → Set source status to "active"
   → Monitor for 24 hours: check Source Health Dashboard

5. CALIBRATE (after 1 week)
   → Review signal quality from this source
   → Adjust source tier if needed
   → Adjust collection frequency if needed
```

---

## 5. Team Workflows

### How Marketing Uses the Platform

**Primary use cases:**
1. **Content ideation:** Check Content Strategy dashboard weekly for AI-generated ideas based on current signals. Filter by "approved" status for ready-to-use concepts.
2. **Competitive monitoring:** Check Competitive Intelligence dashboard before campaigns to understand competitor messaging.
3. **Trend surfing:** Use Trend Timeline to identify rising topics before they peak.

**Recommended daily habit:** 5-minute morning review of Tier A and B signals from the previous day.

**Content review process:**
1. Content team member reviews idea in Review Queue
2. Adds context notes, edits summary if needed
3. Sets target publish date in Content Calendar
4. Approves → idea moves to Calendar view for planning

### How Sales Uses the Platform

**Primary use cases:**
1. **Pre-call research:** Search for signals mentioning the prospect's company or industry before sales calls.
2. **Trigger events:** Monitor signals for "funding announcements," "executive change," "pain point" types — these are high-intent outreach triggers.
3. **Competitive positioning:** Review competitor signal summaries to understand current competitor strengths and weaknesses for objection handling.

**Recommended setup:**
- Create a saved search filter for each key prospect segment
- Enable Slack notifications for Tier A signals tagged with relevant competitors

### How Leadership Uses the Platform

**Primary use cases:**
1. **Executive briefing:** Review the daily AI-generated briefing (emailed at 7:00 AM and available in the Executive Portal).
2. **Strategic signals:** Focus on Tier A signals — these represent the highest-confidence strategic developments.
3. **ROI review:** Monthly review of ROI Dashboard to assess platform value.

**Access level:** `viewer` role — read-only access to signals, insights, and briefings. No editing or review capabilities.

**Escalation:** If leadership spots a signal requiring immediate action, they notify the analyst team via Slack.

### How Customer Success Uses the Platform

**Primary use cases:**
1. **Account-specific intelligence:** Search for signals mentioning customers' industry, regulatory changes, or competitive moves that affect them.
2. **Risk identification:** Monitor for signals that suggest customer pain points or competitive threats that could cause churn.
3. **Renewal intelligence:** Use knowledge graph to understand the competitive landscape for each customer segment ahead of renewals.

**Recommended workflow:**
- Weekly 15-minute review of signals tagged with key customer industry verticals
- Before major customer calls: search the platform for recent signals about that customer's market

### Content Review Process

**Full workflow from signal to published asset:**

```
Signal Detected (automated)
    ↓
Content Idea Generated (Content Strategy Engine)
    ↓
Idea appears in Review Queue [status: pending]
    ↓
Analyst reviews idea:
  - Is it original enough to publish?
  - Is it strategically relevant?
  - Does it have a strong signal foundation?
    → If no: reject with notes
    → If yes: enrich (add angle, suggested format, key points) → submit for approval
    ↓
Senior reviewer approves:
  - Checks strategic alignment
  - Checks competitive sensitivity
  - Approves or sends back with notes
    ↓
Approved → added to Content Calendar
    ↓
Content team executes (outside platform)
    ↓
Published asset logged in ROI Dashboard (manual entry or integration)
```

**SLA targets:**
- Analyst review: within 1 business day of idea appearing
- Senior reviewer approval: within 1 business day of analyst submission
- Total time idea → calendar: < 3 business days

---

## 6. Incident Log Template

For P1 and P2 incidents, log in the team incident tracking document:

```
INCIDENT LOG ENTRY

Date/Time (UTC): 2026-06-16 10:35 UTC
Severity: P2
Reported By: [Name]
Incident Description: n8n content collection workflow failed for all RSS sources

Timeline:
- 10:35: Alert fired in #tada-alerts
- 10:37: [Name] acknowledged and began investigation
- 10:42: Root cause identified — Redis connection dropped, n8n queue cleared
- 10:48: Redis restarted, workflows re-queued
- 10:55: Collection confirmed running, articles appearing in DB

Root Cause: Redis OOM (out of memory) on Railway Starter plan due to cache growth
Impact: ~2 hours of delayed article collection; no data loss
Resolution: Restarted Redis; cleared stale cache keys; upgraded Redis to 512MB plan
Prevention: Added Redis memory alert at 80%; configured TTL on all cached keys
```

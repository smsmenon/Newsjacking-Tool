# n8n Workflow Design

## Workflow: Daily Intelligence Sweep

Recommended schedule:

- Daily at 6:00 AM local business timezone
- Optional hourly partial sweep for priority sources

## Nodes

1. Cron Trigger
2. Load Active Sources from Supabase
3. Split In Batches by Source
4. RSS Read or HTTP Request
5. Firecrawl / Apify Fallback for Full Text
6. Normalize Article
7. Hash URL and Content
8. Supabase Upsert Article
9. Queue Processing Job
10. Wait for Processing Completion
11. Fetch Surfaced Signals
12. Generate Daily Digest
13. Send Review Notification

## Error Handling

- If source fetch fails, increment source failure count.
- If full-text extraction fails, store metadata and retry with alternate connector.
- If model processing fails, route to dead-letter table with error payload.
- If digest generation fails, alert Marketing Ops and Platform Owner.

## Human Review Integration

Recommended channels:

- Slack notification to `#market-intelligence-review`
- Dashboard review queue
- Optional email digest for executives

Nothing should be pushed to CMS, LinkedIn, or email tooling without an approved status.


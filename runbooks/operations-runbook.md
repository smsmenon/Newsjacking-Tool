# Operations Runbook

## Daily Checks

- Confirm the daily digest was generated.
- Check source failures and degraded sources.
- Review surfaced signals with score >= 7.
- Assign draft content opportunities to reviewers.
- Confirm no items moved to published without approval.

## Failed Source

1. Check source URL and RSS URL.
2. Retry the source manually.
3. If the site changed structure, switch connector strategy to Firecrawl, Apify, or licensed API.
4. If the source is paywalled, store metadata and licensed excerpts only.
5. Mark source degraded until the next successful run.

## Bad Signal Or Low-Quality Output

1. Open the signal detail.
2. Review evidence and scoring breakdown.
3. If evidence is weak, reject the output.
4. If the source is valid but perspective is weak, request revision.
5. Log the issue against the prompt version or scoring rule.

## Review SLA

- High-impact signals: same business day
- Standard signals: within 48 hours
- Weekly report: before Monday leadership distribution
- Monthly executive summary: within three business days of month close

## Incident Severity

P1:

- Auto-publication occurs accidentally
- Data leak or credential exposure
- Major source ingestion failure across all sources

P2:

- Daily digest missed
- QA failure rate above threshold
- Review queue older than SLA

P3:

- Individual source degraded
- Minor dashboard display issue
- Non-blocking report formatting issue


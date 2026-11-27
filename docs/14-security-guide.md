# TADA Intelligence Platform — Security Guide

## Overview

This document defines the security posture, controls, and procedures for the TADA Intelligence Platform. Security is implemented in layers: authentication, authorization, data protection, application hardening, and operational controls.

---

## 1. Authentication & Authorization

### 1.1 Clerk JWT Validation in FastAPI

All API requests must include a valid Clerk JWT in the `Authorization: Bearer <token>` header.

**Middleware implementation (`app/middleware/auth.py`):**

```python
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from jose import jwt, JWTError

security = HTTPBearer()

async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    token = credentials.credentials
    try:
        # Fetch JWKS from Clerk
        jwks = await get_clerk_jwks()
        # Verify and decode
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience="tada-backend"
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
```

JWKS keys are cached with a 1-hour TTL to avoid rate-limiting Clerk's endpoint. Refresh on key rotation events (Clerk webhook).

### 1.2 Role-Based Access Control

Four roles are enforced at the API layer:

| Role | Description | Access Level |
|---|---|---|
| `admin` | Platform administrators | Full access, user management, config |
| `analyst` | Content/intelligence analysts | Read + write signals, content ideas |
| `reviewer` | Human review team | Review queue, approve/reject content |
| `viewer` | Read-only stakeholders | Read published signals and insights |

Roles are stored in Clerk user public metadata and embedded in the JWT:

```python
def require_role(*roles: str):
    async def check_role(user: dict = Depends(verify_clerk_token)):
        user_role = user.get("role")
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role

# Usage on endpoints:
@router.post("/signals/{id}/approve")
async def approve_signal(
    id: str,
    user: dict = Depends(require_role("admin", "analyst"))
):
    ...
```

### 1.3 API Key Management for n8n Webhooks

n8n communicates with the FastAPI backend via webhook calls. These are authenticated using a shared secret, not user JWTs.

**Webhook authentication:**

```python
from fastapi import Header, HTTPException
import hmac, hashlib

def verify_n8n_webhook(
    x_webhook_secret: str = Header(None),
    x_webhook_signature: str = Header(None)
):
    expected_secret = settings.N8N_WEBHOOK_SECRET
    if not hmac.compare_digest(x_webhook_secret or "", expected_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
```

For additional protection, optionally verify HMAC-SHA256 signature of the request body.

**Key rotation procedure:**

1. Generate new secret: `openssl rand -hex 32`
2. Set new secret in Railway backend environment: `N8N_WEBHOOK_SECRET_NEW`
3. Update n8n credential to send both old and new headers (dual-header period)
4. Deploy backend code that accepts either
5. After 24 hours, remove old secret and clean up

### 1.4 Service-to-Service Authentication

| Connection | Method |
|---|---|
| Backend → PostgreSQL | Railway internal network + password auth |
| Backend → Redis | Railway internal network + password |
| Backend → Supabase | Service role key (server-side only) |
| Backend → OpenAI | API key in environment |
| Backend → Langfuse | Secret key in environment |
| n8n → Backend | Webhook secret header |
| n8n → OpenAI | n8n OpenAI credential |
| Frontend → Backend | Clerk JWT |
| Frontend → Supabase | Anon key (public, row-level security enforced) |

---

## 2. Data Security

### 2.1 PII Handling

TADA monitors external content sources (news, LinkedIn, competitor sites). The following rules apply:

- **No personal data from monitored sources is stored.** Article authors are stored as string names only, not linked to user profiles.
- **User data** (login, preferences, review history) is minimal and stored only in Clerk and the `users` table.
- **No scraping of personal social media profiles.** Source collection is limited to public company pages, official news feeds, and press releases.
- **Review audit logs** record the reviewer's Clerk user ID and action timestamp, not other PII.

### 2.2 API Key Rotation Procedures

**Scheduled rotation (quarterly):**

1. Generate new key from the relevant service dashboard
2. Add new key as `*_KEY_NEW` variable in Railway environment
3. Deploy backend update that reads new key
4. Monitor for 24 hours to ensure no errors
5. Remove old key variable
6. Revoke old key in service dashboard

**Emergency rotation (on suspected compromise):**

1. Immediately revoke compromised key in service dashboard
2. Set new key in Railway environment
3. Trigger Railway redeploy
4. Check audit logs for unauthorized usage
5. Notify team via incident channel

### 2.3 Secrets Management

All secrets are stored as Railway environment variables — never in code, `.env` files committed to git, or logs.

**Rules:**
- Never log API keys or secrets (even partial)
- Never include secrets in error messages returned to clients
- `.env.local` is in `.gitignore` — verify this on every new contributor setup
- Railway environment variables are encrypted at rest by Railway

**Pre-commit hook to prevent accidental secret commits:**

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached | grep -E "(sk-|pk_live_|eyJ|AKIA)" ; then
    echo "ERROR: Possible secret detected in commit. Aborting."
    exit 1
fi
```

### 2.4 Database Encryption

- **At rest:** Railway PostgreSQL uses AES-256 encryption at rest by default
- **In transit:** All connections use TLS 1.2+ (enforced by `?sslmode=require` in connection string)
- **Backups:** Railway automated backups are encrypted with the same key

---

## 3. Application Security

### 3.1 Input Validation

All API inputs are validated with Pydantic v2 before reaching business logic:

```python
from pydantic import BaseModel, field_validator, constr
from typing import Optional

class ArticleCreateRequest(BaseModel):
    title: constr(min_length=1, max_length=500)
    url: str
    source_id: str
    content: Optional[constr(max_length=100000)] = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must be http or https')
        return v
```

Never pass raw user input to database queries, shell commands, or LLM prompts without sanitization.

### 3.2 SQL Injection Prevention

The platform uses SQLAlchemy ORM exclusively for database access. Raw SQL is only used in migrations and is parameterized:

```python
# Correct — parameterized
result = await db.execute(
    select(Article).where(Article.id == article_id)
)

# Correct — raw SQL with parameters
result = await db.execute(
    text("SELECT * FROM articles WHERE id = :id"),
    {"id": article_id}
)

# NEVER do this:
# result = await db.execute(f"SELECT * FROM articles WHERE id = '{article_id}'")
```

### 3.3 XSS Prevention

**Next.js CSP Headers** (`next.config.js`):

```js
const ContentSecurityPolicy = `
  default-src 'self';
  script-src 'self' 'unsafe-eval' 'unsafe-inline' https://clerk.tada-intelligence.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  connect-src 'self' https://api.tada-intelligence.com wss://api.tada-intelligence.com https://clerk.tada-intelligence.com;
  frame-ancestors 'none';
`;

module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Content-Security-Policy', value: ContentSecurityPolicy.replace(/\n/g, '') },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ]
  },
}
```

All user-generated content displayed in the frontend uses React's automatic XSS escaping. Never use `dangerouslySetInnerHTML` with untrusted content.

### 3.4 Rate Limiting

Rate limiting is implemented at the FastAPI layer using `slowapi` backed by Redis:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

@router.post("/api/v1/search")
@limiter.limit("30/minute")
async def search(request: Request, ...):
    ...
```

**Rate limits by endpoint class:**

| Endpoint Class | Limit |
|---|---|
| Authentication endpoints | 10/minute per IP |
| Search | 30/minute per user |
| Standard API reads | 120/minute per user |
| Content creation | 30/minute per user |
| Webhook endpoints | 1000/minute per source IP |
| Admin endpoints | 60/minute per user |

### 3.5 CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # e.g. ["https://app.tada-intelligence.com"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
```

In production, `CORS_ORIGINS` must be the exact frontend domain(s). Wildcards (`*`) are prohibited.

---

## 4. Operational Security

### 4.1 Webhook Signature Verification

When n8n sends webhooks to the backend, each request is verified:

```python
import hmac
import hashlib

def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

n8n must include `X-Webhook-Signature: sha256=<hmac>` in all webhook calls.

### 4.2 Audit Logging

All review actions and administrative operations are logged to the `audit_logs` table:

```python
async def log_audit_event(
    db: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict = None
):
    log = AuditLog(
        user_id=user_id,
        action=action,  # e.g. "signal.approved", "content.published", "user.role_changed"
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata or {},
        ip_address=request.client.host,
        created_at=datetime.utcnow()
    )
    db.add(log)
    await db.commit()
```

**Events requiring audit logs:**
- Any signal approval/rejection
- Content idea publishing
- User role changes
- Source add/disable
- API key generation
- Export downloads
- Admin configuration changes

Audit logs are immutable (no UPDATE or DELETE on `audit_logs` table — enforced via Row-Level Security or application logic).

### 4.3 Dependency Scanning

**GitHub Actions workflow (`.github/workflows/security.yml`):**

```yaml
name: Security Scan

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday

jobs:
  python-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run pip-audit
        run: |
          pip install pip-audit
          pip-audit -r backend/requirements.txt

  npm-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run npm audit
        run: |
          cd frontend
          npm audit --audit-level=high

  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
```

### 4.4 Security Update Procedures

**Patch Tuesday process (first Tuesday of each month):**

1. Review automated dependency scan results in GitHub Actions
2. For `CRITICAL` and `HIGH` vulnerabilities: patch within 24 hours
3. For `MEDIUM` vulnerabilities: patch within 2 weeks
4. For `LOW` vulnerabilities: include in next scheduled release
5. Test patches in staging environment before production deploy

---

## 5. Compliance Considerations

### 5.1 Data Retention Policies

| Data Type | Retention Period | Justification |
|---|---|---|
| Collected articles | 2 years | Trend analysis lookback |
| Signals | 3 years | Strategic intelligence history |
| User review actions | 3 years | Audit trail |
| Audit logs | 5 years | Compliance |
| System logs | 90 days | Debugging and incident response |
| Raw article HTML | 6 months | Re-processing capability |

Automated cleanup jobs run monthly via n8n.

### 5.2 Right to Deletion

TADA stores minimal user data. On a user deletion request:

1. Delete the user from Clerk (triggers `user.deleted` webhook)
2. Webhook handler anonymizes the user's review history: reviewer name → `[deleted]`
3. Audit logs retain the action but remove identifying fields
4. Content created by the user is retained (it represents company intelligence, not personal data)

User deletion does **not** affect:
- Articles and signals (content data, not personal data)
- Company insights and reports

### 5.3 Third-Party Data Usage Compliance

**News APIs and RSS feeds:** Usage is governed by each provider's terms of service. TADA stores article metadata and summaries, not full republished content, which typically falls within fair use.

**LinkedIn data:** Only public company page posts via LinkedIn API with proper OAuth. Do not scrape private profiles. Adhere to LinkedIn's API Terms of Service — commercial use requires appropriate API tier.

**Twitter/X data:** Use only the official API. Do not retain tweets beyond the platform's specified retention windows. Delete content if the original post is deleted (if using Filtered Stream).

**Web scraping:** Only scrape publicly accessible pages. Respect `robots.txt`. Include a descriptive User-Agent string. Do not bypass paywalls or authentication.

**Data sharing:** Collected intelligence is for internal use only. Do not redistribute raw third-party content to external parties.

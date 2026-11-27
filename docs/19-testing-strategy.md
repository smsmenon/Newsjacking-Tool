# TADA Intelligence Platform — Testing Strategy

## Overview

Testing is organized into five layers: unit, integration, end-to-end, AI output validation, and load testing. Each layer has specific scope and tooling. The CI/CD pipeline (GitHub Actions) runs unit and integration tests on every pull request; E2E and load tests run nightly and pre-release.

---

## 1. Unit Tests (pytest)

**Location:** `backend/tests/unit/`
**Run:** `pytest tests/unit/ -v --cov=app --cov-report=html`
**Target coverage:** 80%+ for business logic modules

### 1.1 Agent Node Functions

Each LangGraph agent node is tested in isolation with mocked LLM calls:

```python
# tests/unit/agents/test_signal_detection.py
import pytest
from unittest.mock import AsyncMock, patch
from agents.signal_detection import extract_signals_node

@pytest.fixture
def sample_article():
    return {
        "id": "art_123",
        "title": "Competitor X Launches New Product",
        "content": "Competitor X announced today...",
        "source": "TechCrunch"
    }

@pytest.mark.asyncio
async def test_extract_signals_returns_signals(sample_article):
    mock_llm_response = {
        "signals": [
            {"type": "competitive_move", "confidence": 0.9, "summary": "..."}
        ]
    }

    with patch("agents.signal_detection.llm.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value.content = json.dumps(mock_llm_response)

        result = await extract_signals_node({"article": sample_article})

        assert len(result["signals"]) == 1
        assert result["signals"][0]["type"] == "competitive_move"
        assert result["signals"][0]["confidence"] == 0.9

@pytest.mark.asyncio
async def test_extract_signals_handles_llm_error(sample_article):
    with patch("agents.signal_detection.llm.ainvoke", side_effect=Exception("OpenAI error")):
        result = await extract_signals_node({"article": sample_article})

        assert result["signals"] == []
        assert result["error"] is not None
```

### 1.2 API Endpoint Handlers

```python
# tests/unit/api/test_signals.py
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_list_signals_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/signals")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_signals_returns_paginated_results(auth_headers, db_with_signals):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/signals?limit=10", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "signals" in data
    assert "next_cursor" in data
    assert len(data["signals"]) <= 10
```

### 1.3 Signal Detection Logic

```python
# tests/unit/core/test_scoring.py
from app.core.scoring import calculate_signal_score, assign_tier

def test_signal_score_weights_recency():
    recent_signal = {"base_score": 0.8, "age_hours": 2, "source_tier": 1}
    old_signal = {"base_score": 0.8, "age_hours": 72, "source_tier": 1}

    assert calculate_signal_score(recent_signal) > calculate_signal_score(old_signal)

def test_tier_assignment():
    assert assign_tier(0.85) == "A"
    assert assign_tier(0.65) == "B"
    assert assign_tier(0.40) == "C"
    assert assign_tier(0.20) == "D"

def test_competitive_signals_get_boost():
    competitive = {"type": "competitive_move", "base_score": 0.7}
    industry = {"type": "industry_news", "base_score": 0.7}

    assert calculate_signal_score(competitive) > calculate_signal_score(industry)
```

### 1.4 Database Models

```python
# tests/unit/models/test_article.py
from app.models import Article

def test_article_content_hash_generated():
    article = Article(
        title="Test Article",
        url="https://example.com/test",
        content="Test content here"
    )
    assert article.content_hash is not None
    assert len(article.content_hash) == 64  # SHA-256 hex

def test_article_duplicate_detection(db_session, existing_article):
    duplicate = Article(url=existing_article.url)
    assert duplicate.is_duplicate(db_session) == True
```

---

## 2. Integration Tests

**Location:** `backend/tests/integration/`
**Run:** `pytest tests/integration/ -v` (requires test database)
**Environment:** Uses a separate `tada_test` database with test fixtures

### 2.1 Full Pipeline: Article → Signal → Insight

```python
# tests/integration/test_full_pipeline.py
@pytest.mark.asyncio
async def test_article_to_signal_pipeline(test_db, test_redis):
    # 1. Ingest article
    article = await article_service.create(test_db, {
        "title": "Major Competitor Launches AI Feature",
        "url": "https://test-source.com/article-1",
        "content": SAMPLE_ARTICLE_CONTENT,
        "source_id": "test-source-1"
    })

    # 2. Run signal detection (with real LLM or mock)
    with patch_openai_for_testing():
        signals = await signal_detection_service.process_article(test_db, article.id)

    # 3. Verify signals created
    assert len(signals) >= 1
    assert signals[0].article_id == article.id
    assert signals[0].tier in ["A", "B", "C", "D"]

    # 4. Run insight generation
    with patch_openai_for_testing():
        insights = await insight_service.generate_from_signals(test_db, [s.id for s in signals])

    assert len(insights) >= 1
```

### 2.2 API → Database Integration

```python
@pytest.mark.asyncio
async def test_create_signal_persists_to_db(client, auth_headers, test_db):
    response = await client.post("/api/v1/signals", headers=auth_headers, json={
        "article_id": "art_test_1",
        "signal_type": "competitive_move",
        "summary": "Test signal",
        "confidence": 0.85,
        "tier": "A"
    })

    assert response.status_code == 201
    signal_id = response.json()["id"]

    # Verify in DB
    signal = await test_db.get(Signal, signal_id)
    assert signal is not None
    assert signal.tier == "A"
```

### 2.3 n8n → FastAPI Webhook Flow

```python
@pytest.mark.asyncio
async def test_n8n_webhook_triggers_processing(client, test_db):
    webhook_payload = {
        "workflow": "content_collection",
        "articles": [{"url": "https://test.com/1", "title": "Test", "content": "..."}]
    }

    response = await client.post(
        "/api/v1/webhooks/n8n/collection-complete",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json=webhook_payload
    )

    assert response.status_code == 202  # Accepted for processing

    # Wait for async processing
    await asyncio.sleep(1)

    # Verify articles were created
    articles = await article_service.list_recent(test_db, limit=10)
    assert any(a.url == "https://test.com/1" for a in articles)

@pytest.mark.asyncio
async def test_n8n_webhook_rejects_invalid_secret(client):
    response = await client.post(
        "/api/v1/webhooks/n8n/collection-complete",
        headers={"X-Webhook-Secret": "wrong-secret"},
        json={}
    )
    assert response.status_code == 401
```

### 2.4 Auth Flow (Clerk JWT Validation)

```python
@pytest.mark.asyncio
async def test_valid_clerk_jwt_accepted(client):
    # Generate a test JWT with known Clerk test keys
    test_token = generate_test_clerk_jwt(
        user_id="user_test_123",
        role="analyst"
    )

    response = await client.get(
        "/api/v1/signals",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_expired_jwt_rejected(client):
    expired_token = generate_test_clerk_jwt(
        user_id="user_test_123",
        expired=True
    )

    response = await client.get(
        "/api/v1/signals",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_insufficient_role_rejected(client):
    viewer_token = generate_test_clerk_jwt(role="viewer")

    response = await client.post(
        "/api/v1/signals/sig_123/approve",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert response.status_code == 403
```

---

## 3. End-to-End Tests (Playwright)

**Location:** `frontend/tests/e2e/`
**Run:** `npx playwright test`
**Environment:** Staging environment (not production)

### 3.1 User Journey: Search → Signal → Insight

```typescript
// tests/e2e/search-to-insight.spec.ts
import { test, expect } from '@playwright/test'

test('user can search for signals and view insight', async ({ page }) => {
  // Sign in
  await page.goto('/sign-in')
  await page.fill('[name="email"]', process.env.TEST_USER_EMAIL!)
  await page.fill('[name="password"]', process.env.TEST_USER_PASSWORD!)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL('/dashboard')

  // Navigate to search
  await page.click('[data-testid="nav-search"]')

  // Perform search
  await page.fill('[data-testid="search-input"]', 'competitive AI launch')
  await page.press('[data-testid="search-input"]', 'Enter')

  // Verify results
  await expect(page.locator('[data-testid="signal-card"]')).toHaveCount({ minimum: 1 })

  // Click first signal
  await page.click('[data-testid="signal-card"]:first-child')

  // Verify insight panel opens
  await expect(page.locator('[data-testid="insight-panel"]')).toBeVisible()
  await expect(page.locator('[data-testid="insight-body"]')).not.toBeEmpty()
})
```

### 3.2 Review Workflow: Draft → Review → Approve

```typescript
test('analyst can create and reviewer can approve content idea', async ({ browser }) => {
  // Analyst creates content idea
  const analystPage = await browser.newPage()
  await signIn(analystPage, 'analyst')

  await analystPage.goto('/content-strategy')
  await analystPage.click('[data-testid="create-idea-btn"]')
  await analystPage.fill('[data-testid="idea-title"]', 'Blog Post: AI in Content Marketing')
  await analystPage.fill('[data-testid="idea-body"]', 'Based on recent signals...')
  await analystPage.click('[data-testid="submit-for-review-btn"]')

  await expect(analystPage.locator('[data-testid="success-toast"]')).toBeVisible()

  // Reviewer approves
  const reviewerPage = await browser.newPage()
  await signIn(reviewerPage, 'reviewer')

  await reviewerPage.goto('/review-queue')
  await expect(reviewerPage.locator('[data-testid="queue-item"]')).toHaveCount({ minimum: 1 })

  await reviewerPage.click('[data-testid="queue-item"]:first-child [data-testid="approve-btn"]')
  await reviewerPage.fill('[data-testid="review-notes"]', 'Approved — strong signal basis')
  await reviewerPage.click('[data-testid="confirm-approve-btn"]')

  await expect(reviewerPage.locator('[data-testid="success-toast"]')).toContainText('Approved')
})
```

### 3.3 Executive Briefing View

```typescript
test('executive can view daily briefing', async ({ page }) => {
  await signIn(page, 'viewer')
  await page.goto('/executive-portal')

  await expect(page.locator('[data-testid="briefing-header"]')).toBeVisible()
  await expect(page.locator('[data-testid="top-signals"]')).toHaveCount({ minimum: 3 })
  await expect(page.locator('[data-testid="briefing-date"]'))
    .toContainText(new Date().toLocaleDateString())
})
```

---

## 4. AI Output Testing

### 4.1 Golden Set Evaluation

Maintain a curated set of articles with known expected outputs:

```python
# tests/ai/golden_set/
# golden_articles.json — 50 labeled articles
# Expected: signal_type, tier, confidence_range, key_entities

@pytest.mark.parametrize("article,expected", load_golden_set())
@pytest.mark.asyncio
async def test_signal_detection_golden_set(article, expected):
    result = await signal_detection_agent.run(article["content"])

    # Check signal type matches
    assert result["signals"][0]["type"] == expected["signal_type"]

    # Check tier is within expected range
    assert result["signals"][0]["tier"] in expected["acceptable_tiers"]

    # Check confidence within range
    confidence = result["signals"][0]["confidence"]
    assert expected["confidence_min"] <= confidence <= expected["confidence_max"]
```

Run golden set tests weekly (not on every PR — too expensive):

```yaml
# .github/workflows/ai-golden-set.yml
on:
  schedule:
    - cron: '0 6 * * 0'  # Weekly Sunday 06:00 UTC
```

### 4.2 Prompt Regression Testing

Detect when prompt changes degrade output quality:

```python
# tests/ai/test_prompt_regression.py
REGRESSION_THRESHOLD = 0.85  # 85% accuracy on golden set

@pytest.mark.asyncio
async def test_signal_extraction_accuracy_above_threshold():
    golden_set = load_golden_set()
    correct = 0

    for article, expected in golden_set:
        result = await signal_extraction_node(article)
        if is_correct_signal(result, expected):
            correct += 1

    accuracy = correct / len(golden_set)
    assert accuracy >= REGRESSION_THRESHOLD, (
        f"Signal extraction accuracy {accuracy:.1%} below threshold {REGRESSION_THRESHOLD:.1%}"
    )
```

### 4.3 Output Schema Validation

All LLM outputs are validated against Pydantic schemas before use:

```python
from pydantic import BaseModel, ValidationError

class SignalExtractionOutput(BaseModel):
    signals: list[SignalItem]
    confidence: float
    processing_notes: Optional[str]

async def extract_signals_with_validation(article: str) -> SignalExtractionOutput:
    raw_output = await llm.ainvoke(signal_prompt.format(article=article))

    try:
        return SignalExtractionOutput.model_validate_json(raw_output.content)
    except ValidationError as e:
        logger.error("LLM output failed schema validation", error=str(e))
        # Retry with repair prompt
        return await extract_signals_with_repair(article, raw_output.content, e)
```

---

## 5. Load Testing (k6)

**Location:** `tests/load/`
**Run:** `k6 run tests/load/api-load.js`

### 5.1 API Endpoints Under Load

```javascript
// tests/load/api-load.js
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate } from 'k6/metrics'

const errorRate = new Rate('errors')

export const options = {
  stages: [
    { duration: '2m', target: 20 },   // Ramp up to 20 users
    { duration: '5m', target: 20 },   // Stay at 20 users
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests under 500ms
    errors: ['rate<0.01'],             // Error rate below 1%
  },
}

const BASE_URL = __ENV.API_URL || 'https://api-staging.tada-intelligence.com'
const AUTH_TOKEN = __ENV.TEST_AUTH_TOKEN

export default function () {
  // Simulate typical user behavior
  const responses = http.batch([
    ['GET', `${BASE_URL}/api/v1/signals?limit=20`, null, { headers: { Authorization: `Bearer ${AUTH_TOKEN}` }}],
    ['GET', `${BASE_URL}/api/v1/dashboard/executive`, null, { headers: { Authorization: `Bearer ${AUTH_TOKEN}` }}],
  ])

  responses.forEach(res => {
    errorRate.add(res.status >= 400)
    check(res, { 'status is 200': (r) => r.status === 200 })
  })

  sleep(1)
}
```

### 5.2 Search Performance at Volume

```javascript
// tests/load/search-load.js
export const options = {
  vus: 20,
  duration: '5m',
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // Semantic search under 2s at p95
  },
}

const QUERIES = [
  'AI product launch competitor',
  'regulatory change compliance',
  'market expansion opportunity',
  'customer churn risk signals',
]

export default function () {
  const query = QUERIES[Math.floor(Math.random() * QUERIES.length)]

  const res = http.post(
    `${BASE_URL}/api/v1/search`,
    JSON.stringify({ query, mode: 'hybrid', limit: 20 }),
    { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${AUTH_TOKEN}` }}
  )

  check(res, {
    'search returns results': (r) => r.json('results').length > 0,
    'search under 2s': (r) => r.timings.duration < 2000,
  })

  sleep(2)
}
```

### 5.3 Concurrent Review Submissions

```javascript
// tests/load/review-load.js
export const options = {
  vus: 10,  // 10 concurrent reviewers
  duration: '3m',
}

export default function () {
  // Submit a review
  const res = http.patch(
    `${BASE_URL}/api/v1/reviews/${TEST_REVIEW_ID}`,
    JSON.stringify({ status: 'approved', notes: 'Load test review' }),
    { headers: authHeaders }
  )

  check(res, {
    'review submitted successfully': (r) => r.status === 200,
    'no conflicts': (r) => r.status !== 409,
  })

  sleep(5)
}
```

---

## 6. Test Environment

### 6.1 Staging Environment Configuration

Staging mirrors production but uses:
- Separate Railway project: `tada-staging`
- Separate Clerk application (staging keys)
- Separate Supabase project (staging data)
- Test OpenAI API key with lower rate limits
- Real LangGraph agents with `test_mode=true` flag (skip expensive LLM calls for most tests)

### 6.2 Test Data Fixtures

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def db_with_articles(test_db: AsyncSession) -> AsyncSession:
    """Populate test DB with 20 sample articles across 5 sources."""
    articles = [create_test_article(i) for i in range(20)]
    test_db.add_all(articles)
    await test_db.commit()
    return test_db

@pytest.fixture
async def db_with_signals(db_with_articles: AsyncSession) -> AsyncSession:
    """Add 10 signals derived from test articles."""
    signals = [create_test_signal(i) for i in range(10)]
    db_with_articles.add_all(signals)
    await db_with_articles.commit()
    return db_with_articles
```

### 6.3 CI/CD Pipeline Integration (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_DB: tada_test
          POSTGRES_USER: tada
          POSTGRES_PASSWORD: test
      redis:
        image: redis:7-alpine

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: cd backend && poetry install
      - run: cd backend && poetry run pytest tests/unit/ -v --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - run: cd backend && poetry install
      - run: cd backend && poetry run pytest tests/integration/ -v
        env:
          DATABASE_URL: postgresql+asyncpg://tada:test@localhost:5432/tada_test
          REDIS_URL: redis://localhost:6379
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY_TEST }}

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '18' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run type-check
```

**E2E tests run nightly (not on PRs) against staging:**

```yaml
# .github/workflows/e2e-nightly.yml
on:
  schedule:
    - cron: '0 3 * * *'  # 3am UTC nightly

jobs:
  playwright:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci && npx playwright install
      - run: cd frontend && npx playwright test
        env:
          BASE_URL: https://app-staging.tada-intelligence.com
          TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
```

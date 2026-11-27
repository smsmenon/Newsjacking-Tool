const state = {
  view: "digest",
  digest: null,
  sources: [],
  weekly: null,
  reviews: [],
};

const titles = {
  digest: ["Daily Digest", "Supply chain signals translated into Detect, Decide, Do."],
  signals: ["Signals", "Evidence, scoring, and TADA perspective for surfaced developments."],
  review: ["Review Queue", "Draft intelligence remains human-reviewed before use."],
  sources: ["Sources", "Approved source coverage and monitoring posture."],
  weekly: ["Weekly Report", "Strategic synthesis for leadership, sales, and marketing."],
};

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function metric(label, value) {
  return `<div class="metric"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`;
}

function renderMetrics() {
  const items = state.digest?.top_signals || [];
  const avg = items.length
    ? (items.reduce((sum, item) => sum + item.signal.score.final_score, 0) / items.length).toFixed(2)
    : "0.00";
  const risks = state.digest?.top_risks?.length || 0;
  document.getElementById("metrics").innerHTML = [
    metric("Surfaced signals", items.length),
    metric("Average score", avg),
    metric("Emerging themes", state.digest?.emerging_themes?.length || 0),
    metric("Data mode", state.digest?.data_mode || "sample"),
  ].join("");
}

function renderDigest() {
  const items = state.digest?.top_signals || [];
  return `
    <div class="stack">
      ${items.map((item) => `
        <article class="panel">
          <div class="split">
            <div>
              <h2>${esc(item.signal.headline)}</h2>
              <p class="muted">${esc(item.signal.source)} · ${esc(item.signal.signal_type)} · <span class="score">${esc(item.signal.score.final_score)}</span></p>
              <p style="margin-top:12px">${esc(item.signal.summary)}</p>
              <div class="tag-row">${item.signal.keywords.map((kw) => `<span class="tag">${esc(kw)}</span>`).join("")}</div>
            </div>
            <div>
              <h3>Suggested Action</h3>
              <p>${esc(item.suggested_action)}</p>
              <h3 style="margin-top:16px">Review Status</h3>
              <p class="status">${esc(item.content_opportunity.review_status)}</p>
            </div>
          </div>
        </article>
      `).join("")}
    </div>
  `;
}

function renderSignals() {
  const rows = (state.digest?.top_signals || []).map((item) => `
    <tr>
      <td><strong>${esc(item.signal.headline)}</strong><br><span class="muted">${esc(item.signal.evidence)}</span></td>
      <td>${esc(item.signal.signal_type)}</td>
      <td class="score">${esc(item.signal.score.final_score)}</td>
      <td>${esc(item.tada_perspective.detect)}<br><br>${esc(item.tada_perspective.decide)}<br><br>${esc(item.tada_perspective.do)}</td>
    </tr>
  `).join("");
  return `
    <table class="table">
      <thead><tr><th>Signal</th><th>Type</th><th>Score</th><th>Detect / Decide / Do</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderReview() {
  const items = state.digest?.top_signals || [];
  return `
    <div class="stack">
      ${items.map((item, index) => `
        <div class="panel">
          <h2>${esc(item.content_opportunity.thought_leadership_article.title)}</h2>
          <p class="muted">${esc(item.signal.headline)}</p>
          <p style="margin-top:12px">${esc(item.content_opportunity.thought_leadership_article.executive_summary)}</p>
          <div class="tag-row">
            <button class="secondary" onclick="recordReview(${index}, 'under_review')">Send to review</button>
            <button class="primary" onclick="recordReview(${index}, 'approved')">Approve</button>
            <button class="secondary" onclick="recordReview(${index}, 'rejected')">Reject</button>
          </div>
        </div>
      `).join("")}
      <div class="panel">
        <h2>Review Events</h2>
        <table class="table">
          <thead><tr><th>Status</th><th>Reviewer</th><th>Comments</th><th>Time</th></tr></thead>
          <tbody>${state.reviews.map((event) => `
            <tr><td>${esc(event.to_status)}</td><td>${esc(event.reviewer)}</td><td>${esc(event.comments)}</td><td>${esc(event.created_at)}</td></tr>
          `).join("")}</tbody>
        </table>
      </div>
    </div>
  `;
}

function renderSources() {
  return `
    <table class="table">
      <thead><tr><th>Source</th><th>Category</th><th>Access</th><th>Priority</th><th>Status</th></tr></thead>
      <tbody>${state.sources.map((source) => `
        <tr>
          <td><strong>${esc(source.name)}</strong><br><span class="muted">${esc(source.url)}</span></td>
          <td>${esc(source.category)}</td>
          <td>${esc(source.access_method)}</td>
          <td>${esc(source.priority)}</td>
          <td>${esc(source.health_status)}</td>
        </tr>
      `).join("")}</tbody>
    </table>
  `;
}

function renderWeekly() {
  const report = state.weekly || {};
  return `
    <div class="stack">
      <div class="panel">
        <h2>${esc(report.title)}</h2>
        <p>${esc(report.market_overview)}</p>
      </div>
      <div class="split">
        <div class="panel">
          <h3>Strategic Recommendations</h3>
          <ul>${(report.strategic_recommendations || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
        </div>
        <div class="panel">
          <h3>Metrics</h3>
          <p>Surfaced signals: <strong>${esc(report.metrics?.surfaced_signals || 0)}</strong></p>
          <p>Average score: <strong>${esc(report.metrics?.average_score || 0)}</strong></p>
        </div>
      </div>
      <div class="panel">
        <h3>Leadership Talking Points</h3>
        <ul>${(report.leadership_talking_points || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      </div>
    </div>
  `;
}

function render() {
  const [title, subtitle] = titles[state.view];
  document.getElementById("page-title").textContent = title;
  document.getElementById("page-subtitle").textContent = subtitle;
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.view);
  });
  renderMetrics();
  const renderers = { digest: renderDigest, signals: renderSignals, review: renderReview, sources: renderSources, weekly: renderWeekly };
  document.getElementById("view").innerHTML = renderers[state.view]();
}

async function recordReview(index, status) {
  const item = state.digest.top_signals[index];
  await api("/api/review-events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      entity_type: "content_opportunity",
      entity_id: item.signal.url,
      from_status: item.content_opportunity.review_status,
      to_status: status,
      reviewer: "local-reviewer@tada.example",
      comments: `${status} from dashboard`,
    }),
  });
  state.reviews = (await api("/api/review-events")).events;
  render();
}

async function load() {
  const [digest, sources, weekly, reviewEvents] = await Promise.all([
    api("/api/digest"),
    api("/api/sources"),
    api("/api/reports/weekly"),
    api("/api/review-events"),
  ]);
  state.digest = digest;
  state.sources = sources.sources;
  state.weekly = weekly;
  state.reviews = reviewEvents.events;
  render();
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    render();
  });
});

document.getElementById("refresh-btn").addEventListener("click", async () => {
  state.digest = await api("/api/ingestion/run", { method: "POST" });
  state.weekly = await api("/api/reports/weekly");
  render();
});

document.getElementById("live-btn").addEventListener("click", async () => {
  state.digest = await api("/api/ingestion/live", { method: "POST" });
  state.weekly = await api("/api/reports/weekly");
  render();
});

load().catch((error) => {
  document.getElementById("view").innerHTML = `<div class="panel risk">${esc(error.message)}</div>`;
});

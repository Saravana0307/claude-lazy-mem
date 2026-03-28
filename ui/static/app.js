/* claude-lazy-mem dashboard app.js */

let currentDays = 7;
let sessionDays = 7;
let sessionsChart = null;
let savingsChart = null;

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  await Promise.all([
    loadMode(),
    loadSummary(),
    loadCharts(currentDays),
    loadProjects(),
    loadSessions(sessionDays),
    loadHealth(),
  ]);
});

// ─── Mode Toggle ─────────────────────────────────────────────────────────────

async function loadMode() {
  const res = await fetch("/api/mode");
  const { mode } = await res.json();
  updateModeUI(mode);
}

function updateModeUI(mode) {
  const btn = document.getElementById("mode-btn");
  const text = document.getElementById("mode-text");
  const hint = document.getElementById("mode-hint");

  text.textContent = mode.toUpperCase();
  btn.className = `mode-btn ${mode}`;
  hint.textContent = mode === "lazy"
    ? "Context loads on request"
    : "Context auto-loads at session start";
}

async function toggleMode() {
  const res = await fetch("/api/mode");
  const { mode } = await res.json();
  const newMode = mode === "lazy" ? "full" : "lazy";

  await fetch("/api/mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: newMode }),
  });

  updateModeUI(newMode);
}

// ─── Summary Cards ────────────────────────────────────────────────────────────

async function loadSummary() {
  const d = await fetch("/api/summary").then(r => r.json());

  setText("total-sessions", d.total.toLocaleString());
  setText("lazy-sessions", d.lazy.toLocaleString());
  setText("lazy-pct", `${d.lazy_pct}% of total`);
  setText("tokens-saved", formatTokens(d.tokens_saved));
  setText("ctx-size", `est. context: ~${formatTokens(d.estimated_context_size)}`);
  setText("cost-saved", `$${d.cost_saved.toFixed(4)}`);
}

// ─── Charts ───────────────────────────────────────────────────────────────────

async function loadCharts(days) {
  const data = await fetch(`/api/daily?days=${days}`).then(r => r.json());

  const labels = data.map(d => formatDate(d.date));
  const lazyCounts = data.map(d => d.lazy_count || 0);
  const fullCounts = data.map(d => d.full_count || 0);

  // Cumulative savings (estimate: 25k tokens per lazy session)
  let cum = 0;
  const cumulativeSavings = lazyCounts.map(v => { cum += v * 25000; return cum; });

  renderSessionsChart(labels, lazyCounts, fullCounts);
  renderSavingsChart(labels, cumulativeSavings);
}

function renderSessionsChart(labels, lazyData, fullData) {
  const ctx = document.getElementById("sessions-chart").getContext("2d");
  if (sessionsChart) sessionsChart.destroy();

  sessionsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Lazy",
          data: lazyData,
          backgroundColor: "rgba(108, 142, 245, 0.7)",
          borderRadius: 4,
        },
        {
          label: "Full",
          data: fullData,
          backgroundColor: "rgba(251, 191, 36, 0.6)",
          borderRadius: 4,
        },
      ],
    },
    options: chartOptions({ stacked: true }),
  });
}

function renderSavingsChart(labels, cumulativeData) {
  const ctx = document.getElementById("savings-chart").getContext("2d");
  if (savingsChart) savingsChart.destroy();

  savingsChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Tokens Saved",
          data: cumulativeData,
          borderColor: "rgba(74, 222, 128, 0.9)",
          backgroundColor: "rgba(74, 222, 128, 0.08)",
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
      ],
    },
    options: chartOptions({ yCallback: v => formatTokens(v) }),
  });
}

function chartOptions({ stacked = false, yCallback = null } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: { color: "#7a7f9a", font: { size: 12 } },
        position: "bottom",
      },
      tooltip: {
        backgroundColor: "#22263a",
        borderColor: "#2e3347",
        borderWidth: 1,
        titleColor: "#e8eaf0",
        bodyColor: "#7a7f9a",
      },
    },
    scales: {
      x: {
        stacked,
        grid: { color: "#2e3347" },
        ticks: { color: "#7a7f9a", font: { size: 11 } },
      },
      y: {
        stacked,
        grid: { color: "#2e3347" },
        ticks: {
          color: "#7a7f9a",
          font: { size: 11 },
          callback: yCallback || (v => v),
        },
      },
    },
  };
}

async function setDays(days, btn) {
  currentDays = days;
  document.querySelectorAll(".chart-card .filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  await loadCharts(days);
}

// ─── Projects Table ───────────────────────────────────────────────────────────

async function loadProjects() {
  const projects = await fetch("/api/projects").then(r => r.json());
  const tbody = document.getElementById("projects-body");

  if (!projects.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty">No session data yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = projects.map(p => {
    const pct = p.total ? Math.round(p.lazy / p.total * 100) : 0;
    return `<tr>
      <td>${esc(p.project)}</td>
      <td>${p.total.toLocaleString()}</td>
      <td>${pct}%</td>
      <td>~${formatTokens(p.avg_context_size)}</td>
      <td>${formatTokens(p.tokens_saved)}</td>
      <td>$${p.cost_saved.toFixed(4)}</td>
    </tr>`;
  }).join("");
}

// ─── Sessions Table ───────────────────────────────────────────────────────────

async function loadSessions(days) {
  const sessions = await fetch(`/api/sessions?days=${days}`).then(r => r.json());
  const tbody = document.getElementById("sessions-body");

  if (!sessions.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">No sessions in this period.</td></tr>`;
    return;
  }

  tbody.innerHTML = sessions.map(s => `<tr>
    <td>${formatDateTime(s.started_at)}</td>
    <td>${esc(s.project || "—")}</td>
    <td><span class="badge ${s.mode}">${s.mode || "—"}</span></td>
    <td>${s.input_tokens != null ? s.input_tokens.toLocaleString() : "—"}</td>
    <td>${s.output_tokens != null ? s.output_tokens.toLocaleString() : "—"}</td>
    <td>${s.model ? s.model.replace("claude-", "") : "—"}</td>
    <td>${s.cost != null ? "$" + s.cost.toFixed(4) : "—"}</td>
  </tr>`).join("");
}

async function setSessionDays(days, btn) {
  sessionDays = days;
  document.querySelectorAll(".sessions-section .filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  await loadSessions(days === 90 ? 365 : days);
}

// ─── Health ───────────────────────────────────────────────────────────────────

async function loadHealth() {
  const h = await fetch("/api/health").then(r => r.json());
  const el = document.getElementById("health-content");

  if (h.patched) {
    el.innerHTML = `<div class="health-ok">✓ hooks.json patched — context gate is active</div>`;
  } else {
    el.innerHTML = `<div class="health-warn">
      ⚠ hooks.json patch missing — plugin may have updated.<br>
      Run: <code>lazy-mem doctor</code> then <code>bash ~/.claude/hooks/patch-mem-hooks.sh</code>
    </div>`;
  }
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function formatTokens(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "k";
  return String(n || 0);
}

function formatDate(str) {
  if (!str) return "";
  const d = new Date(str);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatDateTime(str) {
  if (!str) return "—";
  const d = new Date(str);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
    " " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

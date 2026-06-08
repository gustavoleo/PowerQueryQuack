// Power Query Quack — beta web UI (Phase 6).
// Dependency-free: vanilla fetch + DOM, so the beta stays cheap to run.

const $ = (id) => document.getElementById(id);
let lastReport = null;

async function loadMeta() {
  try {
    const meta = await (await fetch("/meta")).json();
    fillSelect($("language"), meta.languages, meta.defaults.language);
    fillSelect($("runtime"), meta.target_runtimes, meta.defaults.target_runtime);
  } catch (err) {
    console.warn("pqquack: /meta unavailable", err);
  }
}

function fillSelect(select, values, selected) {
  select.innerHTML = "";
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    if (v === selected) opt.selected = true;
    select.appendChild(opt);
  }
}

$("file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (file) $("source").value = await file.text();
});

$("convert").addEventListener("click", async () => {
  const text = $("source").value.trim();
  if (!text) {
    alert("Please paste some Power Query first.");
    return;
  }
  $("convert").disabled = true;
  $("convert").textContent = "Converting…";
  try {
    const res = await fetch("/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        target_runtime: $("runtime").value,
        language: $("language").value,
      }),
    });
    const data = await res.json();
    if (data.error) {
      alert(data.error);
      return;
    }
    lastReport = data;
    renderReport(data);
  } catch (err) {
    alert("Conversion failed: " + err);
  } finally {
    $("convert").disabled = false;
    $("convert").textContent = "Convert →";
  }
});

function renderReport(data) {
  $("results").hidden = false;
  $("feedback").hidden = false;

  const ready = data.production_ready;
  const conf = data.confidence_percent;
  $("status-bar").innerHTML =
    `<span class="badge ${ready ? "ok" : "warn"}">` +
    `${ready ? "Production-ready" : "Review needed"}</span>` +
    `<span class="badge">Validation: ${data.validation_overall}</span>` +
    `<span class="badge">Confidence: ${conf != null ? conf.toFixed(1) + "%" : "—"}</span>`;

  const report = $("report");
  report.innerHTML = "";
  data.sections.forEach((sec, i) => {
    const wrap = document.createElement("details");
    wrap.open = i < 1 || sec.title.toLowerCase().includes("sql");
    const summary = document.createElement("summary");
    summary.textContent = `${i + 1}. ${sec.title}`;
    wrap.appendChild(summary);

    const body = document.createElement("div");
    body.className = "section-body";
    const sql = extractSql(sec.body);
    if (sql !== null) {
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = sql;
      pre.appendChild(code);
      body.appendChild(pre);
    } else {
      const pre = document.createElement("pre");
      pre.className = "plain";
      pre.textContent = sec.body;
      body.appendChild(pre);
    }
    wrap.appendChild(body);
    report.appendChild(wrap);
  });
  $("results").scrollIntoView({ behavior: "smooth" });
}

function extractSql(body) {
  const m = body.match(/```sql\n([\s\S]*?)```/);
  return m ? m[1].trim() : null;
}

document.querySelectorAll(".feedback-buttons button").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const verdict = btn.dataset.verdict;
    try {
      const res = await fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verdict,
          language: $("language").value,
          target_runtime: $("runtime").value,
          sql_summary: lastReport ? lastReport.sql.slice(0, 200) : "",
        }),
      });
      const data = await res.json();
      const ack = $("feedback-ack");
      ack.hidden = false;
      ack.textContent = `Thanks! Feedback recorded (id: ${data.conversion_id.slice(0, 8)}…).`;
    } catch (err) {
      console.warn("feedback failed", err);
    }
  });
});

document.addEventListener("DOMContentLoaded", loadMeta);

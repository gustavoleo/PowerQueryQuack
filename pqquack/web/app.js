// Power Query Quack — beta web UI (Phase 0 placeholder).
//
// Phase 6 wires the Upload / Settings / Results / Feedback areas to the API:
//   - GET  /meta     -> populate settings (languages, runtimes, output modes)
//   - POST /convert  -> render the 10-section conversion output
//   - POST /feedback -> submit 👍 / 👎 / 🛠
//
// Kept intentionally dependency-free so the beta stays cheap to run.

async function loadMeta() {
  try {
    const res = await fetch("/meta");
    if (!res.ok) return;
    const meta = await res.json();
    console.info("pqquack meta:", meta);
  } catch (err) {
    console.warn("pqquack: /meta not available yet", err);
  }
}

document.addEventListener("DOMContentLoaded", loadMeta);

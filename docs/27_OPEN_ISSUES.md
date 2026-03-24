# Agent-0: Open Issues (as of 2026-03-16)

## Critical — FIXED

### 1. ~~Ping system doesn't deliver~~ FIXED
**Fix:** Replaced SQLite-based ping delivery with in-memory thread-safe queue (`threading.Lock` + list) in `BriefingSystem`. The `add_ping()` writes to both in-memory queue (primary) and DB (backup log). `_get_pending_pings()` reads from in-memory queue, bypassing SQLite thread visibility entirely.

### 2. ~~Scan results not queryable by LLM~~ FIXED
**Fix:** Scan summary (counts + top 10 findings) now written to `state/current.md` under "## Latest Scan Results" section. System prompt includes a SCAN RESULTS section with the summary injected directly. Both `/scan` API endpoint and onboarding write the summary. Watcher preserves scan section when updating state.

### 3. ~~Stale knowledge from docs~~ FIXED
**Fix:** During onboarding synthesis, scan results are cross-referenced against doc-mentioned bugs. The LLM prompt explicitly instructs: "If documentation mentions a bug but the scan did NOT find it, that bug is likely ALREADY FIXED." Doc reading phase already marks FIXED/DONE/RESOLVED items correctly.

## Medium

### 4. Tauri project switching unreliable
Works sometimes, fails sometimes. Multiple Python processes accumulate. The `taskkill /F /T` approach is brittle.
**Fix needed:** More robust process management — PID file, port checking before start.

### 5. Third-party code in scan results
Semgrep/bandit/radon scan llama.cpp, ggml, and other vendored code. Creates noise (most of the 676 findings are in third-party code).
**Fix needed:** Better exclusion of third-party directories. The SKIP_DIRS list needs to be more comprehensive, or use .gitignore patterns.

### 6. Session count keeps growing
17 sessions from restarts during testing. Each restart creates a new session. The auto-close works but the count is noisy.
**Fix needed:** Don't create a new session on every restart. Only create when intent changes or gap > 30 minutes.

## Low

### 7. 206 alerts in DB — too many
The scan created 103+ alerts for HIGH findings. The alerts table is now polluted with scan results alongside real operational alerts. No way to distinguish scan alerts from runtime alerts.
**Fix needed:** Separate scan_findings table or add a source column to alerts.

### 8. code_index.md too large to embed
950KB file can't be embedded for vector search. Only searchable via raw grep.
**Not a problem for now** — grep search works fine for this file.

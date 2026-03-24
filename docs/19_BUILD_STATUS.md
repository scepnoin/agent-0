# Agent-0: Build Status

## Last Updated: 2026-03-14

## Architecture

```
Agent-0.exe (Tauri, 11MB)
  │ Opens native window → loading screen → connects to backend
  │ Auto-launches Python backend as hidden subprocess
  │
  ▼
Python Backend (Flask on localhost:7800)
  ├── ReACT Loop (15 tools, Gemini 2.5 Flash)
  ├── File Watcher (watchfiles, debouncing)
  ├── Memory System (SQLite + markdown + hybrid search)
  ├── Reasoning Engine (drift, patterns, debt, gospels, sessions)
  ├── MCP Server (localhost:7801)
  └── Knowledge stored in AppData/Local/Agent0/projects/
```

## Completed Items

### Core System
- [x] Config system with AppData storage + global/project separation
- [x] .agent0.json marker in project root
- [x] SQLite database (9 tables, WAL mode)
- [x] 15 tools (all registered, all working)
- [x] ReACT loop (think → act → observe → done)
- [x] System prompt with dynamic context injection
- [x] LLM client (Google Gemini + Anthropic + OpenAI)
- [x] Gemini embedding-001 (free tier)
- [x] Markdown knowledge store (read/write/append/split)
- [x] Knowledge indexer (chunk by heading, embed, index)
- [x] Hybrid search (vector + FTS5 + RRF fusion, sqlite-vec optional)
- [x] File watcher with debouncing + bulk detection
- [x] Flask API (12 endpoints)
- [x] MCP server (4 tools)
- [x] 5-phase onboarding with write-as-you-go
- [x] Logging (console + file in AppData)

### Reasoning Engine (reasoning/reasoning.py)
- [x] Drift detection (tracks consecutive unrelated changes vs phase goal)
- [x] Pattern matching (file history, category patterns, knowledge patterns)
- [x] Debt tracking (detects patches/workarounds, maintains ledger)
- [x] Session management (start/end, intent vs outcome, drift score)
- [x] Gospel auto-creation (agent gospels with confidence levels)
- [x] Gospel confidence adjustment (up on confirm, down on dismiss, auto-retire)
- [x] Dependency gospel detection (auto-detects co-changing files)
- [x] Auto-checkpoint scheduling (based on strictness mode)
- [x] Cost tracking (per-model, monthly budget, warnings)
- [x] Strictness mode behavior (strict/normal/loose thresholds)

### LLM Client
- [x] Multi-provider (Google Gemini, Anthropic Claude, OpenAI)
- [x] Tiered model strategy (fast/mid/smart with auto-selection)
- [x] Retry with exponential backoff (3 attempts: 2s, 5s, 15s)
- [x] Error recovery (returns error text instead of crashing)
- [x] Embedding client (Gemini embedding-001, free tier)

### Desktop App
- [x] Tauri .exe (11MB, native window, no terminal)
- [x] Auto-launches Python backend as hidden subprocess
- [x] Loading screen with connection retry
- [x] Widget HTML: Dashboard / Query / Knowledge / Settings tabs
- [x] Dashboard: status, project info, knowledge path, activity feed
- [x] Query: chat interface wired to ReACT loop
- [x] Knowledge: browse and view all .md files
- [x] Settings: provider, model, API key, embeddings, strictness, debounce, folder picker

### Open Source Libraries Used
- watchfiles (MIT) — file system monitoring
- sqlite-vec (MIT/Apache 2.0) — SIMD-accelerated vector search (optional, with fallback)
- Flask + flask-cors (BSD) — REST API
- google-generativeai (Apache 2.0) — Gemini LLM + embeddings

## File Counts

| Area | Files | Lines |
|------|-------|-------|
| Python backend | ~36 .py files | ~4,500 |
| Tauri desktop | 5 files (rs, toml, json, html) | ~300 |
| Documentation | 19 .md files | ~3,000 |
| **Total** | **~60 files** | **~7,800** |

## How to Run

### Development (from source)
```bash
cd backend
pip install -r requirements.txt
python main.py --project "C:\path\to\your\project" --no-ui
```

### With Tauri Desktop
```bash
# Start Python backend first
cd backend && python main.py --project "C:\path\to\project" --no-ui &

# Then run Tauri
cd desktop && npx tauri dev
```

### Built .exe
Double-click Agent-0.exe on Desktop. It auto-finds the last project and launches.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Status, project info |
| /state | GET | Current project state |
| /query | POST | Ask Agent-0 a question (ReACT loop) |
| /brief | GET | Handoff brief |
| /gospels | GET | Active gospel rules |
| /alerts | GET | Recent alerts |
| /activity | GET | Activity feed |
| /knowledge | GET | Browse knowledge files |
| /checkpoint | GET | Latest checkpoint |
| /config | GET | Current config (keys masked) |
| /config/save | POST | Update config |
| /config/strictness | POST | Change strictness mode |
| /widget | GET | Widget HTML |

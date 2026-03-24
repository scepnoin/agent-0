# Agent-0: Codebase Structure

## Language Decisions

| Component | Language | Why |
|-----------|----------|-----|
| Core logic, tools, API, watcher, memory | **Python** | All brain logic in one language. Simple, maintainable. |
| Desktop widget backend | **Rust** (Tauri) | Tiny binary, native window, proper desktop program (not a web UI). |
| Desktop widget UI | **HTML/CSS/TypeScript** | Clean widget face. Minimal — just layout, styling, and API calls. |
| Build/distribution | **Shell + Python** | Package everything into one distributable. |

## Why Tauri (Not Electron, Not PyQt)

- **Native desktop program** — not a browser window, not a web UI. Its own program.
- **Tiny binary** — ~5-10MB vs Electron's ~150MB.
- **Open-source ready** — if Agent-0 works and gets released, Tauri is the professional foundation.
- **Modern** — Rust backend, web frontend. Industry standard for lightweight desktop apps.
- **Cross-platform** — Windows, Mac, Linux from same codebase.

## Architecture: Two Processes, One Program

```
┌─────────────────────────────────┐
│  TAURI APP (Desktop Widget)     │
│  - Rust + HTML/CSS/TS           │
│  - Native window, own program   │
│  - Alert display                │
│  - Query input                  │
│  - Status/health dashboard      │
│  - Talks to Python via localhost │
└──────────┬──────────────────────┘
           │ HTTP (localhost)
┌──────────▼──────────────────────┐
│  PYTHON BACKEND (Core)          │
│  - Flask API (localhost)        │
│  - Watcher (watchdog)           │
│  - ReACT loop + 15 tools        │
│  - Memory (SQLite + markdown)   │
│  - LLM client                  │
│  - MCP server                  │
│  - Runs as background service   │
└─────────────────────────────────┘
```

Tauri app launches the Python backend on startup. Two processes under the hood, but the user sees **one program**. Open Agent-0, it's running. Close it, it stops.

## Full Codebase Layout

```
agent-0/
│
├── backend/                            ← PYTHON (the brain)
│   ├── main.py                         → Entry point: starts Flask + watcher
│   ├── config.py                       → Settings, API key, provider, project path
│   ├── requirements.txt                → Python dependencies
│   │
│   ├── agent/                          → Core agent logic
│   │   ├── __init__.py
│   │   ├── loop.py                     → ReACT loop (think → act → observe → repeat)
│   │   ├── system_prompt.py            → System prompt builder with project context
│   │   └── onboarding.py              → First-run deep scan (write-as-you-go)
│   │
│   ├── tools/                          → 15 tools (one file each)
│   │   ├── __init__.py                 → Tool registry + schema definitions
│   │   ├── read_file.py                → Read project files or own knowledge
│   │   ├── read_diff.py                → Read file diffs/changes
│   │   ├── list_files.py               → List directory contents
│   │   ├── search_knowledge.py         → Hybrid search across .agent0/ knowledge
│   │   ├── search_project.py           → Grep/search the actual project codebase
│   │   ├── get_state.py                → Shortcut: current project state
│   │   ├── write_knowledge.py          → Create/append/update knowledge markdown
│   │   ├── db_write.py                 → Insert/update SQLite records
│   │   ├── db_query.py                 → Query SQLite tables
│   │   ├── git_info.py                 → Git log, status, branch, blame, reverts
│   │   ├── check_gospels.py            → Validate against all active gospel rules
│   │   ├── send_alert.py               → Ping user via desktop widget
│   │   ├── log_question.py             → Save questions for human review
│   │   ├── create_checkpoint.py        → Create point-in-time project snapshot
│   │   └── summarize_and_split.py      → Split large markdown files, archive old content
│   │
│   ├── memory/                         → Knowledge system
│   │   ├── __init__.py
│   │   ├── store.py                    → Markdown file operations (read/write/append/split)
│   │   ├── db.py                       → SQLite operations (CRUD, schema, migrations)
│   │   ├── indexer.py                  → Vector embedding + FTS5 indexing
│   │   └── search.py                   → Hybrid search (semantic + keyword fusion)
│   │
│   ├── llm/                            → LLM provider abstraction
│   │   ├── __init__.py
│   │   └── client.py                   → Direct API calls (Anthropic / OpenAI / Google)
│   │
│   ├── watcher/                        → File system monitoring
│   │   ├── __init__.py
│   │   └── watcher.py                  → Watchdog event handler (event-driven, not polling)
│   │
│   ├── api/                            → External interfaces
│   │   ├── __init__.py
│   │   ├── server.py                   → Flask REST API (localhost)
│   │   └── mcp.py                      → MCP server endpoint
│   │
│   └── reasoning/                      → Reasoning helpers
│       ├── __init__.py
│       └── reasoning.py                → Drift detection, pattern matching, debt flagging
│
├── desktop/                            ← TAURI (the face)
│   ├── src-tauri/                      → Rust backend
│   │   ├── Cargo.toml                  → Rust dependencies
│   │   ├── tauri.conf.json             → Window config (size, position, always-on-top)
│   │   └── src/
│   │       └── main.rs                 → Tauri app entry, launches Python backend process
│   │
│   ├── src/                            → Frontend (widget UI)
│   │   ├── index.html                  → Widget layout
│   │   ├── style.css                   → Widget styling (small, clean, minimal)
│   │   └── app.ts                      → Query input, alert display, status indicator,
│   │                                     health dashboard, API calls to Python backend
│   │
│   └── package.json                    → Frontend dependencies (minimal)
│
├── build/                              → Build & distribution
│   ├── build_backend.py                → PyInstaller config (Python → .exe)
│   └── build_all.sh                    → Full build: Tauri + Python → one distributable
│
└── docs/                               → Documentation (what we've been writing)
    ├── 01_VISION.md
    ├── 02_WHAT_IT_DOES.md
    ├── 03_ARCHITECTURE.md
    ├── 04_ONBOARDING.md
    ├── 05_KNOWLEDGE_SYSTEM.md
    ├── 06_INTERFACES.md
    ├── 07_SETUP_FLOW.md
    ├── 08_REACT_LOOP_AND_TOOLS.md
    └── 09_CODEBASE_STRUCTURE.md
```

## Python Dependencies (requirements.txt)

```
# Core
flask                   # REST API
watchdog                # File system monitoring

# Database
sqlite-vec              # Vector similarity search for SQLite
# (sqlite3 and FTS5 are built into Python)

# LLM Providers (user picks one)
anthropic               # Anthropic Claude API
openai                  # OpenAI API
google-generativeai     # Google Gemini API

# Embeddings (via Google Gemini API — no local model, keeps .exe lightweight)
google-generativeai     # Google Gemini Embedding API (free tier, $0.25/M tokens)

# Build
pyinstaller             # Package Python as .exe
```

## Tauri Dependencies

```toml
# Cargo.toml (minimal)
[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

```json
// package.json (minimal)
{
    "dependencies": {},
    "devDependencies": {
        "typescript": "^5.0",
        "@tauri-apps/cli": "^2"
    }
}
```

## File Counts

| Area | Files | Language |
|------|-------|----------|
| Backend core | ~25 .py files | Python |
| Tools | 15 .py files (one per tool) | Python |
| Desktop UI | 3-4 files (html, css, ts, main.rs) | Rust/TS/HTML/CSS |
| Build | 2 files | Python/Shell |
| Docs | 9 .md files | Markdown |
| **Total** | **~55 files** | |

Small. Focused. One file per concern. No bloat.

## Key Design Rules

1. **One tool per file** — each of the 15 tools is its own .py file. Easy to find, easy to modify.
6. **File snapshots for diffs** — watcher maintains file content snapshots to compute real diffs without requiring git.
2. **No frameworks for the agent** — pure Python ReACT loop. No LangChain, no LangGraph.
3. **Flask is just a thin API layer** — it exposes endpoints, nothing more. Logic lives in `agent/` and `tools/`.
4. **Tauri is just the face** — all it does is render the widget UI and call the Python API. No logic in the frontend.
5. **Backend works without the desktop app** — you could run just the Python backend and query it via API/MCP. The Tauri widget is optional.

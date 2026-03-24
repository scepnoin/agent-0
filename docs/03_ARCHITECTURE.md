# Agent-0: Architecture

## Tech Stack

| Layer | Tech | Why |
|-------|------|-----|
| **Backend** | Flask | Lightweight, minimal, Python — perfect for a small always-on service |
| **Database** | SQLite (WAL mode, thread-safe) | Single file, no server, zero config, per-thread connections |
| **Search** | sqlite-vec + FTS5 | Hybrid search: vector similarity (semantic) + full-text (keyword). Same approach as OpenClaw |
| **LLM Access** | Direct API key | User provides their key — Anthropic, OpenAI, or Google. One provider per instance |
| **File Watching** | watchdog (Python) | Event-driven file system monitoring, cross-platform |
| **Knowledge** | Markdown files + SQLite | .md for human-readable knowledge, SQLite for structured retrieval and indexing |
| **Desktop UI** | Lightweight popup widget | Tiny floating window, input field, alert area. (Tauri/PyQt/Electron TBD) |
| **Distribution** | Single .exe | PyInstaller or similar. One file, double-click, go |

## App Structure

```
agent-0/
├── main.py                     → Entry point, starts everything
├── config.py                   → Settings, API key, provider, project path
│
├── watcher/
│   └── watcher.py              → Watchdog file system monitor, event-driven
│
├── analyzer/
│   └── analyzer.py             → Reads diffs, classifies changes
│
├── memory/
│   ├── writer.py               → Writes to markdown files (create, append, split)
│   ├── db.py                   → SQLite operations (insert, update, query)
│   ├── indexer.py              → Vector + FTS5 indexing of all markdown
│   └── search.py               → Hybrid search (semantic + keyword)
│
├── reasoning/
│   └── reasoning.py            → Drift detection, pattern matching, debt flagging
│
├── alerts/
│   └── alerts.py               → Ping system, question log, dismissal tracking
│
├── llm/
│   └── client.py               → Direct API calls to chosen provider
│
├── api/
│   ├── server.py               → Flask API for external agents to query
│   └── mcp.py                  → MCP server endpoint
│
├── ui/
│   └── widget.py               → Desktop popup widget
│
└── requirements.txt
```

## Per-Project Knowledge Structure

Created inside the project folder when Agent-0 bonds to it:

```
<project_folder>/.agent0/
├── agent0.db                   → SQLite: structured data + vector index + FTS5
│
├── gospels/                    → Hard rules, rarely change
│   └── (grows as needed)
│
├── phases/                     → One file per phase, grows naturally
│   └── (grows as needed)
│
├── sessions/                   → Daily / per-session logs
│   └── (grows as needed)
│
├── state/
│   └── current.md              → Always up to date — what's active NOW
│
├── patterns/                   → Recognized recurring patterns
│   └── (grows as needed)
│
├── checkpoints/                → Periodic project snapshots
│   └── (grows as needed)
│
├── debt/
│   └── (grows as needed)
│
└── modules/                    → Per-module understanding (built during onboarding)
    └── (grows as needed)
```

Markdown files grow organically — Agent-0 creates new files as needed, splits large files, and cross-references. The SQLite database indexes ALL markdown content for hybrid retrieval. The markdown is for readability and durability. The DB is for fast retrieval.

## SQLite Schema

```sql
-- Every change observed
CREATE TABLE changes (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    files_changed TEXT NOT NULL,
    diff_summary TEXT,
    category TEXT,          -- feature, bugfix, refactor, patch, test, config
    phase_id INTEGER,
    session_id INTEGER
);

-- Phase tracking
CREATE TABLE phases (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    goal TEXT,
    status TEXT,            -- open, in_progress, closed, abandoned
    opened TEXT,
    closed TEXT,
    summary TEXT
);

-- Gospel rules
CREATE TABLE gospels (
    id INTEGER PRIMARY KEY,
    rule TEXT NOT NULL,
    reason TEXT,
    category TEXT,
    created TEXT,
    last_validated TEXT
);

-- Open items (bugs, debt, untested things)
CREATE TABLE open_items (
    id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    type TEXT,              -- bug, debt, untested, todo
    status TEXT,            -- open, resolved, dismissed
    linked_phase INTEGER,
    created TEXT,
    resolved TEXT
);

-- Session tracking
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    intent TEXT,
    actual_outcome TEXT,
    drift_score REAL
);

-- Alerts sent
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT,              -- drift, pattern, debt, gospel_violation, risk
    dismissed INTEGER DEFAULT 0,
    response TEXT
);

-- Vector + FTS index of all markdown content
CREATE TABLE memory_index (
    id INTEGER PRIMARY KEY,
    source_file TEXT NOT NULL,
    chunk TEXT NOT NULL,
    embedding BLOB,
    updated TEXT
);

-- FTS5 virtual table for keyword search
CREATE VIRTUAL TABLE memory_fts USING fts5(
    source_file, chunk, content=memory_index
);
```

## Data Flow

### On File Change
```
File change detected (watcher.py)
    → analyzer.py reads the diff, classifies it
    → llm/client.py: "what does this change mean in context?"
    → memory/writer.py updates relevant .md files
    → memory/db.py updates SQLite tables
    → memory/indexer.py re-indexes changed .md files
    → reasoning/reasoning.py checks: drift? pattern? debt? gospel violation?
    → alerts/alerts.py pings if needed
    → back to idle
```

### On Query (widget or API/MCP)
```
Query received
    → memory/search.py does hybrid search (vector + FTS5)
    → llm/client.py synthesizes answer from retrieved context
    → returns response to widget or calling agent
```

## Interfaces

### 1. Desktop Mini-Widget
- Small floating window, always visible on desktop
- Input field for queries
- Alert/notification area for pings
- Status indicator (idle / processing / onboarding)
- Minimal — not a full app

### 2. API Endpoint (Flask)
- REST API for external tools to query Agent-0
- Endpoints: /query, /state, /brief, /gospels, /health
- Any tool can hit it: scripts, other agents, CI/CD

### 3. MCP Server
- Model Context Protocol endpoint
- Claude Code, Cursor, or any MCP-compatible tool connects directly
- Working agent can query Agent-0 as part of its tool chain

# Agent-0

**The zeroth agent. The one that exists before any working agent spins up, and persists after they all shut down.**

Agent-0 is a lightweight sentinel that bonds to a single project folder and becomes the sole source of truth for everything that happens in it. It watches every file change, classifies it, builds structured knowledge, and answers any question — for both you and your AI tools.

It does not write code. It does not fix bugs. It **watches, tracks, remembers, reasons, and speaks up**.

---

## The Problem

When a solo developer replaces a team of 5–6 people with agentic tools (Claude Code, Cursor, Codex, etc.), several things break:

| Problem | What Happens |
|---------|-------------|
| **Context death** | Session hits its limit. The understanding of *why* a decision was made evaporates. The next session starts blind. |
| **Rabbit-hole chaining** | A bug leads to another bug, hours lost. The original task goes in undertested. Regressions surface weeks later. |
| **Agent narrow-mindedness** | Agents patch symptoms, not root causes. No one is pushing back. |
| **Documentation sprawl** | 100+ markdown files constantly in flux. Nothing is coherent. Things fall through the cracks. |
| **No institutional memory** | The team's collective knowledge — what failed, what patterns exist, what must never be touched alone — lives nowhere. |

Agent-0 is the **team memory + QA engineer + project manager** a solo dev with an agent stack doesn't have.

---

## What Agent-0 Does

### 1. Watches
Every file save, create, or delete in your project folder triggers Agent-0. It wakes, processes, and goes back to idle — event-driven, not polling. Near-zero resource usage when idle.

### 2. Reads & Classifies
It reads the actual diff of every change — not just "file X was saved". Classifies each change: feature, bugfix, refactor, patch, test, config. Understands which modules are coupled. Knows which paths are critical vs. low-risk.

### 3. Reasons
Simple, reliable pattern matching — not deep reasoning chains:
- **Drift detection** — "You've been off your stated goal for 45 minutes"
- **Pattern recognition** — "This looks like what caused the regression 3 weeks ago"
- **Dependency awareness** — "You changed module X but module Y imports it"
- **Debt tracking** — Distinguishes real fixes from patches. Maintains a ledger.
- **Gospel enforcement** — Rules derived from your own code, docs, and history

### 4. Writes (to its own knowledge system)
Agent-0 writes constantly — but only to its own `agent-0/` folder, never to your code:
- **Markdown files** — Human-readable, organized by topic. You can open, read, and edit them.
- **SQLite database** — Structured data with vector embeddings + full-text search (FTS5).
- All knowledge is browsable in the desktop widget or queryable via API.

### 5. Alerts
Proactive pings when something matters:
- "You've been off-goal for 45 minutes"
- "This pattern appeared before and led to a regression"
- "You left the last phase open"
- "You changed a file with 155 dependents without running tests"

Strictness modes: **strict** (tight guardrails), **normal** (default), **loose** (just observe).

### 6. Answers
Any question about your project, from you or your AI agent:
- `"What's the current state?"` → structured brief with recent changes, open items, gospel rules
- `"What should I know before changing config.py?"` → dependencies, history, gospel warnings
- `"Brief me on the last session"` → what changed, what's open, what drifted

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Agent-0.exe (Tauri, 11MB)          │
│   Native desktop widget — no terminal needed    │
└────────────────────┬────────────────────────────┘
                     │ spawns
                     ▼
┌─────────────────────────────────────────────────┐
│       Python Backend (Flask, localhost:7800)    │
│                                                 │
│  ┌─────────────┐  ┌──────────────────────────┐ │
│  │  File       │  │  ReACT Loop              │ │
│  │  Watcher    │→ │  Think → Act → Observe   │ │
│  │  (watchfiles│  │  → 17 tools available    │ │
│  │   debounced)│  └──────────────────────────┘ │
│  └─────────────┘              │                 │
│                               ▼                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Memory System                          │   │
│  │  ├── SQLite (9 tables, WAL, FTS5)       │   │
│  │  ├── Vector search (sqlite-vec)         │   │
│  │  └── Markdown knowledge store          │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌──────────────┐  ┌───────────────────────┐   │
│  │  Flask API   │  │  MCP Server           │   │
│  │  :7800       │  │  :7801                │   │
│  └──────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────┘
                     │ writes to
                     ▼
        <your-project>/agent-0/
        ├── agent0.db          ← SQLite knowledge
        ├── gospels/           ← Project rules
        ├── sessions/          ← Session history
        ├── modules/           ← Per-module understanding
        ├── patterns/          ← Recognized patterns
        ├── debt/              ← Technical debt ledger
        ├── state/current.md   ← Live project state
        └── checkpoints/       ← Periodic snapshots
```

**Key design decisions:**
- One Agent-0 instance per project — total isolation, total devotion
- Knowledge stored in `<project>/agent-0/` — visible, browsable, human-editable
- `agent-0/` is automatically added to `.gitignore` — never committed
- API keys stored in system AppData — never in the project folder
- No git dependency — uses file snapshots for real diffs

---

## Quick Start

### Option A: Pre-built Binary (Windows)

Download `Agent-0.exe` from the [Releases](https://github.com/scepnoin/agent-0/releases) page. Double-click to run.

> **Requirements:** Windows 10/11 — no Python, no Node.js needed.

1. Double-click `Agent-0.exe`
2. Select your project folder
3. Enter your API key (Google Gemini recommended — has a free embedding tier)
4. Click **Start** — onboarding begins
5. Agent-0 goes idle and starts watching

On subsequent launches it finds your project automatically and resumes instantly.

---

### Option B: Run from Source

**Requirements:** Python 3.10+, Node.js 18+, Rust toolchain

**1. Clone and set up:**
```bash
git clone https://github.com/scepnoin/agent-0.git
cd agent-0
python scripts/setup.py
```

**2. Run the backend only (headless):**
```bash
# Windows
venv\Scripts\python backend\main.py --project "C:\path\to\your\project"

# macOS/Linux
./venv/bin/python backend/main.py --project /path/to/your/project
```

**3. Run with Tauri desktop (full UI):**
```bash
# Terminal 1 — backend
venv\Scripts\python backend\main.py --project "C:\path\to\project" --no-ui

# Terminal 2 — desktop app
cd desktop
npm install
npx tauri dev
```

**4. Build the .exe yourself:**
```bash
# Build Python backend into an executable
venv\Scripts\pyinstaller backend\main.py --onefile --name agent0-backend

# Build Tauri desktop app
cd desktop
npx tauri build
# Output: desktop/src-tauri/target/release/Agent-0.exe
```

---

## Connecting Your AI Agent (MCP)

Agent-0 exposes itself as an MCP server on `localhost:7801`. Any MCP-compatible tool connects to it directly.

> **Full integration guide:** [`docs/28_WORKING_WITH_AGENT0.md`](docs/28_WORKING_WITH_AGENT0.md)

### Step 1 — Add to your CLAUDE.md (copy-paste this)

Create or update `CLAUDE.md` in your project root:

```markdown
## Agent-0 — Project Oracle

Agent-0 is running and watching this project. It knows everything.
**Always call it first before starting any work.**

MCP server: localhost:7801
REST API: localhost:7800

### Session Start (REQUIRED)
Before doing anything else:
POST http://localhost:7800/brief
Read the response fully — it contains current state, recent changes,
open issues, active gospel rules, and any pending reminders.

### Before Touching Critical Files
POST http://localhost:7800/query
{"question": "What should I know before changing [filename]?"}

### When You Finish a Task
Update ACTIVE_WORK.md with what you did. Agent-0 watches it.
```

### Step 2 — Configure MCP in your tool

**.claude/settings.json:**
```json
{
  "mcpServers": {
    "agent-0": {
      "url": "http://localhost:7801"
    }
  }
}
```

### The 4 MCP Tools

| Tool | When to use | What you get |
|------|-------------|-------------|
| `agent0_brief` | **Session start — always** | Full context: state, recent changes, open issues, gospels |
| `agent0_query` | Any question about the project | Synthesized answer from full knowledge base |
| `agent0_state` | Quick state check | Raw current state |
| `agent0_gospels` | Before significant changes | All active rules derived from your codebase |

### What a session looks like

```
Session starts
  → agent0_brief()
  → "Phase 3 active. Last 3 changes: X, Y, Z.
     Gospel warning: config.py has 155 dependents.
     Open issues: I-12 (auth bug), I-15 (race condition).
     Reminder: ACTIVE_WORK.md is stale."

Before touching config.py
  → agent0_query("What should I know before changing config.py?")
  → "155 dependents. Last change caused regression W-34.
     Gospel G-07: run full test suite after any config change."

After finishing task
  → Update ACTIVE_WORK.md
  → Agent-0 watches it, logs intent vs. outcome automatically
```

### Why This Matters

Every AI tool that connects gets the same knowledge. Switch from Claude Code to Cursor mid-session — Agent-0 is the constant. No context lost between tools or sessions. The new session calls `agent0_brief` and is fully caught up in seconds.

---

## REST API

Agent-0 also exposes a REST API on `localhost:7800` for scripts, CI/CD, and custom integrations.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Status, project info, uptime |
| `/state` | GET | Current project state |
| `/brief` | GET | Handoff brief for new agent sessions |
| `/query` | POST | Ask a question (runs full ReACT loop) |
| `/gospels` | GET | All active gospel rules |
| `/alerts` | GET | Recent alerts and dismissal status |
| `/activity` | GET | Recent activity feed |
| `/knowledge` | GET | Browse all knowledge files |
| `/checkpoint` | GET | Latest checkpoint snapshot |
| `/config` | GET/POST | View/update configuration |

**Example:**
```bash
# Ask Agent-0 a question
curl -X POST http://localhost:7800/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What should I know before changing the auth module?"}'

# Get a handoff brief
curl http://localhost:7800/brief
```

---

## LLM Providers

Agent-0 supports three providers. You need an API key for one.

| Provider | Fast Model | Mid Model | Smart Model |
|----------|-----------|-----------|-------------|
| **Google Gemini** ⭐ | Gemini Flash | Gemini Flash | Gemini Pro |
| **Anthropic** | Claude Haiku | Claude Sonnet | Claude Opus |
| **OpenAI** | GPT mini | GPT standard | GPT full |

**Google Gemini is recommended** — it has a free embedding tier (1,500 requests/day via `gemini-embedding-001`) used for semantic search. If you use Anthropic or OpenAI for the LLM, you can still point embeddings to Google for free.

Agent-0 uses a **tiered model strategy** to control costs:
- **Fast tier** — file classification, quick summaries (~70% of calls)
- **Mid tier** — analysis, query responses, gospel checks
- **Smart tier** — onboarding synthesis, deep pattern analysis

Estimated cost for an active project: **~$10–25/month**.

---

## Knowledge Structure

When Agent-0 bonds to a project, it creates an `agent-0/` folder inside it:

```
your-project/
└── agent-0/
    ├── agent0.db          ← SQLite: all structured data + vector index
    ├── agent0.json        ← Project marker
    ├── gospels/           ← Rules derived from code, docs, and history
    │   ├── code_gospels.md
    │   └── pattern_gospels.md
    ├── modules/           ← Per-module understanding (built during onboarding)
    │   ├── core.md
    │   └── api.md
    ├── sessions/          ← Per-session logs with intent vs. outcome
    │   └── 2026-03-24.md
    ├── state/
    │   └── current.md     ← Always up-to-date live state
    ├── patterns/          ← Recognized recurring patterns
    ├── debt/              ← Technical debt ledger
    └── checkpoints/       ← Periodic project snapshots
```

All files are plain markdown — open them in any editor. The SQLite DB indexes everything for fast hybrid search (vector + keyword). The `agent-0/` folder is automatically added to `.gitignore` and is never committed.

---

## Configuration

Config is split into two layers:

**Global config** (`%LOCALAPPDATA%/Agent0/config.json`) — API keys, shared across projects:
```json
{
  "provider": "google",
  "api_key": "your-key-here",
  "embedding_provider": "google",
  "embedding_key": "your-key-here"
}
```

**Project config** (`<project>/agent-0/config.json`) — per-project settings:
```json
{
  "strictness": "normal",
  "debounce_seconds": 5,
  "ignore_patterns": ["node_modules", "venv", "__pycache__", ".git"],
  "alert_enabled": true,
  "checkpoint_interval_hours": 24,
  "monthly_budget_cap": 50.00
}
```

**Strictness modes:**
- `strict` — tight guardrails, frequent alerts, more LLM calls
- `normal` — balanced (default)
- `loose` — observe and log only, minimal interruptions

---

## Gospels

Gospels are the rules Agent-0 derives about your project. They are derived from **all sources** — not just a single config file:

- **Code patterns** — "config.py has 155 dependents — test thoroughly before changing"
- **Documentation** — rules found in any `.md`, `.txt`, or config file
- **History** — "last time X changed without Y, the build broke"
- **Patterns** — files that always change together become a dependency gospel
- **CLAUDE.md** — if it exists, all checklist items and rules are extracted

Gospels are stored in `agent-0/gospels/` as plain markdown. You can edit, add, or remove them. Agent-0 checks every change against all active gospels and flags violations.

---

## Onboarding

When Agent-0 first bonds to a project, it runs a deep one-time scan:

1. **Scan structure** — walks the directory tree, maps all files, identifies entry points
2. **Read docs** — reads every `.md`, `.txt`, and config file in batches
3. **Read code** — module by module, using AST for structure (no hallucination)
4. **Reason** — synthesizes everything into gospels, patterns, and a project overview
5. **Confirm** — presents its understanding; you can correct it before it goes live

Small project: minutes. Large project (thousands of files): hours. It only happens once.

---

## Tools (ReACT Loop)

Agent-0's reasoning uses 17 tools internally:

| Tool | Purpose |
|------|---------|
| `read_file` | Read any project file |
| `read_diff` | Compute diff between file versions |
| `list_files` | List project files with filters |
| `search_knowledge` | Semantic + keyword search of knowledge base |
| `search_project` | Search actual project files |
| `write_knowledge` | Write to knowledge markdown files |
| `db_write` / `db_query` | Read/write structured SQLite data |
| `get_state` | Get current project state |
| `check_gospels` | Check a change against all gospel rules |
| `git_info` | Get git status, log, branches |
| `send_alert` | Send alert to widget/API |
| `create_checkpoint` | Create a timestamped project snapshot |
| `log_question` | Log a user question for tracking |
| `summarize_and_split` | Split large knowledge files |
| `list_knowledge` | Browse the knowledge catalog |

---

## Project Structure

```
agent-0/
├── backend/
│   ├── main.py              ← Entry point
│   ├── config.py            ← Dual-layer config system
│   ├── logger.py
│   ├── agent/               ← ReACT loop, onboarding, briefing
│   ├── api/                 ← Flask REST API + MCP server
│   ├── llm/                 ← Multi-provider LLM client
│   ├── memory/              ← SQLite, markdown store, indexer, hybrid search
│   ├── reasoning/           ← Drift, patterns, debt, gospels, sessions
│   ├── tools/               ← 17 registered tools
│   └── watcher/             ← File watcher with debouncing
│
├── desktop/
│   ├── src/index.html       ← Widget UI
│   └── src-tauri/           ← Rust/Tauri native app
│
├── docs/                    ← 27 design documents
├── scripts/
│   └── setup.py             ← Development setup script
└── AGENT-0-MUST-READ.md     ← Core development bible
```

---

## Contributing

Agent-0 is in active development. The core mechanics work — file watching, classification, knowledge system, ReACT loop, Tauri UI, MCP server. The current focus is onboarding quality: making Agent-0's deep scan produce genuinely authoritative knowledge, not just shallow summaries.

**Priority areas:**
1. **Onboarding depth** — reading every file fully, deriving gospels from all sources
2. **Query quality** — answers should cite evidence from the knowledge base
3. **Cross-platform** — currently Windows-first, macOS/Linux support needed
4. **MCP polish** — more tools, better integration patterns

See [`docs/`](docs/) for the full design documentation, and [`AGENT-0-MUST-READ.md`](AGENT-0-MUST-READ.md) before contributing code.

**To contribute:**
1. Fork the repo
2. Run `python scripts/setup.py` to set up the dev environment
3. Make your changes against a real project (test with `--project /path/to/project`)
4. Submit a PR — describe what changed and what project you tested it on

---

## License

**Personal use only.** Free to use, modify, and run for personal and non-commercial purposes. Commercial use (products, services, internal business tooling, SaaS, consulting) requires explicit written permission.

See [LICENSE](LICENSE) for full terms. For commercial licensing, open an issue.

---

*Agent-0 is the zeroth agent. The constant. The one that knows everything.*

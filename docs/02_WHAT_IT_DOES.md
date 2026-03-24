# Agent-0: What It Does

## Core Functions

### 1. Watches

- File system watcher (event-driven, not polling)
- Triggers on any create, modify, or delete in the project folder
- Tracks what changed (diffs, not just "file X was saved")
- Tracks what *didn't* change (started Phase 16G but never closed 16F)
- Single line change, new file, deleted file — it wakes, processes, goes back to idle

### 2. Reads & Classifies

- Reads the actual diff of every change
- Classifies each change: feature work, bugfix, refactor, patch, test, config
- Understands which files/modules are coupled
- Knows which paths are critical vs low-risk

### 3. Reasons (Simple, Not Deep)

Agent-0 is not a deep reasoning engine. It does simple, reliable pattern matching:

- **Drift detection** — Compares current activity against stated goals. Gospel says "Phase 16 goal is X." After 10 edits, none advance X. Flag it.
- **Pattern recognition** — "This happened before during W2671. That time it led to a regression."
- **Debt tracking** — Distinguishes real fixes from patches. Maintains a debt ledger.
- **Session awareness** — Knows when a work session starts/ends, what the intent was vs what actually happened.
- **Dependency awareness** — Learns which files/modules are coupled. Flags when one changes without the other.
- **Risk scoring** — Not all changes are equal. Config file vs core reasoning module = different alert levels.
- **Git awareness** — Understands commits, reverts, branches. "User committed but didn't push." "User reverted 3 files but the related config change is still in place."

### 4. Writes (To Its Own Knowledge System)

Agent-0 writes constantly — but only to its own knowledge system, never to project code:

- **Markdown files** — Human-readable, organized by topic. Grows organically. When a file gets too large, Agent-0 splits it and cross-references both.
- **SQLite database** — Structured data, indexed for retrieval. Vector embeddings + full-text search.
- **Auto re-indexing** — When any markdown file changes, the SQLite index updates automatically.

### 5. Alerts (Proactive)

- "Hey, you've been off-goal for 45 minutes"
- "Hey, this looks like the same pattern from W2671"
- "Hey, you left Phase 16F open"
- "Hey, you changed module X but module Y depends on it"
- Alerts can be dismissed — Agent-0 logs the dismissal but doesn't forget
- Strictness modes: strict (tight guardrails) vs loose (just observe and log)

### 6. Answers (Queryable)

- Human asks via desktop widget: "What's the state of phase 16?"
- Working agent asks via API/MCP: "Brief me on what's in progress"
- Responds with reasoned, contextual answers — not file dumps
- Generates handoff briefs for new agent sessions

## What Agent-0 Does NOT Do

- Write project code
- Fix bugs
- Make architectural decisions
- Replace the working agent (Claude Code, Cursor, etc.)
- Manage multiple projects (one instance = one project)
- Deep multi-step reasoning chains
- Anything complex — simplicity is the entire point

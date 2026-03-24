# Agent-0: Knowledge System

## Design Philosophy

Inspired by OpenClaw's memory system: markdown files are the source of truth, SQLite indexes them for retrieval. Simple, robust, not deep — but reliable.

**Key change from original spec:** Knowledge is stored inside the project folder at `<project>/agent-0/` (not in AppData). This makes it visible, browsable, and project-specific. Global config (API keys) still lives in AppData.

- Markdown for human readability and durability
- SQLite for structured data and fast retrieval
- Hybrid search (vector + keyword) for querying
- Auto re-indexing when any markdown changes
- Files grow organically — no artificial limits on count
- Agent-0 self-organizes: splits large files, cross-references

## Knowledge Types

### Gospels (Sacred Rules)
Hard-won rules that rarely change. The guardrails.

Examples:
- "Touching module X without updating module Y WILL break Z"
- "Never refactor the memory system without running benchmark suite first"
- "The overarching goal of Phase 16 is X, not Y"

Stored in: `gospels/` folder. Few files, high value.

### State (Current Reality)
What's active right now. Always current, constantly overwritten.

- What phase is in progress
- What's blocked
- What's open/untested
- Last activity

Stored in: `state/current.md` — single file, always fresh.

### Phases (Project History)
One file per phase. Linear history of what happened.

- Phase opened, goal stated
- What actually happened during the phase
- Code changes, bugs found, decisions made
- Phase closed (or abandoned), outcome

Stored in: `phases/` folder. Grows naturally.

### Sessions (Daily Logs)
Per-session or per-day records.

- When work started/ended
- What the intent was
- What actually happened
- Drift score (did the session stay on target?)

Stored in: `sessions/` folder. One file per day or per session.

### Patterns (Recognized Recurrences)
Things Agent-0 has seen before.

- "This same error pattern appeared during W2671"
- "Last time this module was refactored, tests broke in 3 other modules"

Stored in: `patterns/` folder. Grows over time.

### Debt (Technical Debt Ledger)
Patches that need real fixes.

- What was patched and when
- Root cause (if known)
- Risk level
- Status (open, resolved)

Stored in: `debt/` folder.

### Modules (Codebase Understanding)
Per-module knowledge built during onboarding.

- What the module does
- Key files and functions
- Dependencies (what it depends on, what depends on it)
- Known issues

Stored in: `modules/` folder.

### Checkpoints (Point-in-Time Snapshots)
Periodic coherent summaries of project state.

- Timestamped
- "As of March 12: Phase 16G in progress, 3 open bugs, 2 patches need root-cause fixes"
- Useful when returning after days/weeks away

Stored in: `checkpoints/` folder.

## File Management Rules

1. **No artificial file limits** — Create as many .md files as needed
2. **Auto-split** — When a file gets too large, split it and cross-reference both
3. **Auto-index** — Every .md file change triggers re-indexing in SQLite
4. **Human-editable** — User can open, edit, reorganize any file. Agent-0 re-indexes on change
5. **DB mirrors markdown** — SQLite contains structured versions of what's in the markdown. Markdown is source of truth

## Retrieval (Hybrid Search)

Following the OpenClaw approach:

1. **Vector similarity** — Embeddings stored in SQLite via `sqlite-vec`. Semantic matching ("find things related to the build pipeline").
2. **Full-text search** — SQLite FTS5. Exact keyword matching ("find all mentions of W2671").
3. **Weighted fusion** — Both scores combined into a final relevance score.

When Agent-0 needs to answer a query or check against gospels, it searches its own knowledge using this hybrid approach. Fast, reliable, works at any scale of markdown files.

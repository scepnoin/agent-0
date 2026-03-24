# Agent-0: Onboarding Phase

## Overview

When Agent-0 first bonds to a project, it does a full deep scan before it ever goes idle. This is the onboarding phase — it can take minutes (small project) or hours (massive codebase with thousands of files). It only happens once.

## Core Pattern: Write-As-You-Go

**Critical design decision:** Agent-0 writes after every small step, not at the end. This prevents three problems:

1. **Context bloat** — Reading 200 files before writing anything overloads the LLM context
2. **Hallucination** — Too much in one call = the LLM starts making things up
3. **Context loss** — If the call fails or gets compressed, everything learned is gone

The pattern:
```
DO small chunk
  → WRITE to .md + DB
  → CLEAR (new LLM call, fresh context)
  → READ BACK own notes
  → CONTINUE with next chunk
```

Agent-0 takes notes as it goes and reads its own notes back to stay grounded. Each LLM call is small and focused. No single call ever holds the entire project in context. Understanding is built incrementally through its own written artifacts.

## Onboarding Phases

### Phase 1: SCAN STRUCTURE
- Walk entire directory tree
- Map folder structure, file types, file counts
- Identify key files (configs, entry points, tests, docs)
- Ignore junk (node_modules, venv, __pycache__, tmp files, build artifacts)
- **WRITE** → `structure.md` + DB tables
- **READ BACK** → `structure.md`

### Phase 2: READ KEY DOCS (batch by batch)

Each batch is a separate LLM call with fresh context:

**Batch 1:** README, CLAUDE.md, any roadmap/plan files
- **WRITE** → `project_overview.md` + DB
- **READ BACK** what was written

**Batch 2:** Known issues, active work docs, changelogs
- **WRITE** → update `state/current.md` + DB
- **READ BACK**

**Batch 3:** Config files, entry points, requirements
- **WRITE** → update `architecture.md` + DB
- **READ BACK**

**Batch N:** Continue batching through remaining docs...

### Phase 3: READ CODE (module by module)

Each module/directory is a separate LLM call:

**Module 1:** e.g., `core/cognitive/`
- Read all files in the module
- **WRITE** → `modules/cognitive.md` + DB
- **READ BACK**

**Module 2:** e.g., `core/agency/`
- **WRITE** → `modules/agency.md` + DB
- **READ BACK**

Continue module by module until entire codebase is covered.

### Phase 4: REASON (on its own notes, not raw files)

This is the synthesis step. Agent-0 reads back ALL its own .md files (which are small, summarized) and reasons about the full picture:

- What is this project? What are its goals?
- What's the architecture — what depends on what?
- What phase is it in?
- What's broken / open / in progress?
- What patterns exist?
- What technical debt is visible?

- **WRITE** → `gospels/goals.md`, `debt/ledger.md`, `patterns/patterns.md`
- **READ BACK**

### Phase 5: CONFIRM (human in the loop)

Before going live, Agent-0 presents its understanding to the user via the widget:

- "Here's what I understand about this project"
- Summary of: goals, architecture, current state, identified risks, proposed gospels
- User can correct, add rules, clarify goals
- Agent-0 updates its knowledge based on corrections
- **WRITE** → all corrections and additions

### READY

Onboarding complete. Agent-0 goes idle and starts watching for file changes. From this point forward, every change is incremental — it already knows the full picture.

## Key Design Points

- **Progressive depth:** Structure first, then key docs, then code, then details. If the user stops it early, it still has a useful baseline.
- **Chunked processing:** Never shove everything into one LLM call. Small batches, small context, reliable outputs.
- **Self-referential:** Agent-0 reads its own notes back. It builds understanding through its own written artifacts, not by trying to hold everything in context.
- **Takes as long as needed:** Small project = minutes. A large production codebase (50,000+ files) = hours. That's fine — it only happens once.

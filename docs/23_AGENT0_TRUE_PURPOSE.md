# Agent-0: True Purpose & Knowledge Architecture

## What Agent-0 Actually Is

Agent-0 is NOT just a file watcher. It is the **single source of truth for the project** — for both AI agents and human developers.

### The Problem It Solves

1. **For the developer:** "What did I change 2 days ago? What broke because of it? What was the state before?" — Instead of spending 2 hours digging through code and docs, ask Agent-0.

2. **For AI agents:** When a new Claude Code / Codex / Cursor session starts with zero context, the agent reads CLAUDE.md. But CLAUDE.md is static. Agent-0 is LIVE — it has a perfect record of every change, every issue, every decision. The new agent calls Agent-0's API and gets fully caught up instantly.

3. **For onboarding:** Months of work on a large project. Hundreds of changes, phases, sprints, issues. A new agent or developer needs to understand ALL of it — precisely, not approximately. Agent-0 has the complete history.

## Agent-0 Is NOT a Mirror of the Project

Agent-0's knowledge structure does NOT mirror the project's folder structure. It creates its OWN organized source of truth:

### Knowledge Categories

**Documentation Intelligence**
- Every doc in the project, understood and catalogued
- Not just summaries — structured records
- Completed work: every W-number, I-number, what was done, when
- Known issues: every open bug, severity, affected modules
- Roadmap: phases, goals, status, what's next
- Historical: what decisions were made and why

**Code Intelligence**
- Every module, sub-module, class, function mapped (AST)
- Every dependency traced (what imports what)
- Critical files ranked by impact (dependents count)
- Every TODO, FIXME, HACK found and tracked
- File change history with real diffs

**Gospel Rules (Derived From ALL Sources)**
- From code: "config.py has 155 dependents — test thoroughly before changing"
- From docs: "Never modify core/cognitive without running full test suite" (from KNOWN_ISSUES)
- From CLAUDE.md (if exists): All checklist items and rules
- From history: "Last time plan_executor.py was changed without updating planner.py, the build broke"
- From patterns: Files that always change together → dependency gospel

**Live State**
- Current phase, goal, what's active
- Last N changes with diffs
- Open issues, blockers
- Session history (who did what, when)

## How It's Used

### Scenario 1: New Claude Code Session
```
Claude Code starts → reads CLAUDE.md → sees "Call Agent-0 API for full context"
Claude Code: POST /query "Brief me on current state and recent changes"
Agent-0: "You're on MyProject. Phase 3 paused. Refactor Sprint complete.
          Last 3 changes: fixed build metadata regression in orchestrator.py,
          fixed identity visibility in architecture.py,
          fixed UnboundLocalError in executor.py.
          30 gospel rules active. 46 open known issues. Test suite: 3149 tests."
```

### Scenario 2: Developer Returns After Weekend
```
Developer: "What happened while I was away?"
Agent-0: "12 files changed across 3 sessions. Key changes:
          - Watcher pipeline rewritten for real diffs
          - Gospel extraction now uses CLAUDE.md rules
          - 2 new known issues found (I-573, I-574)
          - Hardening Sprint 5 started"
```

### Scenario 3: Before Making a Change
```
Developer: "I need to modify config.py. What should I know?"
Agent-0: "config.py has 155 dependents. Last modified 3 days ago.
          Gospel rule: 'Test thoroughly — affects entire system.'
          Last time it was changed without testing, W2432 regression occurred.
          Dependencies: every module in core/ imports it.
          Related known issues: I-445 (config reload race condition)."
```

## Onboarding Philosophy

Onboarding is ONE SHOT but THOROUGH. It can take hours. That's OK.

For each document in the project:
- Read it FULLY (not truncated to 5000 chars)
- Understand what type of document it is
- Extract structured facts into the DB
- Write a detailed record to the appropriate .md
- Move to the next document

For each code file:
- Parse with AST (classes, functions, imports, TODOs)
- Store structured facts in DB
- Write analysis to module .md
- Trace dependencies

For the synthesis:
- Read ALL own notes
- Build comprehensive understanding
- Derive gospels from ALL sources
- Create actionable knowledge, not just summaries

The result: Agent-0 becomes THE authority on the project. Anyone (human or AI) can query it and get accurate, detailed, up-to-date answers about any aspect of the project.

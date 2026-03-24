# AGENT-0 MUST READ — Development Bible

**THIS FILE IS THE SOURCE OF TRUTH FOR ALL DEVELOPMENT ON AGENT-0.**
**Read this FIRST before writing any code. If work drifts from this, STOP.**

---

## What Agent-0 IS

Agent-0 is the SINGLE SOURCE OF TRUTH for a software project. It is the team memory, QA engineer, and project manager that a solo developer using AI agents doesn't have.

When Agent-0 is bonded to a project, it knows EVERYTHING about that project — every file, every module, every dependency, every rule, every issue, every decision, every change. It becomes the authority that both humans and AI agents query to understand the project.

## What Agent-0 is NOT

- NOT a code writer or bug fixer
- NOT a UI-first application (the brain matters, not the face)
- NOT a shallow summarizer that skims files
- NOT dependent on any single file existing (like CLAUDE.md)

## The 4 Things Agent-0 Does

1. **READS** — Every file, every doc, every code module. Thoroughly. If it takes hours, that's fine. Thoroughness over speed.
2. **WRITES** — Structured, organized knowledge. Both markdown (human readable) AND SQLite (machine queryable). Raw facts, not summaries of summaries.
3. **WATCHES** — Every file change, classified with real diffs, logged with context.
4. **ANSWERS** — Any question about the project, accurately, with evidence.

## Core Architecture (DO NOT CHANGE)

- Python backend (Flask API + SQLite + file watcher)
- Tauri desktop app (native window, not web UI)
- Knowledge stored in `<project>/agent-0/` folder
- Global config (API keys) in AppData
- One instance per project, total isolation
- ReACT loop with tools for reasoning
- AST analysis for code structure (programmatic, no LLM)
- File snapshots for real diffs (no git dependency)
- Tiered LLM: fast (classification) / mid (analysis) / smart (synthesis)
- MCP server for agent integration

## Gospel Sources (ALL of these, not just one)

1. **Code patterns** — dependency coupling, critical files, import chains
2. **Project documentation** — ANY .md, .txt, config file with rules/constraints
3. **CLAUDE.md** (if it exists) — checklist items, rules, lessons
4. **History** — past changes, what broke, what was fixed
5. **Architecture** — structural patterns that must be preserved

## Onboarding Philosophy

ONE SHOT. THOROUGH. Take as long as needed.

For each document: read it FULLY → understand it → write structured facts to DB AND .md → move on.
For each code file: parse with AST → store classes/functions/imports → trace dependencies.
For synthesis: use SMART tier LLM → derive gospels from ALL sources → create comprehensive state.

The result: Agent-0 becomes THE authority. Anyone can query it and get accurate answers.

## Knowledge Structure

Agent-0 creates its OWN organized knowledge — it does NOT mirror the project structure:

- **Documentation intelligence** — every doc catalogued, work items tracked, issues listed
- **Code intelligence** — every module analyzed, dependencies traced, critical files ranked
- **Gospels** — derived from code + docs + patterns + history
- **Live state** — current phase, recent changes, open issues, session history

## Priority Order for Development

1. **Onboarding quality** — this is everything. If Agent-0 doesn't deeply understand the project, nothing else matters.
2. **Change tracking accuracy** — real diffs, accurate classification, proper logging
3. **Query/answer quality** — search finds what Agent-0 knows, answers are factual
4. **Gospel derivation** — from ALL sources, not just one file
5. **UI/Tauri/packaging** — LAST priority. The brain matters, not the face.

## Anti-Patterns (Things That Wasted Time)

- Spending hours on PyInstaller .exe packaging before the core worked
- Fighting pywebview then switching to Tauri then fighting Tauri
- Multiple onboarding rewrites (V1, V2, V3) that were all too shallow
- UI polish (dashboard stats, activity feeds) before knowledge quality was solid
- Hallucinated gospels from LLM instead of reading actual project rules
- Truncating files to 3000-5000 chars — losing most of the content
- Summarizing summaries — losing signal at each compression step

## This Development Is Proof Agent-0 Works

This entire development session is a perfect example of why Agent-0 is needed:
- We drifted from the core mission (onboarding quality) to UI work multiple times
- We rewrote the same code 3+ times because we lost context
- The original vision (doc 01) described EXACTLY what we re-discovered hours later
- If Agent-0 had been watching, it would have flagged the drift immediately

**Build Agent-0 properly. Stay focused on the brain. The face comes last.**

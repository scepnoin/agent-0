# Agent-0: Vision

## What Is Agent-0?

Agent-0 is a lightweight sentinel agent — a small, always-on `.exe` that bonds to a single project folder and becomes the sole authority on everything that happens in it. Its only reason for existing is to make sure that project succeeds.

It does not write code. It does not fix bugs. It does not make architectural decisions. It **watches, tracks, remembers, reasons, and speaks up**.

## The Problem It Solves

### The Solo Dev + Agentic Tool Reality

A clean team of 5-6 developers has natural checks: code review, QA, institutional memory, someone saying "hey didn't we already try that?" When a solo developer replaces that team with agentic tools (Claude Code, Cursor, Codex, etc.), several things break:

1. **Rabbit-hole chaining** — Feature work leads to a bug, which leads to a deeper bug, which leads to hours lost. The original feature goes in undertested. Weeks later, a regression bites you that traces back to that chaotic session.

2. **Context death** — Conversations build rich understanding (why a decision was made, what was tried and failed, subtle tradeoffs). Then the chat hits its limit, compresses, or a new session starts. The markdown files capture *what* but not the *why* or the *journey*. The semantics evaporate.

3. **Agent narrow-mindedness** — Agentic tools tend to reach for the quickest fix — patch the symptom, not the root cause. A real teammate would push back. Agents don't always do that unprompted.

4. **Documentation sprawl** — 100+ markdown files (roadmaps, plans, known issues, completed items) constantly in flux. Hundreds of lines changing daily. Nothing is coherent, things fall through the cracks.

5. **No safety net for the pace** — The agentic workflow lets you ship changes faster than any process can track them. Things get done but not *accounted for*.

### What Agent-0 Replaces

Agent-0 is the **team memory + QA engineer + project manager** that a solo dev with an agent doesn't have. It's the institutional knowledge that would normally be distributed across 5-6 people's heads — but persistent, searchable, and always up to date.

## Core Principles

- **Simplicity is key** — Agent-0 does a few things and does them 100%. It is not a multi-level reasoning agent. It is not trying to be a general-purpose AI agent or a full reasoning system. It is a small sentinel that tracks everything as a source of truth.
- **One agent, one project** — Total devotion. Each Agent-0 instance is bonded to a single project folder. Its entire existence revolves around that project. No cross-project confusion.
- **Read, reason, write** — That's the loop. Read what changed. Reason about what it means. Write it down. Go idle.
- **Event-driven** — Sits idle at near-zero resource usage. Wakes only when something changes. Processes. Goes back to idle.
- **Human-editable knowledge** — All knowledge stored as markdown files + SQLite. The human can open, read, edit, reorganize any of it.
- **Tool-agnostic** — Doesn't matter if the developer uses Claude Code, Cursor, Codex, Windsurf, or anything else. Agent-0 is the constant.

## What Type of Agent Is This?

This is a **sentinel agent** — a new category in the AI agent taxonomy. Most agents are built to *do work*. Agent-0 doesn't do the work — it watches the work and makes sure the work succeeds. It maintains file snapshots for computing real diffs without requiring git, and uses a tiered LLM strategy (fast/mid/smart) for cost optimization.

- **Sentinel** — watches, guards, alerts
- **Ambient** — always-on, background, non-intrusive, event-driven
- **Meta-agent** — oversees other agents and work processes

The name "Agent-0" reflects this: it's the zeroth agent, the one that exists before any working agent spins up, and persists after they all shut down.

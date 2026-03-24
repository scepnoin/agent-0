# Agent-0: Interfaces

## Overview

Agent-0 has two access points: a desktop widget for the human, and an API/MCP endpoint for working agents.

## 1. Desktop Mini-Widget

A small, always-visible floating window on the desktop. Not a full app — minimal, out of the way, but always there.

### Components
- **Status indicator** — Idle (dim) / Processing (active) / Onboarding (progress) / Alert (highlight)
- **Alert area** — Shows recent pings: "heads up — you've been off-goal for 45 minutes"
- **Input field** — Query Agent-0 directly: "what's the state of phase 16?" / "what did I break today?" / "what's still open?"
- **Response area** — Agent-0's answers, concise and contextual
- **Health dashboard** — Simple stats at a glance: open items, drift score, debt count, days since last checkpoint

### Behavior
- Always on top (optional, user-configurable)
- Collapsible to just the status indicator
- Pings appear as subtle notifications, not modal popups
- Dismissing a ping logs it (Agent-0 doesn't forget)

## 2. Flask REST API

For external tools, scripts, and automation to query Agent-0.

### Endpoints

```
GET  /health          → Agent-0 status (idle, processing, onboarding)
GET  /state           → Current project state (state/current.md)
GET  /brief           → Handoff brief for new agent sessions
GET  /gospels         → All active gospel rules
POST /query           → Free-form query with hybrid search + LLM synthesis
GET  /phases          → Phase list with statuses
GET  /debt            → Current debt ledger
GET  /alerts          → Recent alerts and their dismissal status
GET  /checkpoint      → Latest checkpoint snapshot
```

### Usage Examples
- A script that checks project state before deploying
- CI/CD pipeline that queries gospels before merging
- A dashboard that pulls health stats

## 3. MCP Server (Model Context Protocol)

For direct integration with agentic coding tools.

### Supported Tools (MCP-compatible)
- Claude Code
- Cursor
- Codex
- Windsurf
- Any MCP-compatible tool

### How It Works
- Agent-0 exposes itself as an MCP server
- The working agent (e.g., Claude Code) connects to it as a tool
- Before starting work, the agent calls Agent-0: "brief me"
- During work, the agent can check: "does this violate any gospels?" / "what's the state of module X?"
- Agent-0 responds from its full accumulated understanding

### Key Benefit
Every working agent that connects gets the same knowledge. Doesn't matter if you switch from Claude Code to Cursor mid-session — Agent-0 is the constant. No context lost between tools.

## Access Pattern

```
Human → Desktop Widget → Agent-0 → answers / alerts
Agent → API or MCP     → Agent-0 → answers / briefs / gospel checks
```

Both hit the same knowledge base. Same source of truth. Always consistent.

# Working with Agent-0: A Guide for AI Coding Agents

This guide is for the AI coding agents (Claude Code, Cursor, Codex, Windsurf, etc.) that work alongside Agent-0. It explains exactly how to talk to Agent-0, when to call it, and what it can tell you.

---

## The Relationship

You are the **working agent** — you write code, fix bugs, build features.
Agent-0 is the **sentinel** — it knows everything about the project and keeps you grounded.

You do the work. Agent-0 makes sure the work succeeds.

```
You (Claude Code / Cursor / etc.)
    │
    │  "Brief me" / "What should I know?" / "Check this change"
    ▼
Agent-0 (localhost:7801 via MCP, or localhost:7800 via HTTP)
    │
    │  "Here's the state. Here's what's open. Here's what to watch out for."
    ▼
You, now with full context
```

---

## Step 0: Add Agent-0 to Your CLAUDE.md

Put this in your project's `CLAUDE.md` (create it if it doesn't exist). This ensures every Claude Code session knows about Agent-0 automatically.

```markdown
## Agent-0 — Project Oracle

Agent-0 is running and watching this project. It knows everything.
**Always call it first before starting any work.**

MCP server: localhost:7801
REST API: localhost:7800

### Session Start (REQUIRED)
Before doing anything else:
```
POST http://localhost:7800/brief
```
Read the response fully. It contains current state, recent changes,
open issues, active gospel rules, and any pending reminders.

### Before Touching Critical Files
Always check gospels first:
```
POST http://localhost:7800/query
{"question": "What should I know before changing [filename]?"}
```

### When You're Not Sure What's Going On
```
POST http://localhost:7800/query
{"question": "your question here"}
```

### When You Finish a Task
Update ACTIVE_WORK.md with what you did. Agent-0 watches it.
```

---

## The 4 MCP Tools

When connected via MCP (localhost:7801), you have 4 tools available:

### `agent0_brief`
**Use at the start of every session. No exceptions.**

Returns: current phase/goal, last N changes with diffs, open issues,
active gospel rules, any staleness warnings, and pending reminders.

```
Call: agent0_brief()
```

Example response:
```
Phase 3 is active. Goal: refactor the auth module.
Last 3 changes: auth/middleware.py (refactor), tests/test_auth.py (added),
config.py (modified — 155 dependents, tested).
Open issues: 2 bugs (I-12, I-15), 1 untested change in session.py.
Active gospels: 8 rules. Key: "Never modify database schema without migration."
Reminder: ACTIVE_WORK.md hasn't been updated in 4 hours.
```

---

### `agent0_query`
**Ask anything about the project.**

Returns: a synthesized answer from Agent-0's full knowledge base — change
history, patterns, gospel rules, module analysis, session logs.

```
Call: agent0_query(question="What broke last time someone changed the auth module?")
Call: agent0_query(question="What is the current state of the payment feature?")
Call: agent0_query(question="What files always change together with config.py?")
Call: agent0_query(question="What open issues are related to the database?")
```

---

### `agent0_state`
**Get the raw current state.**

Returns: the contents of `state/current.md` — what's active right now.
Faster than `agent0_brief` when you just need a quick check.

```
Call: agent0_state()
```

---

### `agent0_gospels`
**Get all active gospel rules.**

Returns: the full list of rules Agent-0 has derived for this project.
Call this before making any significant change.

```
Call: agent0_gospels()
```

---

## The REST API (Without MCP)

If you're not using MCP, hit the REST API directly on `localhost:7800`.

```bash
# Get a full brief (DO THIS FIRST)
curl http://localhost:7800/brief

# Ask a question
curl -X POST http://localhost:7800/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What should I know before changing config.py?"}'

# Get current state
curl http://localhost:7800/state

# Get all gospel rules
curl http://localhost:7800/gospels

# Get recent alerts
curl http://localhost:7800/alerts

# Get open items
curl http://localhost:7800/debt
```

---

## When to Call Agent-0

### Always
| Moment | What to call | Why |
|--------|-------------|-----|
| **Session start** | `agent0_brief` | Get full context before touching anything |
| **Before a risky change** | `agent0_query("What should I know before changing X?")` | Check gospels, history, dependents |
| **When you're confused** | `agent0_query("What is the state of X?")` | Agent-0 has the full history |
| **After finishing a task** | Update `ACTIVE_WORK.md` | Lets Agent-0 track your intent |

### When Something Feels Off
```
agent0_query("Has anything like this happened before?")
agent0_query("What patterns exist around this module?")
agent0_query("What are the open issues in this area?")
```

### When You're About to Touch a Core File
```
agent0_query("How many files depend on [filename]?")
agent0_query("What breaks if I change [filename]?")
agent0_query("What was the last significant change to [module] and why?")
```

---

## The 5 Tracking Docs

Agent-0 watches these files closely. Keeping them updated makes Agent-0
dramatically more useful — it can connect your changes to your goals,
detect drift, and give far more accurate context.

| File | What it tracks | Who updates it |
|------|---------------|----------------|
| `ACTIVE_WORK.md` | What you're working on **right now** | You (the working agent) |
| `COMPLETED_WORK.md` | What you've finished | You + Agent-0 |
| `KNOWN_ISSUES.md` | Open bugs and issues | You + Agent-0 |
| `ROADMAP.md` | Phases, goals, what's next | Developer |
| `CHANGELOG.md` | Version history | You |

### ACTIVE_WORK.md format (simple is fine)
```markdown
## Currently Working On
Fixing auth token expiry bug (I-12)
- Editing: auth/middleware.py
- Plan: add refresh token logic before expiry check
- Started: 2026-03-24 10:00
```

When Agent-0 sees this, it knows:
- Changes to `auth/middleware.py` are **intentional and on-track**
- If you start editing unrelated files, it will flag it as drift
- When you mark I-12 resolved, it logs the fix automatically

---

## What Agent-0 Will Tell You (Proactively)

Agent-0 doesn't interrupt you mid-task. It piggybacks reminders onto
your next query. Watch for these in responses:

**Drift warning:**
> "By the way — your ACTIVE_WORK.md says you're fixing I-12 in auth/middleware.py
> but your last 6 changes were all in database/schema.py. Drift?"

**Pattern warning:**
> "Heads up — a similar change to this module caused a regression last month.
> Check the build pipeline after committing."

**Gospel reminder:**
> "Note: database schema changes require a migration file per gospel rule G-04.
> Don't see one in your recent changes."

**Staleness reminder:**
> "ACTIVE_WORK.md hasn't been updated in 3 hours. When you get a chance,
> update it with what you're currently doing."

These are suggestions, not demands. You can proceed. Agent-0 will log
whether you heeded or dismissed the warning — that history informs future patterns.

---

## Example: A Full Session

```
=== SESSION START ===

Working Agent: [calls agent0_brief]
Agent-0: "Phase 3 active. Goal: refactor auth module.
          Last session: middleware.py partially refactored, session.py untouched.
          Open: I-12 (token expiry bug), I-15 (race condition in login).
          Gospel G-04: database schema changes require migration files.
          Gospel G-07: auth module changes require full test suite run.
          Reminder: ACTIVE_WORK.md hasn't been updated since yesterday."

Working Agent: Updates ACTIVE_WORK.md — "Fixing I-12: token expiry bug"

Working Agent: [edits auth/middleware.py]
Agent-0: [watches the change, logs it as on-track with Phase 3 / I-12]

Working Agent: [about to edit database/schema.py]
Working Agent: [calls agent0_query("What should I know before changing schema.py?")]
Agent-0: "schema.py has 23 dependents. Gospel G-04 applies: you need a migration file.
          Last schema change was 3 weeks ago — caused I-08 (data type mismatch).
          Current open issue I-15 is related to a race condition that schema.py touches."

Working Agent: Creates migration file first, then edits schema.py

Working Agent: Updates COMPLETED_WORK.md — "Fixed I-12"
Working Agent: Updates KNOWN_ISSUES.md — "I-12: RESOLVED"
Agent-0: [watches the update, auto-logs the resolution with the diff]

=== SESSION END ===
Agent-0: Full session logged. Next session brief will include: I-12 resolved,
         schema.py changed (migration created), I-15 still open.
```

---

## Key Rules for Working Agents

1. **Brief first, always.** Don't touch anything before calling `agent0_brief`.
2. **Ask before risky changes.** Any core file, shared module, or config — query Agent-0 first.
3. **Update ACTIVE_WORK.md.** Even a one-liner. It multiplies Agent-0's usefulness.
4. **Don't dismiss warnings without reading them.** Agent-0's pattern matching is based on real history.
5. **Trust the gospels.** They were derived from the project's actual code, docs, and history — not invented.

---

## Troubleshooting

**Agent-0 not responding?**
```bash
curl http://localhost:7800/health
```
If no response: Agent-0 isn't running. Launch `Agent-0.exe` or start the backend:
```bash
python backend/main.py --project /path/to/project
```

**MCP not connecting?**
Check that port 7801 is open and Agent-0 is running. The MCP server starts
automatically alongside the Flask API.

**Getting empty/wrong answers?**
Agent-0's knowledge quality depends on onboarding. If it was just installed,
onboarding may still be in progress. Check the widget or:
```bash
curl http://localhost:7800/health
# Look for "onboarding_complete": true
```

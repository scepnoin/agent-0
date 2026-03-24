# Agent-0: Agent-to-Agent Communication & Project Hygiene

## The Problem

Agent-0 can see WHAT changed but not WHY. It doesn't know the developer's intent. If the dev is fixing bug I-445, Agent-0 just sees "cognitive_architecture.py modified" — it can't connect the change to the goal.

## The Solution: Standard Tracking Docs

Every project should have these 5 core tracking documents:

| Document | Purpose | Who Updates |
|----------|---------|-------------|
| ACTIVE_WORK.md | What's being worked on RIGHT NOW | Working agent + dev |
| COMPLETED_WORK.md | What's been finished (W-numbers, I-numbers) | Agent-0 + working agent |
| KNOWN_ISSUES.md | Open bugs, issues, regressions | Agent-0 + working agent |
| ROADMAP.md | Phases, goals, what's next | Dev |
| CHANGELOG.md | Version history, releases | Working agent |

Agent-0 watches these files. When they change, it updates its understanding of the project's current goals, active work, and status.

## Onboarding: Recommend Missing Docs

During onboarding, if Agent-0 doesn't find these docs, it sends a recommendation via MCP to the working agent:

```
Agent-0 → Working Agent (via MCP):
"For me to track your project effectively, I recommend creating these files:
- ACTIVE_WORK.md (what you're currently working on)
- KNOWN_ISSUES.md (open bugs and issues)
- COMPLETED_WORK.md (finished work items)
When you have a moment between tasks, please create them.
I'll watch them and use them to understand your goals."
```

This is NOT a hard requirement. Agent-0 works without them. But it works MUCH better with them.

## How Agent-0 Uses These Docs

### Drift Detection
```
ACTIVE_WORK.md says: "Fixing I-445: config reload race condition"
Agent-0 sees: 5 changes to cognitive_architecture.py (not config.py)
Agent-0 pings: "Your active work says config.py but you've been editing
                cognitive_architecture.py for the last hour. Drift?"
```

### Change Context
```
ACTIVE_WORK.md says: "Phase 16K: ReAct architecture integration"
Agent-0 sees: plan_executor.py modified
Agent-0 logs: "Change to plan_executor.py — ON TRACK with Phase 16K goal"
```

### Auto-Completion Tracking
```
KNOWN_ISSUES.md: "I-445: config reload race condition — OPEN"
Agent-0 sees: config.py changed, tests pass, KNOWN_ISSUES.md updated to "RESOLVED"
Agent-0 auto-logs: "I-445 resolved. Changes: config.py lines 200-215"
```

## Agent-to-Agent Ping System

When Agent-0 detects that the core tracking docs are stale (changes happening but docs not updated), it pings the working agent:

```
Agent-0 → Working Agent (via MCP):
"Hey — you've made 8 changes in the last 2 hours but ACTIVE_WORK.md
hasn't been updated. When you finish your current task, can you update:
1. ACTIVE_WORK.md with what you're currently doing
2. COMPLETED_WORK.md with what you just finished
This helps me track the project accurately. Thanks."
```

### Key Principles:
- Agent-0 NEVER interrupts mid-task — waits for a natural break
- The ping is a suggestion, not a demand
- Agent-0 phrases it as "when you're done" not "do this now"
- If the working agent is deep in coding, it can ignore and Agent-0 will remind later
- Agent-0 can also ping the human directly via the widget

## Two-Way Flow

```
Developer/Working Agent → Updates docs → Agent-0 reads them → Understands goals
Agent-0 → Detects drift/staleness → Pings working agent → Agent updates docs
```

Neither side does ALL the work. It's collaborative:
- The working agent updates docs when it naturally can
- Agent-0 watches, reminds, and fills gaps where it can
- The developer can always override or correct

## Connection Model: Agents Come to Agent-0

Agent-0 does NOT discover or find agents. The working agent connects to Agent-0 via MCP. Agent-0 tracks who's connected.

```
5 projects, 5 Agent-0 instances, each isolated:

ProjectA/agent-0      → MCP :7801 → Claude Code session
ProjectB/agent-0      → MCP :7803 → Cursor session
ProjectC/agent-0      → MCP :7805 → Codex session
```

Each Agent-0 only knows about agents that connect to IT. No cross-talk.

### Pinging Is Piggyback, Not Push

Agent-0 doesn't push notifications. It waits for the working agent to make its next query, then includes the reminder in the response:

```
Working Agent: POST /query "What's the current state?"
Agent-0: "Current state is Phase 16K. By the way — ACTIVE_WORK.md
          hasn't been updated in 2 hours. When you get a chance,
          please update it with what you're working on."
```

No complex notification system. Just append reminders to responses.

### Session Reconnection (Critical)

When an agent disconnects and a new session connects, Agent-0 gives a "welcome back" brief on first contact:

```
New Agent Session: POST /brief
Agent-0: "Welcome back. Since the last session:
          - 12 files changed across 3 hours
          - Key changes: plan_executor.py (bugfix), config.py (refactor)
          - ACTIVE_WORK.md is stale (last updated 4 hours ago)
          - KNOWN_ISSUES.md has 2 new entries from change tracking
          - Gospel reminder: config.py has 155 dependents, test thoroughly

          Recommend updating ACTIVE_WORK.md before starting new work."
```

This is the MOST important interaction. The new agent session starts with FULL context. No more "zero context" cold starts.

### What Agent-0 Tracks Per Connection

```
DB table: agent_connections
  - connection_id
  - connected_at
  - last_query_at
  - agent_type (claude_code, cursor, codex, unknown)
  - queries_count
  - pings_pending (JSON list of reminders to deliver)
```

When a new connection is detected (first query after no activity for 30+ minutes), Agent-0 treats it as a new session and delivers the welcome brief + any pending pings.

## Implementation (Future — V5)

1. MCP tools: `agent0_recommend_docs`, `agent0_check_staleness`
2. Watcher: special handling for core tracking doc changes
3. Ping system: queue pings, deliver at natural breaks
4. Auto-completion: detect when issues are resolved from code changes
5. Template: provide starter templates for the 5 core docs if they don't exist

## This Is NOT Required for V4

V4 priority is onboarding quality and code knowledge. The agent communication system is V5. Document it, don't build it yet.

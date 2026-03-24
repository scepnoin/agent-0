# Agent-0: Gospel Management

## What Are Gospels?

Gospels are the sacred rules of a project. Hard-won knowledge captured as guardrails. They are the highest-authority knowledge Agent-0 holds — violations are ALWAYS flagged, regardless of strictness mode.

Examples:
- "Touching `core/cognitive/reasoning.py` without updating `core/agency/control.py` WILL break the build"
- "Never refactor the memory system without running the full benchmark suite first"
- "The overarching goal of Phase 16 is to unify the brain architecture — all work should advance this"
- "The `predict()` function in `models/predictor.py` must always return a dict, never a list"

Gospels are NOT documentation. They are **rules that prevent damage**.

## Gospel Autonomy

**Agent-0 creates, edits, and retires gospels on the fly — autonomously.**

The whole point of Agent-0 is it works while the human is busy. If the user is deep in a rabbit hole, 4 hours into a bug chase, they're not going to stop to approve a gospel suggestion. Agent-0 needs to act immediately.

### Two Tiers of Gospels

#### HUMAN GOSPELS (highest authority)
- Created directly by the human (via widget, API, or editing files)
- Agent-0 can NEVER modify or retire a human gospel — only the human can
- These are the absolute rules the human has explicitly set
- Flagged in DB: `created_by: "human"`

#### AGENT GOSPELS (auto-created, auto-managed)
- Created by Agent-0 when it detects patterns, dependencies, or risks
- Activated IMMEDIATELY — no waiting for approval
- Agent-0 can edit, merge, or retire its own gospels as understanding evolves
- The human can review, promote to human gospel, edit, or dismiss at any time
- Flagged in DB: `created_by: "agent"`

### Why This Works

- Agent-0 sees a pattern: "every time X changes without Y, the build breaks" → **creates a gospel immediately, starts checking against it right now**
- If the gospel turns out to be wrong (user dismisses an alert triggered by it) → Agent-0 can soften or retire it
- If the gospel proves valuable over time → user can promote it to a human gospel
- Agent-0 learns from its own gospels: if an agent gospel causes 3+ false alerts, it auto-retires it

### Confidence Levels (Agent Gospels Only)

Agent-created gospels have a confidence level that affects how they trigger:

| Confidence | How It Triggers | When It's Set |
|------------|----------------|---------------|
| **HIGH** | Full alert, same as human gospel | Pattern seen 3+ times, or clear dependency chain |
| **MEDIUM** | Alert with note: "Agent-0 detected pattern (medium confidence)" | Pattern seen 2 times, or inferred dependency |
| **LOW** | Log only, no alert. Shown in widget under "observations" | First occurrence, or weak signal |

Confidence auto-adjusts:
- Pattern confirmed again → confidence goes UP
- User dismisses alert as false → confidence goes DOWN
- User confirms alert as valid → confidence goes UP, may promote to human gospel
- No relevant triggers for 30 days → confidence decays

## Gospel Lifecycle

### 1. Creation

**A. Human creates directly**
- Via widget: user types a gospel rule
- Via editing `gospels/*.md` files directly
- During onboarding confirmation: user adds rules during Phase 5
- Via API: working agent (Claude Code, etc.) submits on behalf of human
- These are immediately active, highest authority

**B. Agent-0 creates autonomously**
- Agent-0 detects a pattern, dependency, or risk during normal operation
- Creates the gospel immediately with appropriate confidence level
- Writes to `gospels/agent_gospels.md` + DB
- Starts checking against it from the next file change
- Logs: "Created gospel #12: [rule]. Reason: [evidence]. Confidence: [level]"
- No human approval needed — Agent-0 is doing its job

**C. Promotion (agent → human)**
- User sees an agent gospel in the widget and says "yes, this is important"
- Gospel gets promoted: `created_by` changes to "human"
- Agent-0 can no longer auto-edit or retire it
- Confidence becomes irrelevant — human gospels always trigger at full authority

### 2. Format

Each gospel has:

```
Gospel #: auto-incremented ID
Rule: the actual rule (one clear sentence)
Reason: why this rule exists (what happened, what evidence)
Category: code, architecture, process, goal, dependency
Scope: global, phase-specific, module-specific
Created: timestamp
Created by: human / agent
Confidence: high / medium / low (agent gospels only)
Status: active, retired
Last validated: timestamp
False alerts: count (how many times alerts from this gospel were dismissed)
Confirmed alerts: count (how many times alerts were acknowledged as valid)
```

**Markdown format** (in `gospels/` files):

Human gospels go in `gospels/human_gospels.md`:
```markdown
### Gospel #3 [HUMAN]
**Rule:** Never modify `core/memory/store.py` without running `tests/test_memory_integration.py`
**Reason:** Session W2671 — memory store change passed unit tests but broke integration. Lost 4 hours.
**Category:** dependency
**Scope:** module (core/memory/)
**Status:** active
```

Agent gospels go in `gospels/agent_gospels.md`:
```markdown
### Gospel #7 [AGENT | HIGH]
**Rule:** Changes to `core/cognitive/reasoning.py` typically require updates to `core/agency/control.py`
**Reason:** Observed 4 times — 3 out of 4 changes to reasoning.py without control.py updates led to issues.
**Category:** dependency
**Scope:** module (core/cognitive/, core/agency/)
**Status:** active
**Confidence:** high (4 observations, 3 confirmed)
**False alerts:** 1
**Confirmed alerts:** 3
```

### 3. Auto-Management (Agent Gospels)

Agent-0 actively manages its own gospels:

**Merging:** If two agent gospels cover overlapping patterns, Agent-0 merges them into one stronger gospel.

**Strengthening:** When a pattern is confirmed again, confidence goes up. Low → medium → high.

**Weakening:** When an alert is dismissed as false, confidence goes down. High → medium → low. If confidence drops to low AND false alerts > confirmed alerts → auto-retire.

**Auto-retirement triggers:**
- 3+ false alerts with 0 confirmed alerts → retired
- Referenced file/module no longer exists → retired
- Referenced phase is closed → retired (for phase-specific gospels)
- No relevant triggers in 60 days → retired with note "stale"

**Splitting:** If Agent-0 realizes a broad gospel should be more specific (e.g., "module X breaks" should really be "function Y in module X breaks"), it retires the broad one and creates a more specific one.

### 4. Human Override

The human always has final say:

- **Dismiss agent gospel** → immediately retired, logged
- **Edit agent gospel** → updated, confidence reset to medium
- **Promote agent gospel** → becomes human gospel, Agent-0 can no longer auto-manage it
- **Edit human gospel** → updated
- **Retire human gospel** → retired, Agent-0 cannot reactivate
- **Create human gospel** → immediately active, highest authority

All overrides happen via widget or direct file editing. Agent-0 detects file edits and syncs to DB.

### 5. Check Process

When `check_gospels` tool is called:

```
1. Load ALL active gospels from DB (human + agent)
2. For each gospel:
   a. Does this change touch files/modules in the gospel's scope?
   b. If yes, does the change comply with or violate the rule?
   c. If scope doesn't match, skip this gospel
3. Return:
   - Violations from human gospels → ALWAYS alert (high severity)
   - Violations from agent gospels:
     - HIGH confidence → alert (medium severity, note it's agent-detected)
     - MEDIUM confidence → alert (low severity)
     - LOW confidence → log only, no alert
   - Any warnings (partial matches, edge cases)
```

## Gospel Categories

| Category | What It Covers | Example |
|----------|---------------|---------|
| **code** | Specific code rules | "predict() must return a dict" |
| **dependency** | File/module coupling | "X and Y must change together" |
| **architecture** | System-level rules | "All LLM calls go through llm/client.py" |
| **process** | Workflow rules | "Run benchmarks before refactoring memory" |
| **goal** | Phase/project objectives | "Phase 16 goal is brain unification" |

## Scope Levels

| Scope | Applies To | Gospel Check Behavior |
|-------|-----------|----------------------|
| **global** | Every change | Always checked |
| **phase-specific** | Changes during a specific phase | Only checked while that phase is active |
| **module-specific** | Changes to specific files/folders | Only checked when those files are in the change set |

## Gospel Limits

- No hard limit on gospel count, but recommended: **under 30 active gospels** per project (human + agent combined)
- More than 30 means every change requires checking against too many rules → slower, more expensive
- If gospel count grows large, Agent-0 auto-merges or retires low-value agent gospels first
- Agent-0 prioritizes human gospels — if it needs to reduce count, agent gospels get retired first
- Gospels should be specific and actionable, not vague ("write good code" is not a gospel)

## Summary: Gospel Authority Chain

```
HUMAN GOSPEL (highest)
    → Always active, always alert on violation
    → Only human can edit/retire
    → Agent-0 can never touch these

AGENT GOSPEL - HIGH CONFIDENCE
    → Active, alerts on violation (medium severity)
    → Agent-0 can edit/retire based on evidence
    → Human can promote, edit, or dismiss

AGENT GOSPEL - MEDIUM CONFIDENCE
    → Active, alerts on violation (low severity)
    → Auto-adjusts based on confirmation/dismissal

AGENT GOSPEL - LOW CONFIDENCE
    → Active but log-only (no alerts)
    → Observation stage — watching for more evidence
    → Auto-retires if never confirmed
```

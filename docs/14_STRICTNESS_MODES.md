# Agent-0: Strictness Modes

## Overview

Strictness modes control how aggressively Agent-0 alerts and intervenes. Different work styles need different levels of oversight.

Three modes: **STRICT**, **NORMAL**, **LOOSE**.

User can switch modes anytime via the widget or API. Mode is stored in config and persisted between sessions.

## Mode Comparison

| Behavior | STRICT | NORMAL | LOOSE |
|----------|--------|--------|-------|
| Gospel violations | Alert (high) | Alert (high) | Alert (high) |
| Known regression patterns | Alert (high) | Alert (high) | Alert (medium) |
| Drift from phase goal | Alert after 1 unrelated change | Alert after 3 unrelated changes | Log only, no alert |
| Dependency risks | Alert (medium) | Alert (medium) | Log only |
| Session summary | Auto-generate at end | Auto-generate at end | On request only |
| Checkpoint frequency | Every 12 hours | Every 24 hours | Manual only |
| Question logging | Aggressive (log any uncertainty) | Moderate | Minimal |
| Change classification | Every change detailed | Every change classified | Batch classification |
| Debt tracking | Flag all patches immediately | Flag patches, note for review | Log only |
| Cost impact | Highest (more LLM calls) | Medium | Lowest |

## When to Use Each Mode

### STRICT
- Active phase work with clear goals
- Post-regression recovery (just fixed a big bug, don't want another)
- Before a release or milestone
- When working on critical/fragile modules
- When you WANT to be interrupted

### NORMAL (default)
- Day-to-day development
- Feature work with some exploration
- Most of the time

### LOOSE
- Exploratory prototyping
- Experimenting with new approaches
- Research spikes
- When you explicitly don't want to be interrupted
- "Let me work, just take notes"

## What NEVER Changes Between Modes

Regardless of strictness:
- **Gospel violations are ALWAYS alerted** — gospels are sacred
- **All changes are ALWAYS logged** — Agent-0 never stops watching
- **Knowledge is ALWAYS updated** — the source of truth is always maintained
- **Queries always get full answers** — mode only affects proactive behavior, not reactive

## Mode Switching

### Via Widget
Button or dropdown in the widget UI: STRICT / NORMAL / LOOSE

### Via API
```
POST /config/strictness
{
    "mode": "strict"
}
```

### Auto-Switching (optional, user can enable)
- If 3+ gospel suggestions are created in one session → suggest switching to STRICT
- If user dismisses 5+ alerts in a row → suggest switching to LOOSE
- If a checkpoint reveals high debt count → suggest switching to STRICT
- These are suggestions only — user confirms

## Configuration

```json
{
    "strictness": {
        "mode": "normal",
        "auto_switch_suggestions": true,
        "drift_threshold_strict": 1,
        "drift_threshold_normal": 3,
        "checkpoint_hours_strict": 12,
        "checkpoint_hours_normal": 24
    }
}
```

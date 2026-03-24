# Agent-0: Cost Management & Batching

## The Problem

Every file change triggers Agent-0. Each trigger involves at least one LLM API call (often 3-5 per ReACT loop iteration). Without controls:

- User saves a file 20 times in 10 minutes → 20 triggers → 60-100 API calls
- `git pull` brings in 200 changed files → 200 triggers → catastrophic
- Onboarding a large project (50k+ files) → thousands of calls
- Monthly cost could be hundreds of dollars for an active project

Agent-0 must be **cost-conscious by design**, not as an afterthought.

## Strategy 1: Debouncing

Don't react to every save. Wait for activity to settle.

```
File change detected
    → Start a debounce timer (default: 5 seconds)
    → If another change comes in within 5 seconds, reset the timer
    → When timer expires, process ALL accumulated changes as ONE batch

Example:
    10:00:01 — user saves file A → start timer
    10:00:03 — user saves file B → reset timer
    10:00:04 — user saves file A again → reset timer
    10:00:09 — timer expires → process {A, B} as one batch
```

Configurable debounce window:
- **Fast mode**: 2 seconds (during active coding, more responsive)
- **Normal mode**: 5 seconds (default)
- **Slow mode**: 15 seconds (during large operations like git pulls)

Auto-detection: if more than 10 files change within 2 seconds, switch to slow mode for that batch (likely a git operation, not manual editing).

## Strategy 2: Batching

When multiple files change in one debounce window, process them as a single batch — one LLM call, not N calls.

```
Single LLM call:
    "The following files changed in the last 5 seconds:
     1. core/cognitive/reasoning.py — [diff summary]
     2. core/agency/control.py — [diff summary]
     3. tests/test_reasoning.py — [diff summary]

     Classify these changes, check against current phase, and update records."
```

Batch size limit: if more than **20 files** change at once, split into batches of 20. Each batch is its own ReACT loop.

For massive changes (50+ files, e.g., branch switch), Agent-0 writes a single summary entry: "Branch switch detected: 150 files changed. High-level diff: [summary]." No per-file analysis for bulk operations.

## Strategy 3: Tiered Model Usage

Not every trigger needs the smartest (most expensive) model.

| Situation | Model Tier | Example Models | Cost |
|-----------|-----------|----------------|------|
| Simple classification | **Fast/Cheap** | Haiku, GPT-4o-mini, Gemini Flash | ~$0.001/call |
| Normal file change analysis | **Mid** | Sonnet, GPT-4o, Gemini Pro | ~$0.01/call |
| Deep reasoning (pattern matching, drift) | **Smart** | Opus, o1/o3, Gemini Ultra | ~$0.05/call |
| Onboarding | **Mid** | Sonnet, GPT-4o | Bulk processing |
| Query response | **Mid/Smart** | Depends on query complexity | On demand |

### How It Works

The ReACT loop starts with the **fast model** for initial classification:
1. Fast model reads the diff → classifies it (feature/bugfix/refactor/etc.)
2. If classification is "routine, on-track" → fast model writes the record → done. Cheap.
3. If classification flags potential issues (drift, gospel concern, pattern match) → escalate to mid/smart model for deeper reasoning.

This means ~70% of file changes are handled by the cheapest model. Only the interesting ones get the expensive treatment.

## Strategy 4: Token Budgets

Per-call token limits to prevent runaway costs:

| Call Type | Max Input Tokens | Max Output Tokens |
|-----------|-----------------|-------------------|
| Classification (fast) | 2,000 | 500 |
| Analysis (mid) | 4,000 | 1,000 |
| Deep reasoning (smart) | 8,000 | 2,000 |
| Query response | 6,000 | 1,500 |
| Onboarding batch | 4,000 | 1,000 |

Diffs are truncated to fit within token limits. If a diff is too large, Agent-0 summarizes the key changes rather than sending the entire diff.

## Strategy 5: Skip Rules

Some changes don't need LLM processing at all:

- **Auto-generated files**: `*.pyc`, `__pycache__/`, `.git/`, build artifacts → skip entirely
- **Lock files**: `package-lock.json`, `poetry.lock` → log "dependency update" without LLM
- **Agent-0's own files**: changes to `.agent0/` → skip (don't analyze yourself)
- **Binary files**: images, databases, compiled files → log "binary file changed" without LLM
- **Whitespace-only changes**: detect and skip

These are handled by the watcher before the ReACT loop even starts. Zero cost.

## Estimated Monthly Cost

For an active project (100 meaningful file changes per day):

| Component | Calls/Day | Model | Cost/Day | Cost/Month |
|-----------|-----------|-------|----------|------------|
| Classification | 100 | Fast | $0.10 | $3 |
| Escalated analysis | ~30 | Mid | $0.30 | $9 |
| Deep reasoning | ~5 | Smart | $0.25 | $7.50 |
| Queries | ~10 | Mid | $0.10 | $3 |
| **Total** | | | | **~$22.50/month** |

With debouncing and batching, the same 100 changes might collapse to 30-40 actual triggers, reducing cost further.

## Configuration

```json
{
    "cost": {
        "debounce_seconds": 5,
        "max_batch_size": 20,
        "bulk_threshold": 50,
        "model_tiers": {
            "fast": "claude-haiku-4-5",
            "mid": "claude-sonnet-4-6",
            "smart": "claude-opus-4-6"
        },
        "monthly_budget_cap": 50.00,
        "alert_at_percentage": 80
    }
}
```

When monthly budget hits the cap, Agent-0 switches to classification-only mode (fast model, no deep reasoning) and alerts the user.

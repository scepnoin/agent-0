# Agent-0: Testing Strategy

## Challenge

How do you test a sentinel agent? It's not a web app with request/response flows. It watches files, reasons with an LLM, and writes knowledge. The LLM is non-deterministic. The file system is unpredictable. Testing needs to account for this.

## Testing Layers

### Layer 1: Unit Tests (no LLM, no filesystem)

Test each tool's execution logic in isolation with mocked inputs.

```
tests/
├── unit/
│   ├── test_read_file.py
│   ├── test_read_diff.py
│   ├── test_list_files.py
│   ├── test_search_knowledge.py
│   ├── test_search_project.py
│   ├── test_get_state.py
│   ├── test_write_knowledge.py
│   ├── test_db_write.py
│   ├── test_db_query.py
│   ├── test_git_info.py
│   ├── test_check_gospels.py
│   ├── test_send_alert.py
│   ├── test_log_question.py
│   ├── test_create_checkpoint.py
│   ├── test_summarize_and_split.py
│   ├── test_debouncing.py
│   ├── test_batching.py
│   ├── test_indexer.py
│   ├── test_search_hybrid.py
│   └── test_config.py
```

What these test:
- Given a mock file, does `read_file` return correct content?
- Given a mock diff, does `read_diff` parse it correctly?
- Given mock markdown files + SQLite data, does `search_knowledge` return relevant results?
- Given a gospel rule and a change description, does `check_gospels` correctly identify violations?
- Does debouncing correctly merge rapid triggers?
- Does batching correctly group files?
- Does `summarize_and_split` correctly split a file at the threshold?

**No LLM calls.** Pure logic testing. Fast, deterministic, run on every change.

### Layer 2: Integration Tests (mock LLM, real filesystem)

Test the full flow with a mock LLM that returns predictable responses.

```
tests/
├── integration/
│   ├── test_file_change_flow.py      → Simulate file change → full ReACT loop
│   ├── test_query_flow.py            → Simulate query → full ReACT loop
│   ├── test_onboarding_flow.py       → Simulate first-run on a test project
│   ├── test_gospel_violation.py      → Change that violates a gospel → alert
│   ├── test_drift_detection.py       → Off-goal changes → drift alert
│   ├── test_bulk_changes.py          → 100 files change → bulk handling
│   ├── test_error_recovery.py        → API failure → queue → recovery
│   ├── test_checkpoint_creation.py   → Checkpoint flow
│   └── test_knowledge_persistence.py → Write → restart → read back
```

**Mock LLM approach:**
```python
class MockLLMClient:
    """Returns predictable responses based on trigger patterns."""

    def call(self, messages, tools):
        trigger = messages[-1]["content"]

        if "classify this change" in trigger:
            return MockResponse(tool_call=("db_write", {
                "table": "changes",
                "data": {"category": "bugfix"},
                "operation": "insert"
            }))

        if "check against gospels" in trigger:
            return MockResponse(text="No gospel violations found.")

        # ... pattern-based mock responses
```

These tests use a **real filesystem** (temp directories with test project structures) and **real SQLite** but a **mock LLM**. They verify:
- The full ReACT loop executes correctly
- Knowledge files are created/updated correctly
- Alerts fire when they should
- Debouncing and batching work end-to-end
- Recovery from failures works

### Layer 3: Scenario Tests (mock LLM, scripted scenarios)

Full day-in-the-life simulations:

```
tests/
├── scenarios/
│   ├── test_scenario_normal_day.py     → 20 file changes, some drift, one gospel violation
│   ├── test_scenario_rabbit_hole.py    → Start feature → find bug → chase bug → drift alert
│   ├── test_scenario_branch_switch.py  → 200 files change at once → bulk handling
│   ├── test_scenario_api_outage.py     → API dies mid-session → queue → recovery
│   └── test_scenario_onboarding.py     → Full onboarding of a sample project
```

These create a test project directory, simulate a sequence of file changes over time, and verify that Agent-0 correctly:
- Tracked everything
- Detected drift at the right time
- Fired the right alerts
- Wrote accurate knowledge
- Handled edge cases

### Layer 4: Live Tests (real LLM, controlled project)

Run against a real LLM with a small, controlled test project. These are expensive (API calls) so they run manually, not in CI.

```
tests/
├── live/
│   ├── test_live_classification.py    → Real LLM classifies real diffs correctly
│   ├── test_live_gospel_check.py      → Real LLM checks real gospel violations
│   ├── test_live_query_response.py    → Real LLM answers queries accurately
│   └── test_live_onboarding.py        → Real LLM onboards a small test project
```

Purpose: verify that the system prompt produces correct behavior with the actual LLM. Catch prompt regressions.

## Test Project Fixtures

A small, controlled project used for testing:

```
tests/fixtures/test_project/
├── README.md
├── main.py
├── config.py
├── core/
│   ├── module_a.py
│   ├── module_b.py        → depends on module_a
│   └── module_c.py
├── tests/
│   └── test_module_a.py
└── docs/
    └── ROADMAP.md
```

With predefined:
- Gospels: "module_a and module_b must change together"
- Phases: "Phase 1: refactor module_c"
- Known patterns: "last time module_b was changed alone, tests broke"

## What We DON'T Test

- The LLM's reasoning quality (that's the LLM provider's responsibility)
- The Tauri widget UI (separate test suite, standard web testing)
- Cross-platform file watching (watchdog's responsibility, covered by their tests)

## CI Pipeline

```
On every commit:
  1. Unit tests (fast, no LLM, <30 seconds)
  2. Integration tests (mock LLM, <2 minutes)
  3. Scenario tests (mock LLM, <5 minutes)

Manual (before release):
  4. Live tests (real LLM, ~10 minutes, costs ~$1)
  5. Cross-platform testing (Windows, Mac, Linux)
```

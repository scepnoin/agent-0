# Agent-0: ReACT Loop & Tools

## Why ReACT?

ReACT (Reasoning + Acting) is the right pattern for Agent-0 because:

- **Simple** — Think, act, observe, repeat. No complex orchestration graphs.
- **Transparent** — Every step is visible: what it thought, what it did, what it saw.
- **Low hallucination** — Grounding reasoning in observations (tool results) at every step.
- **Lightweight scaffolding** — Easy to implement from scratch in pure Python, no frameworks needed.

Agent-0 is NOT built on LangChain, LangGraph, or any heavy framework. It's a simple ReACT loop in pure Python calling the LLM API directly.

## The Loop

```
TRIGGER (file change detected OR query received)
    │
    ▼
┌─────────────────────────────────────┐
│  THOUGHT: LLM reasons about what   │
│  happened and what to do next       │
│                                     │
│  ACTION: LLM calls a tool           │
│                                     │
│  OBSERVATION: Tool returns result   │
│                                     │
│  → Loop back to THOUGHT             │
│  → Until: DONE (no more actions)    │
└─────────────────────────────────────┘
    │
    ▼
IDLE (wait for next trigger)
```

Max iterations per trigger: configurable (default: 10). Prevents runaway loops.

## Example: File Change Flow

```
TRIGGER: watcher detects core/cognitive/reasoning.py changed

THOUGHT: "A file changed in the project. Let me read the diff."
ACTION:  read_diff("core/cognitive/reasoning.py")
OBSERVATION: "Lines 45-52 changed: retry logic removed from reasoning loop"

THOUGHT: "This is a code change in a core module. Let me check what phase we're in."
ACTION:  get_state()
OBSERVATION: "Phase 16G is active. Goal: unify brain architecture."

THOUGHT: "Removing retry logic doesn't seem related to Phase 16G. Let me check
           if this matches any past patterns."
ACTION:  search_knowledge("retry logic removed cognitive")
OBSERVATION: "Match found: Session 2026-02-15 — similar retry removal in
              cognitive module caused regression in build pipeline (W2671)"

THOUGHT: "This is drift from Phase 16G AND it matches a past regression pattern.
           I need to update my records and alert the user."
ACTION:  write_knowledge("sessions/2026-03-14.md", append,
           "Retry logic removed from cognitive/reasoning.py - unrelated to
            Phase 16G - WARNING: similar change caused regression in W2671")
ACTION:  db_write("changes", {file: "core/cognitive/reasoning.py",
           category: "refactor", phase: "16G", drift: true})
ACTION:  send_alert("Drift: retry logic removed from cognitive module.
           Not related to Phase 16G goal. Similar change caused regression
           during W2671 — check build pipeline.")

DONE → idle
```

## Example: Query Flow

```
TRIGGER: user types in widget "what's the state of phase 16?"

THOUGHT: "User wants to know about Phase 16. Let me search my knowledge."
ACTION:  search_knowledge("phase 16 state progress")
OBSERVATION: [relevant chunks from phases/phase_16.md, sessions, changes]

THOUGHT: "Let me also check open items linked to Phase 16."
ACTION:  db_query("SELECT * FROM open_items WHERE linked_phase = 16")
OBSERVATION: "3 open bugs, 1 untested change, 2 debt items"

THOUGHT: "I have enough to answer."
RESPONSE: "Phase 16G is active. Goal: unify brain architecture.
            Progress: 60% — 3 modules migrated, 2 remaining.
            Open issues: 3 bugs, 1 untested change in cognitive module,
            2 patches needing root-cause fixes. Last activity: 2 hours ago,
            retry logic was removed (flagged as potential regression risk)."

DONE → idle
```

## Agent-0 Tool Set

Minimal. Each tool is a Python function with a JSON schema the LLM can call.

### Reading Tools

#### 1. `read_file`
Read any file from the project or Agent-0's own knowledge.
```json
{
    "name": "read_file",
    "description": "Read the contents of a file. Use for project files or Agent-0 knowledge files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to project root"},
            "line_start": {"type": "integer", "description": "Optional: start reading from this line"},
            "line_end": {"type": "integer", "description": "Optional: stop reading at this line"}
        },
        "required": ["path"]
    }
}
```

#### 2. `read_diff`
Read the diff of a changed file (what changed, not the whole file).
```json
{
    "name": "read_diff",
    "description": "Read the diff/changes for a file that was just modified. Shows what was added, removed, or changed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path that changed"}
        },
        "required": ["path"]
    }
}
```

#### 3. `list_files`
List files in a directory.
```json
{
    "name": "list_files",
    "description": "List files and folders in a directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path relative to project root"},
            "pattern": {"type": "string", "description": "Optional glob pattern to filter (e.g. '*.py')"}
        },
        "required": ["path"]
    }
}
```

#### 4. `search_knowledge`
Hybrid search across Agent-0's own markdown files and database.
```json
{
    "name": "search_knowledge",
    "description": "Search Agent-0's knowledge base using hybrid search (semantic + keyword). Returns relevant chunks from markdown files and database records.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "scope": {"type": "string", "enum": ["all", "gospels", "phases", "sessions", "patterns", "debt", "modules"], "description": "Optional: limit search to specific knowledge type"}
        },
        "required": ["query"]
    }
}
```

#### 5. `get_state`
Shortcut to read the current project state.
```json
{
    "name": "get_state",
    "description": "Get the current project state — what's active, what's open, what phase is in progress. Reads state/current.md.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
```

### Writing Tools

#### 6. `write_knowledge`
Write, append, or update a markdown file in Agent-0's knowledge system.
```json
{
    "name": "write_knowledge",
    "description": "Write to Agent-0's knowledge files. Can create new files, append to existing, or overwrite. Auto-triggers re-indexing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to .agent0/ (e.g. 'sessions/2026-03-14.md')"},
            "content": {"type": "string", "description": "Content to write"},
            "mode": {"type": "string", "enum": ["create", "append", "overwrite"], "description": "Write mode"}
        },
        "required": ["path", "content", "mode"]
    }
}
```

#### 7. `db_write`
Write structured data to SQLite.
```json
{
    "name": "db_write",
    "description": "Insert or update a record in Agent-0's SQLite database.",
    "input_schema": {
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Table name (changes, phases, gospels, open_items, sessions, alerts)"},
            "data": {"type": "object", "description": "Key-value pairs to insert/update"},
            "operation": {"type": "string", "enum": ["insert", "update"], "description": "Insert new or update existing"}
        },
        "required": ["table", "data", "operation"]
    }
}
```

#### 8. `db_query`
Query structured data from SQLite.
```json
{
    "name": "db_query",
    "description": "Query Agent-0's SQLite database. Returns matching records.",
    "input_schema": {
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Table name"},
            "filter": {"type": "object", "description": "Key-value filter conditions"},
            "limit": {"type": "integer", "description": "Max records to return (default 20)"}
        },
        "required": ["table"]
    }
}
```

### Communication Tools

#### 9. `send_alert`
Send a notification to the user via the desktop widget.
```json
{
    "name": "send_alert",
    "description": "Send an alert/ping to the user via the desktop widget.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Alert message to display"},
            "type": {"type": "string", "enum": ["drift", "pattern", "debt", "gospel_violation", "risk", "info"], "description": "Alert category"},
            "severity": {"type": "string", "enum": ["low", "medium", "high"], "description": "How urgent"}
        },
        "required": ["message", "type"]
    }
}
```

#### 10. `log_question`
Save a question for the human to answer later.
```json
{
    "name": "log_question",
    "description": "Log a question that Agent-0 wants to ask the human. Stored for next time the human checks in.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask"},
            "context": {"type": "string", "description": "Why Agent-0 is asking this"}
        },
        "required": ["question"]
    }
}
```

### Git Tools

#### 11. `git_info`
Read git state — log, status, branches, blame, detect reverts.
```json
{
    "name": "git_info",
    "description": "Read git information for the project. Commit history, current branch, status, blame, detect reverts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["log", "status", "branch", "blame", "diff_staged"], "description": "What git info to retrieve"},
            "path": {"type": "string", "description": "Optional: specific file for blame/log"},
            "limit": {"type": "integer", "description": "Optional: number of log entries (default 10)"}
        },
        "required": ["action"]
    }
}
```

### Project Search Tools

#### 12. `search_project`
Search the actual project codebase (not Agent-0's knowledge — the real code).
```json
{
    "name": "search_project",
    "description": "Search the project codebase for text/patterns. Like grep — find where functions are used, where imports come from, where strings appear. Searches project files, NOT Agent-0 knowledge files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text or regex pattern to search for"},
            "file_pattern": {"type": "string", "description": "Optional: glob filter (e.g. '*.py', 'core/**/*.py')"},
            "max_results": {"type": "integer", "description": "Max matches to return (default 20)"}
        },
        "required": ["query"]
    }
}
```

### Gospel Tools

#### 13. `check_gospels`
Check a change or action against ALL active gospel rules.
```json
{
    "name": "check_gospels",
    "description": "Check a change or action against ALL active gospel rules. Returns any violations or warnings. This is a dedicated gospel-check — more thorough than general search_knowledge.",
    "input_schema": {
        "type": "object",
        "properties": {
            "change_description": {"type": "string", "description": "Description of what changed or is about to happen"},
            "files_affected": {"type": "string", "description": "Which files were changed"}
        },
        "required": ["change_description"]
    }
}
```

### Maintenance Tools

#### 14. `create_checkpoint`
Create a point-in-time snapshot of the entire project state.
```json
{
    "name": "create_checkpoint",
    "description": "Create a timestamped checkpoint — a coherent summary of the entire project state right now. Useful for returning after time away.",
    "input_schema": {
        "type": "object",
        "properties": {
            "trigger": {"type": "string", "enum": ["manual", "scheduled", "milestone"], "description": "Why this checkpoint is being created"},
            "notes": {"type": "string", "description": "Optional: additional context for the checkpoint"}
        },
        "required": ["trigger"]
    }
}
```

#### 15. `summarize_and_split`
Manage large markdown files — summarize, archive old content, start fresh.
```json
{
    "name": "summarize_and_split",
    "description": "When a markdown file gets too large: summarize the older content, archive it to a new file, and start the current file fresh with a reference to the archive. Prevents knowledge files from growing unbounded.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the markdown file that's too large"},
            "max_lines": {"type": "integer", "description": "Threshold — split when file exceeds this (default 200)"}
        },
        "required": ["path"]
    }
}
```

## Tool Count: 15

15 tools, organized by purpose. Each does one thing. The reasoning happens in the LLM's thinking, not in the tools.

| Category | Tools | Purpose |
|----------|-------|---------|
| **Reading** | `read_file`, `read_diff`, `list_files` | See project files and changes |
| **Knowledge Search** | `search_knowledge`, `get_state` | Search Agent-0's own brain |
| **Project Search** | `search_project` | Search the actual codebase |
| **Writing** | `write_knowledge`, `db_write` | Write to markdown + SQLite |
| **Querying** | `db_query` | Query structured data |
| **Git** | `git_info` | Understand commits, branches, reverts |
| **Gospels** | `check_gospels` | Validate against sacred rules |
| **Communication** | `send_alert`, `log_question` | Talk to the human |
| **Maintenance** | `create_checkpoint`, `summarize_and_split` | Keep knowledge system healthy |

## System Prompt (Core)

The LLM is given a focused system prompt that defines its role:

```
You are Agent-0, a sentinel agent bonded to this project.

Your ONLY job is to watch, track, remember, and speak up.
You do NOT write project code. You do NOT fix bugs.
You track what happens and maintain the source of truth.

When a file changes, you:
1. Read the diff
2. Classify the change (feature, bugfix, refactor, patch, test, config)
3. Check it against current phase goals (drift detection)
4. Check it against known patterns (has this happened before?)
5. Check it against gospels (does this violate any rules?)
6. Update your knowledge (markdown + database)
7. Alert the user if needed

When queried, you:
1. Search your knowledge
2. Give a concise, contextual answer
3. Never dump raw files — synthesize

You think step by step. You use tools one at a time.
You write after every observation. You never hold too much in context.

Current project: {project_name}
Current phase: {current_phase}
Active gospels: {gospel_count}
```

## Implementation: Pure Python, No Frameworks

```python
# Pseudocode — the core ReACT loop

def react_loop(trigger, context, max_iterations=10):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": trigger}
    ]

    for i in range(max_iterations):
        response = llm_client.call(
            messages=messages,
            tools=TOOL_SCHEMAS
        )

        # If LLM wants to use a tool
        if response.has_tool_call:
            tool_name = response.tool_call.name
            tool_args = response.tool_call.arguments
            result = execute_tool(tool_name, tool_args)

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "tool", "content": result})
            continue

        # If LLM is done (no tool call, just text)
        else:
            return response.text

    return "Max iterations reached."
```

No LangChain. No LangGraph. No agent framework. Just a loop, an LLM, and 15 tools.

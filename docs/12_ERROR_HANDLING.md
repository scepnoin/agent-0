# Agent-0: Error Handling & Edge Cases

## Design Philosophy

Agent-0 should be **resilient, not fragile**. When things go wrong, it degrades gracefully — never crashes silently, never loses knowledge, never enters an unrecoverable state.

**Key patterns:** Retry with exponential backoff (3 attempts: 2s, 5s, 15s). Per-thread DB connections. Pending trigger queue for failed LLM calls. Global Flask error handler returning JSON.

Core rule: **always write what you know before failing.** If Agent-0 is mid-processing and something breaks, it saves whatever it has before shutting down.

## Edge Cases & How to Handle Them

### 1. LLM API Is Down / Unreachable

**Scenario:** Anthropic/OpenAI/Google API returns errors or times out.

**Handling:**
- Retry with exponential backoff (3 attempts: 2s, 5s, 15s)
- If all retries fail:
  - Queue the trigger (file change) in a local buffer (SQLite table: `pending_triggers`)
  - Switch widget status to "OFFLINE — queuing changes"
  - Continue watching and queuing — no changes are lost
  - When API comes back, process the queue in order (batched)
- Never silently drop a file change

### 2. API Key Invalid / Out of Credits

**Scenario:** API returns 401 (invalid key) or 429/402 (quota exceeded).

**Handling:**
- Alert user immediately via widget: "API key invalid" or "API credits exhausted"
- Switch to queue mode (same as API down)
- For quota exceeded: show estimated wait time if rate-limited, or prompt user to add credits
- Agent-0 continues watching and queuing — no data lost

### 3. Massive File Changes (Branch Switch / Git Pull)

**Scenario:** 200+ files change within 1-2 seconds.

**Handling:**
- Auto-detect bulk operation (>50 files in <5 seconds)
- Switch to bulk mode:
  - Do NOT process each file individually
  - Read the git log to understand what happened: `git_info("log", limit=5)`
  - Write a single summary entry: "Branch switch from X to Y. 200 files changed. Key areas affected: [list top-level directories]"
  - Update `state/current.md` with new branch context
  - Skip per-file classification for this batch
- Return to normal mode after bulk processing

### 4. Project Folder Deleted / Moved / Renamed

**Scenario:** The watched folder no longer exists.

**Handling:**
- Watcher raises an error immediately
- Alert user: "Project folder not found at {path}. Agent-0 paused."
- Enter paused state — no processing, no queuing
- Widget shows: "PAUSED — project folder missing"
- When user reconfigures the path (via widget settings), Agent-0:
  - Checks if `.agent0/` exists at the new path
  - If yes: resume with existing knowledge
  - If no: start onboarding

### 5. Agent-0 Knowledge Corrupted

**Scenario:** SQLite database is corrupted, or critical .md files are missing/broken.

**Handling:**
- On startup, Agent-0 runs a health check:
  - Can SQLite be opened and queried?
  - Do critical files exist? (`state/current.md`, `gospels/` folder)
  - Is the index intact?
- If corruption detected:
  - Alert user: "Knowledge database corrupted. Options: rebuild index / restore from checkpoint"
  - **Rebuild index**: re-index all existing .md files into SQLite (no data lost if .md files are intact)
  - **Restore from checkpoint**: roll back DB to last checkpoint state
  - **Full re-onboard**: last resort — wipe .agent0/ and start fresh
- Automatic backups: Agent-0 backs up `agent0.db` every 24 hours (keep last 3 backups)

### 6. Rapid Saves (Human Editing Fast)

**Scenario:** User saves the same file 10 times in 30 seconds (normal editing behavior).

**Handling:**
- Debouncing handles this (see 11_COST_AND_BATCHING.md)
- Only the LAST state of the file matters — Agent-0 diffs against the state before the first save in the burst, not intermediate saves
- One trigger, one LLM call, one record

### 7. File Watcher Misses Events

**Scenario:** OS-level file watcher drops events (can happen under heavy load on some OS).

**Handling:**
- Periodic reconciliation: every 5 minutes, Agent-0 does a quick scan of file modification timestamps against its last known state
- If it finds files that changed but weren't caught by the watcher, it processes them as a batch
- This is a safety net, not the primary mechanism

### 8. LLM Hallucination in Reasoning

**Scenario:** The LLM invents a pattern that doesn't exist, or claims a gospel was violated when it wasn't.

**Handling:**
- **Grounding rule in system prompt**: "Never claim something without tool evidence"
- The `check_gospels` tool returns the actual gospel text — the LLM must match against real content, not memory
- `search_knowledge` returns actual chunks — the LLM reasons on real data, not assumptions
- If Agent-0 sends a false alert, the user dismisses it, and the dismissal + reason is logged
- Over time, false alert patterns can be identified and prompt can be tuned

### 9. Recursive Loop (Agent-0 Triggers Itself)

**Scenario:** Agent-0 writes a .md file → watcher detects the change → triggers Agent-0 again → infinite loop.

**Handling:**
- **Critical**: the watcher IGNORES all changes inside `.agent0/` folder
- This is a hard rule in the watcher configuration, not a soft filter
- Agent-0 never watches its own knowledge directory

### 10. Onboarding Interrupted

**Scenario:** User closes Agent-0 mid-onboarding, or API fails during onboarding.

**Handling:**
- Onboarding writes after every step (write-as-you-go pattern)
- If interrupted, everything written so far is preserved
- On next startup, Agent-0 detects incomplete onboarding:
  - Checks which phases completed (e.g., structure scan done, code reading partially done)
  - Resumes from where it left off, not from scratch
- Progress is tracked in `agent0.db` table: `onboarding_progress`

### 11. Very Large Files

**Scenario:** User has a 50,000-line Python file or a massive JSON/CSV.

**Handling:**
- read_file and read_diff have line limits
- For diffs: if diff exceeds 500 lines, truncate and summarize: "Large change in {file}: {first 50 lines of diff}... (truncated, {total} lines changed)"
- For onboarding reads: chunk large files, read in sections
- Never send an entire large file in one LLM call

### 12. Concurrent Access

**Scenario:** Two tools (e.g., Claude Code via MCP + user via widget) query Agent-0 simultaneously.

**Handling:**
- Flask handles concurrent requests natively
- SQLite: use WAL mode (Write-Ahead Logging) for concurrent reads
- Writes are serialized through a single write queue — no race conditions
- Each query gets its own ReACT loop instance with its own message history

## Recovery Priority

When multiple things go wrong, priority order:

1. **Preserve knowledge** — never lose what's been written
2. **Queue triggers** — never drop a file change event
3. **Alert the user** — tell them something is wrong
4. **Degrade gracefully** — classification-only mode, queue mode, paused mode
5. **Auto-recover** — when the problem resolves, process the queue and resume

## Health Check (runs on startup + every hour)

```
1. Can reach LLM API? → yes/no
2. SQLite DB intact? → yes/no
3. Critical .md files present? → yes/no
4. Index up to date? → yes/no
5. Watcher running? → yes/no
6. Pending triggers in queue? → count
7. Last successful processing? → timestamp
8. Monthly cost so far? → amount
```

Results displayed in widget health dashboard.

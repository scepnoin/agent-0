# Agent-0: Build Plan

## Approach: Fast Prototype First

Build the minimum needed to prove Agent-0 works. Plug it into a real project. See if it's useful. Then harden.

**Not building full:** Tiered model escalation, strictness modes, auto-splitting, gospel confidence auto-adjustment.
**Building full:** Core loop, watcher, tools, knowledge system, Flask API, one model tier.
**Building skeleton:** Tauri desktop widget, MCP server — architecture in place from day one, fill in details later.

## What We Borrow

| Component | Library | License |
|-----------|---------|---------|
| Memory/search system | memsearch | MIT |
| File watching | watchfiles (or watchdog) | MIT (Apache 2.0) |
| ReACT loop reference | mattambrogi/agent-implementation | Reference only |
| Hybrid search approach | sqlite-hybrid-search | Reference approach |
| Embeddings | Google Gemini `gemini-embedding-001` | Free (1,500 req/day) |
| API framework | Flask | BSD-3 |
| Database | SQLite (built-in) + sqlite-vec | Public domain / MIT |

## Build Phases

---

### PHASE 1: Skeleton (Day 1)
**Goal:** Project scaffolding, config, can start up and shut down.

Build:
```
backend/
├── main.py              → Entry point (starts Flask, prints "Agent-0 running")
├── config.py            → Load/save config (project path, API keys, provider)
└── requirements.txt     → All dependencies
```

Tasks:
- [ ] Create full folder structure (backend/, tools/, memory/, desktop/, etc.)
- [ ] Write config.py — load from `.agent0/config.json`, create if not exists
- [ ] Write main.py — parse args, load config, start Flask server
- [ ] Write requirements.txt
- [ ] Init Tauri project in desktop/ — `npm create tauri-app`
- [ ] Basic Tauri window — small floating widget, shows "Agent-0" + status text
- [ ] Tauri ↔ Python — Tauri launches Python backend on startup, kills on close
- [ ] Basic HTML/CSS for widget — status indicator, empty query input, empty alert area
- [ ] Test: `python main.py --project /path/to/folder` starts without error
- [ ] Test: Tauri app opens, shows widget window, backend starts

---

### PHASE 2: LLM Client (Day 1-2)
**Goal:** Can call LLM API and get a response with tool use.

Build:
```
backend/
├── llm/
│   └── client.py        → Call Anthropic/OpenAI/Google with tool schemas
```

Tasks:
- [ ] LLM client abstraction — one interface, three providers
- [ ] Tool schema format — define how tools are registered
- [ ] Test: send a message with tools, get a tool_call response back
- [ ] Test: send tool_result, get final text response
- [ ] Embedding client — call `gemini-embedding-001`, return vector

---

### PHASE 3: Tool Registry + Core Tools (Day 2-3)
**Goal:** Tools can be registered, called, and return results.

Build:
```
backend/
├── tools/
│   ├── __init__.py      → Tool registry (register, list, execute)
│   ├── read_file.py
│   ├── read_diff.py
│   ├── list_files.py
│   ├── write_knowledge.py
│   ├── db_write.py
│   ├── db_query.py
│   └── get_state.py
```

Tasks:
- [ ] Tool registry — decorator or register function, auto-generates JSON schemas
- [ ] Implement 7 core tools (read, write, query)
- [ ] Test: each tool works independently
- [ ] Test: tool registry returns correct schemas for LLM

---

### PHASE 4: ReACT Loop (Day 3-4)
**Goal:** The core agent loop works — think, act, observe, repeat.

Build:
```
backend/
├── agent/
│   ├── loop.py          → ReACT loop
│   └── system_prompt.py → System prompt builder
```

Tasks:
- [ ] ReACT loop — messages list, call LLM, detect tool_call, execute, feed back
- [ ] Max iterations (default 10)
- [ ] System prompt builder — template with dynamic context injection
- [ ] Test: trigger loop with "a file changed: X" → loop classifies and writes record
- [ ] Test: trigger loop with query → loop searches and responds

---

### PHASE 5: Database + Knowledge (Day 4-5)
**Goal:** SQLite schema in place, knowledge can be written and searched.

Build:
```
backend/
├── memory/
│   ├── db.py            → SQLite setup, CRUD operations, schema
│   ├── store.py         → Markdown file read/write/append
│   ├── indexer.py       → Embed chunks, store in sqlite-vec, FTS5 indexing
│   └── search.py        → Hybrid search (vector + keyword + fusion)
```

Tasks:
- [ ] SQLite schema — create all tables (changes, phases, gospels, open_items, sessions, alerts, memory_index)
- [ ] Markdown store — create, append, overwrite, read
- [ ] Indexer — chunk markdown by heading/paragraph, embed via Gemini API, store vectors
- [ ] FTS5 setup — virtual table for keyword search
- [ ] Hybrid search — vector similarity + FTS5 BM25 + score fusion
- [ ] Test: write markdown → index → search → get relevant results
- [ ] Use memsearch as reference/borrowed code where applicable

---

### PHASE 6: File Watcher (Day 5-6)
**Goal:** Agent-0 detects file changes and triggers the ReACT loop.

Build:
```
backend/
├── watcher/
│   └── watcher.py       → File system watcher with debouncing
```

Tasks:
- [ ] watchfiles/watchdog integration — watch project folder
- [ ] Ignore patterns (.agent0/, __pycache__, .git, venv, node_modules, *.pyc, etc.)
- [ ] Debouncing — 5 second window, batch changes
- [ ] Diff generation — what changed between old and new file state
- [ ] On trigger: build trigger message → feed to ReACT loop
- [ ] Test: save a file → Agent-0 wakes, processes, writes knowledge, goes idle

---

### PHASE 7: Remaining Tools (Day 6-7)
**Goal:** All 15 tools working.

Build:
```
backend/
├── tools/
│   ├── search_knowledge.py
│   ├── search_project.py
│   ├── git_info.py
│   ├── check_gospels.py
│   ├── send_alert.py
│   ├── log_question.py
│   ├── create_checkpoint.py
│   └── summarize_and_split.py
```

Tasks:
- [ ] search_knowledge — wraps memory/search.py hybrid search
- [ ] search_project — grep/search actual project files
- [ ] git_info — shell out to git commands
- [ ] check_gospels — load all active gospels, check change against each
- [ ] send_alert — for now: print to console + store in DB (no widget yet)
- [ ] log_question — store in DB
- [ ] create_checkpoint — gather state, write timestamped checkpoint .md
- [ ] summarize_and_split — detect large files, split at threshold
- [ ] Test: each tool independently

---

### PHASE 8: Flask API (Day 7-8)
**Goal:** External tools can query Agent-0.

Build:
```
backend/
├── api/
│   ├── server.py        → Flask routes
│   └── mcp.py           → MCP server (working skeleton)
```

Tasks:
- [ ] Flask routes: /health, /state, /brief, /query, /gospels, /alerts, /checkpoint
- [ ] /query — accepts free-form question, runs ReACT loop, returns response
- [ ] /brief — generates handoff brief for new agent sessions
- [ ] CORS for localhost (Tauri widget calls this)
- [ ] MCP server skeleton — expose Agent-0 as an MCP tool provider
- [ ] MCP tools: `agent0_query`, `agent0_brief`, `agent0_state`, `agent0_gospels`
- [ ] Test: curl Flask endpoints, get correct responses
- [ ] Test: Claude Code (or similar) connects to MCP server and can query Agent-0
- [ ] Wire Tauri widget to Flask API — query input sends to /query, displays response
- [ ] Wire Tauri alerts — poll /alerts endpoint, display new alerts in widget

---

### PHASE 9: Onboarding (Day 8-9)
**Goal:** Agent-0 can bond to a new project and learn it.

Build:
```
backend/
├── agent/
│   └── onboarding.py    → First-run deep scan
```

Tasks:
- [ ] Phase 1: Scan structure — walk directory, map files, write structure.md
- [ ] Phase 2: Read key docs — batch by batch, write-as-you-go
- [ ] Phase 3: Read code — module by module, write-as-you-go
- [ ] Phase 4: Reason — synthesize understanding from own notes
- [ ] Phase 5: Confirm — present summary (print to console for now)
- [ ] Resume from interruption — track onboarding progress in DB
- [ ] Test: point at a small test project → full onboarding completes

---

### PHASE 10: Integration Test on a Real Project (Day 9-10)
**Goal:** Plug Agent-0 into a real-world project and see if it works.

Tasks:
- [ ] Run onboarding on a large project (expect this to take a while)
- [ ] Monitor: does it build accurate understanding?
- [ ] Make some changes to the project — does Agent-0 detect and classify correctly?
- [ ] Ask Agent-0 questions via /query — are answers useful?
- [ ] Identify what's broken, what's noisy, what's missing
- [ ] Tune system prompt based on real behavior
- [ ] Document findings

---

## Post-Prototype (Only If Phase 10 Proves Value)

| Feature | Priority |
|---------|----------|
| Tauri widget polish (full UI, health dashboard) | High — skeleton is in, needs flesh |
| Gospel confidence system (auto-create/manage) | High — core feature |
| MCP server polish (full tool suite) | High — skeleton is in, needs more tools |
| Tiered model escalation (fast → mid → smart) | Medium — cost optimization |
| Strictness modes | Medium |
| Checkpoint scheduling | Low |
| Auto-split large files | Low |
| Multi-provider embedding support | Low |
| Cross-platform testing | Low |
| Full Tauri + Python packaging (.exe / .dmg) | Low (after everything works) |

---

## Estimated Timeline

| Phase | What | Days |
|-------|------|------|
| 1 | Skeleton | 1 |
| 2 | LLM Client | 1 |
| 3 | Core Tools | 1-2 |
| 4 | ReACT Loop | 1-2 |
| 5 | Database + Knowledge | 1-2 |
| 6 | File Watcher | 1-2 |
| 7 | Remaining Tools | 1-2 |
| 8 | Flask API | 1-2 |
| 9 | Onboarding | 1-2 |
| 10 | Real Project Test | 1-2 |
| **Total** | **Working Prototype** | **~10-15 days** |

## Dev Rules

1. **Keep it simple** — if it works ugly, it works. Polish later.
2. **Test on real data early** — don't wait until Phase 10 to try it on a real project.
3. **One model tier for prototype** — mid tier only (Sonnet/GPT-4o/Gemini Pro). No escalation logic yet.
4. **Console output for alerts** — no widget yet. Print to terminal.
5. **No premature abstraction** — if we only support one provider for now, don't build a provider framework. Just make it work.
6. **Write-as-you-go pattern** — Agent-0's own development should follow the pattern. Write down what works and what doesn't.

# V4 Action Plan — Get Agent-0 Done

## Priority: ONBOARDING QUALITY (everything else is secondary)

## What's Already Built & Working
- [x] File watcher with real diffs (snapshots)
- [x] LLM classification of changes
- [x] Session/DB logging
- [x] ReACT loop with 16 tools
- [x] Flask API (12 endpoints)
- [x] MCP server
- [x] Tauri desktop app with folder picker
- [x] AST code analyzer (classes, functions, imports, dependencies)
- [x] Hybrid search (FTS5 + vector)
- [x] Tiered LLM (fast/mid/smart)
- [x] Project switching from UI

## What Needs Building (in order)

### Step 1: V4 Onboarding — Read Everything Thoroughly
The brain. The #1 priority. Nothing else matters until this works.

**Sub-tasks:**
1. Read EVERY doc fully (no truncation under 20K chars)
2. Create structured knowledge files by TOPIC not by batch
3. Read ALL core sub-modules (semantic, control, deep_thinking, etc.)
4. AST analysis already works — integrate results into onboarding knowledge
5. Extract gospels from ALL sources (code patterns + docs + CLAUDE.md if exists)
6. Store raw facts in DB alongside markdown writeups
7. Take as long as needed — hours is fine for large projects

### Step 2: Gospel Derivation From Code
Currently gospels only come from CLAUDE.md. Need:
- "config.py has 155 dependents — changes affect entire system" (from AST)
- "plan_executor.py and planner.py always change together" (from change history)
- "Never modify core/cognitive without full test suite" (from known issues docs)
- Rules from any doc that contains constraints/lessons/rules

### Step 3: Query Quality
Make sure Agent-0 can answer ANY question about the project:
- "What changed yesterday?"
- "What depends on config.py?"
- "What are the open issues?"
- "What was W2790 about?"
- "What's the architecture of the agency module?"

### Step 4: Change Tracking Quality
When a file changes:
- Real diff (already working)
- Accurate classification (already working)
- Check against gospels (needs improvement)
- Update knowledge (needs improvement — should update module .md if relevant)

### Step 5: Polish (LAST)
- Tauri auto-starts backend
- Icon
- MSI installer
- Cost dashboard in UI
- Session management cleanup

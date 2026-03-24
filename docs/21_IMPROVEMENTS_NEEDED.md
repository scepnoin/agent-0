# Agent-0: Improvements Needed

## Updated: 2026-03-15

## Critical Issues (Must Fix)

### 1. Onboarding: Code reading too shallow
**Problem:** Only reads 60 files per module with 5000 char limit. For a large project's core/ directory (200+ files), misses 75%.
**Fix:**
- Build AST-based dependency graph (programmatic, not LLM) for Python files
- Trace imports to understand module relationships
- Read ALL files in key modules, not just first 60
- Increase per-file limit to 8000+ chars for important files
- Multi-pass analysis: structure pass, then deep pass on key files

### 2. Onboarding: Code is the source of truth, not docs
**Problem:** Most knowledge comes from docs which may be stale. Code is always current.
**Fix:**
- Phase order: scan → read CODE first → then docs for supplementary context
- Build understanding from imports, class hierarchies, function signatures
- Cross-reference docs against code — flag stale docs as unreliable

### 3. Gospel extraction fails
**Problem:** LLM output format doesn't match expected GOSPEL:/REASON:/CATEGORY: format. Gospels end up empty or truncated.
**Fix:**
- Use structured output (JSON mode) instead of free-text parsing
- Send explicit JSON schema for gospel format
- Validate each gospel has complete rule + reason before storing
- Retry if format is wrong

### 4. Search doesn't find all knowledge
**Problem:** Queries like "what are the key modules" don't find modules/*.md files. FTS5 keyword search misses semantic matches.
**Fix:**
- Ensure ALL .md files are indexed after onboarding (verify index coverage)
- Improve search to query BOTH FTS5 and DB tables
- System prompt should instruct LLM to check specific knowledge areas (modules/, docs_analysis, etc.)
- Add a `list_knowledge` tool so the LLM can see what files are available

### 5. Phase detection weak
**Problem:** Despite having phase info in docs (Phase 15, Phase 16, W2508, etc.), synthesis says "Not specified".
**Fix:**
- Specifically search for phase indicators during synthesis
- Look for files named with phase/roadmap keywords
- Give the LLM the FULL docs_analysis (not truncated) when detecting phase

## Important Improvements

### 6. Model tiers updated
**Status:** DONE (March 2026)
- Google: gemini-3.1-flash-lite (fast), gemini-2.5-flash (mid), gemini-3.1-pro (smart)
- Anthropic: claude-haiku-4-5 (fast), claude-sonnet-4-6 (mid), claude-opus-4-6 (smart)
- OpenAI: gpt-5-mini (fast), gpt-5.3-codex (mid), gpt-5.4 (smart)

### 7. Use SMART tier for onboarding synthesis
**Problem:** Using flash for synthesis produces thin results.
**Fix:** Use smart tier (Opus/GPT-5.4/Gemini 3.1 Pro) for:
- Phase 5 synthesis
- Gospel generation
- Initial phase detection
Keep flash for batch classification during watching.

### 8. AST-based dependency graph
**Problem:** Agent-0 guesses dependencies from LLM analysis. Should be programmatic.
**Fix:**
- Parse Python files with `ast` module
- Extract all imports, class definitions, function definitions
- Build a real dependency graph: which file imports which
- Store in DB as structured data (not markdown)
- Use this for gospel auto-detection (if A imports B, they're coupled)

### 9. Full file indexing
**Problem:** Not all knowledge files are searchable.
**Fix:**
- After onboarding, verify every .md in agent-0/ is in the memory_index
- Add a health check: count .md files vs indexed files
- Re-index on every backend startup

### 10. Tauri exe auto-launches backend
**Status:** Working but needs polish
- Browse button now opens native Windows folder picker via tauri-plugin-dialog
- Switch project restarts backend via Rust (kills old, spawns new)
- Need to handle case where Python isn't installed

## Nice to Have

### 11. Cost dashboard in widget
Show: total cost today, this month, per-model breakdown

### 12. Session management cleanup
Stop creating new sessions on every restart

### 13. Stale doc detection
Cross-reference docs against code — flag docs that reference functions/files that don't exist anymore

### 14. Export/import knowledge
Ability to export agent-0/ knowledge and import on another machine

### 15. Git integration
If project is a git repo, use git diff for much better change tracking

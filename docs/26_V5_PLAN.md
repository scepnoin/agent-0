# V5 Plan: Agent-to-Agent Communication & Live Intelligence

## Prerequisite: V4 DONE (confirmed — 95%+ accuracy, 1.7MB knowledge, 36 gospels)

## What V5 Adds

V4 made Agent-0 a thorough, one-shot knowledge builder.
V5 makes Agent-0 a LIVE, communicating sentinel that stays current and talks to working agents.

## V5 Features (in build order)

---

### Feature 1: Welcome-Back Brief

**What:** When a new agent session connects (first query after 30+ min gap), Agent-0 delivers a comprehensive welcome brief automatically.

**Why:** The #1 value of Agent-0. A new Claude Code session starts cold — Agent-0 gives it everything.

**How:**
- Track last query timestamp per connection
- If gap > 30 minutes, treat as new session
- Prepend the brief to the first response:
  ```
  "Welcome back. Since your last session:
   - 5 files changed (config.py, plan_executor.py, ...)
   - Phase: Alpha Development, hardening sprint active
   - 3 new known issues (I-573, I-574, I-575)
   - Top gospel reminder: sqlite3.Row access uses bracket notation

   Now to your question: ..."
  ```

**Changes needed:**
- New DB table: `connections` (last_query_at, queries_count)
- `/query` endpoint checks if this is a "new session" (30+ min gap)
- Generate brief from: recent changes, current state, pending pings
- Prepend to response

**Estimated effort:** Small — mostly logic in server.py

---

### Feature 2: Stale Doc Detection & Agent Pinging

**What:** Agent-0 detects when core tracking docs (ACTIVE_WORK, KNOWN_ISSUES, etc.) haven't been updated despite file changes happening, and pings the working agent to update them.

**Why:** Without this, the tracking docs go stale and Agent-0's understanding of intent drifts.

**How:**
- Track last-modified time of key docs (ACTIVE_WORK.md, KNOWN_ISSUES.md, etc.)
- After N file changes without a doc update, set a pending ping
- On next agent query, append the ping:
  ```
  "By the way — ACTIVE_WORK.md hasn't been updated in 3 hours
   and 12 files have changed. When you finish your current task,
   please update it with what you're working on."
  ```

**Changes needed:**
- Watcher tracks key doc modification times
- New: `pending_pings` list in memory (or DB)
- `/query` response appends pending pings
- Pings are delivered once, then cleared

**Estimated effort:** Medium — watcher + server changes

---

### Feature 3: Recommend Missing Docs

**What:** During onboarding, if Agent-0 doesn't find key tracking docs, it creates a recommendation in its knowledge and pings the first agent that connects.

**Why:** Some projects have no ACTIVE_WORK.md or KNOWN_ISSUES.md. Agent-0 works better with them.

**How:**
- During onboarding Phase 3 (read docs), check which key docs exist
- Store missing docs as a recommendation in DB
- On first agent connection, include recommendation:
  ```
  "Recommendation: This project doesn't have ACTIVE_WORK.md.
   Creating one would help me track what you're working on
   and detect drift. Want me to create a template?"
  ```

**Key docs to check for:**
- ACTIVE_WORK.md (or similar: CURRENT_WORK, IN_PROGRESS, TODO)
- KNOWN_ISSUES.md (or similar: BUGS, ISSUES)
- COMPLETED_WORK.md (or similar: CHANGELOG, DONE)
- ROADMAP.md (or similar: PLAN, PHASES)

**Changes needed:**
- Onboarding stores missing doc recommendations in DB
- `/brief` endpoint includes recommendations
- Optional: template generator for missing docs

**Estimated effort:** Small

---

### Feature 4: Live Knowledge Updates

**What:** When the watcher detects changes to key project docs (KNOWN_ISSUES.md, ACTIVE_WORK.md, ROADMAP.md, CLAUDE.md), Agent-0 re-reads them and updates its knowledge immediately.

**Why:** V4 onboarding is a point-in-time snapshot. If KNOWN_ISSUES.md is updated, Agent-0 should know within seconds, not require re-onboarding.

**How:**
- Already partially built in V4 (watcher key_docs update)
- Expand to cover more doc types
- Re-index the updated knowledge file
- Log the update in session

**Changes needed:**
- Watcher: expand key_docs list
- After re-reading, re-index the specific file
- Notify via pending_pings: "I noticed KNOWN_ISSUES.md was updated. I've refreshed my knowledge."

**Estimated effort:** Small — mostly expanding existing watcher code

---

### Feature 5: MCP Full Integration

**What:** Make the MCP server fully functional — not just stubs, but proper tool implementations that working agents can call directly.

**Why:** Claude Code, Cursor, etc. connect via MCP. The tools need to work properly.

**MCP Tools:**
```
agent0_brief      → Full project brief (welcome-back aware)
agent0_query      → Free-form question (same as /query)
agent0_state      → Current state snapshot
agent0_gospels    → All active gospel rules
agent0_changes    → Recent file changes with diffs
agent0_issues     → Current known issues (live read)
agent0_recommend  → What Agent-0 recommends (missing docs, etc.)
```

**Changes needed:**
- MCP handler calls Flask API internally (already partially done)
- Add new tools: agent0_changes, agent0_issues, agent0_recommend
- Test with Claude Code's MCP client

**Estimated effort:** Medium

---

### Feature 6: Session Intent Tracking

**What:** When an agent starts working, Agent-0 asks "what are you working on?" and tracks the intent. All changes are then compared against this intent for drift detection.

**Why:** Without intent, drift detection is just "is this change related to the phase?" With intent, it's "is this change related to what you SAID you'd do?"

**How:**
- On new session (welcome-back), include: "What are you working on this session?"
- Store the intent in the sessions table
- Watcher compares changes against both phase goal AND session intent
- If drift detected: "You said you'd work on I-573 but you've been editing cognitive_architecture.py which isn't related."

**Changes needed:**
- `/session/start` endpoint that accepts intent
- Watcher drift detection uses session intent
- MCP tool: agent0_set_intent

**Estimated effort:** Medium

---

## Build Order

| Step | Feature | Priority | Effort |
|------|---------|----------|--------|
| 1 | Welcome-Back Brief | CRITICAL | Small |
| 2 | Stale Doc Detection | HIGH | Medium |
| 3 | Live Knowledge Updates | HIGH | Small |
| 4 | MCP Full Integration | HIGH | Medium |
| 5 | Recommend Missing Docs | MEDIUM | Small |
| 6 | Session Intent Tracking | MEDIUM | Medium |

## What V5 Does NOT Include

- UI improvements (Tauri polish, icons, installer) → V6
- Multi-project management from one UI → V6
- Cost dashboard → V6
- Open source packaging → V6

## Success Criteria

V5 is done when:
1. A new Claude Code session gets an automatic welcome-back brief with recent changes
2. Agent-0 pings the working agent when ACTIVE_WORK.md is stale
3. KNOWN_ISSUES.md changes are reflected in Agent-0's knowledge within 30 seconds
4. MCP tools work end-to-end with Claude Code
5. Agent-0 detects drift against session intent, not just phase goal

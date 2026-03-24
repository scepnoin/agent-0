# Onboarding V3 Plan

## Problems with V2
1. Gospels are hallucinated (generic, not project-specific)
2. Backup/venv files pollute analysis
3. Only 60/255 core files analyzed
4. docs_analysis is 75 truncated batches, not structured
5. CLAUDE.md rules not extracted as gospels
6. Documentation/Archive folder history not captured
7. TODO scanner flags DEBUG comments as bugs
8. Phase detection fails

## V3 Strategy: Code First, Docs as Context

### Phase Order
1. **SCAN** — directory structure (unchanged)
2. **AST ANALYSIS** — programmatic code structure (unchanged, works well)
3. **READ CLAUDE.md** — extract the 24 pre-implementation rules as GOSPELS (new)
4. **READ CURRENT STATE DOCS** — ACTIVE_WORK, KNOWN_ISSUES, OUTSTANDING_WORK, COMPLETED_WORK, HARDENING_CHECKLIST (new, full reads)
5. **READ ARCHITECTURE DOCS** — SCRIBE_MAP, ROADMAP, PHASE_16 plan, NSCA paper (new, full reads)
6. **READ ARCHIVE DOCS** — history, past phases, handovers (batch, for context only)
7. **READ CODE MODULES** — ALL core sub-modules, not just 60 files (improved)
8. **SYNTHESIZE** — smart tier, with FULL context from all above (improved)
9. **CONFIRM** — present to user

### Key Changes
- CLAUDE.md rules become gospels (not LLM-generated)
- Exclude: backups/, .backup/, t5_training_env_py311/, venv/, python/, site-packages/, Lib/, Scripts/
- Read ALL files in core/semantic/, core/control/, core/deep_thinking/
- Structure docs_analysis by topic, not batch number
- TODO scanner: only flag lines starting with # TODO, # FIXME, # HACK (not DEBUG)
- Use SMART tier for synthesis and gospel extraction

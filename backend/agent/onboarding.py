"""
Agent-0 Onboarding V4 — Thorough Project Learning
Reads EVERYTHING. Takes as long as needed. Becomes the source of truth.

Phases:
1. SCAN — directory structure
2. AST — programmatic code analysis (classes, functions, imports, deps)
3. READ DOCS — every doc, one at a time, fully, organized by topic
4. READ CODE — every sub-module deeply
5. DERIVE GOSPELS — from code patterns + docs + any rules files
6. SYNTHESIZE — smart tier, comprehensive state
7. CONFIRM — index and present
"""

import os
import json as json_mod
from pathlib import Path
from datetime import datetime
from logger import get_logger

log = get_logger("onboarding")

SKIP_DIRS = {
    ".git", "agent-0", ".agent0", "__pycache__", "node_modules",
    "venv", ".venv", "python", "site-packages", "Lib", "lib",
    "Scripts", "Include", "target", "dist", "build",
    "t5_training_env_py311", ".tox", ".pytest_cache", ".mypy_cache",
    "egg-info", ".eggs", ".tmp", "logs",
    "backups", "backup", ".backup", "db_backups",
    "tests_runtime_tmp",
    # Third-party / vendored code
    "third_party", "vendor", "vendors", "vendored",
    "llama.cpp", "ggml", "whisper.cpp",
    "external", "deps",
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".db", ".sqlite",
    ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg",
    ".mp3", ".mp4", ".wav", ".zip", ".tar", ".gz", ".7z",
    ".whl", ".egg", ".lock", ".log", ".db-journal", ".db-shm", ".db-wal",
}

CODE_EXTENSIONS = {".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp", ".h"}


class Onboarding:
    def __init__(self, config, llm_client, db, store, indexer):
        self.config = config
        self.llm = llm_client
        self.db = db
        self.store = store
        self.indexer = indexer
        self.project_path = Path(config.get("project_path"))
        self.project_name = config.get("project_name")

    def run(self):
        print(f"\n  [ONBOARD] Starting V4 thorough onboarding...")
        print(f"  [ONBOARD] Project: {self.project_name}")
        print(f"  [ONBOARD] This may take a while for large projects.\n")

        phases = ["scan", "ast", "code_scan", "read_docs", "read_code", "derive_gospels", "synthesize", "confirm"]
        for phase in phases:
            if not self.db.fetchone("SELECT * FROM onboarding_progress WHERE phase = ?", (phase,)):
                self.db.insert("onboarding_progress", {"phase": phase, "status": "pending"})

        for name, func in [
            ("scan", self._scan), ("ast", self._ast), ("code_scan", self._code_scan),
            ("read_docs", self._read_docs), ("read_code", self._read_code),
            ("derive_gospels", self._derive_gospels),
            ("synthesize", self._synthesize), ("confirm", self._confirm),
        ]:
            p = self.db.fetchone("SELECT * FROM onboarding_progress WHERE phase = ?", (name,))
            if p and p["status"] == "completed":
                print(f"  [ONBOARD] Phase '{name}' done, skipping.")
                continue
            self.db.update("onboarding_progress",
                {"status": "in_progress", "started": datetime.now().isoformat()}, "phase = ?", (name,))
            try:
                func()
                self.db.update("onboarding_progress",
                    {"status": "completed", "completed": datetime.now().isoformat()}, "phase = ?", (name,))
            except Exception as e:
                log.error(f"Phase '{name}' failed: {e}")
                self.db.update("onboarding_progress",
                    {"status": "failed", "notes": str(e)[:500]}, "phase = ?", (name,))
                raise

        print("\n  [ONBOARD] V4 Onboarding complete!")

    def _llm(self, prompt, tier="mid"):
        try:
            return self.llm.call_tiered(
                messages=[{"role": "user", "content": prompt}], tier=tier
            ).get("text", "") or ""
        except Exception as e:
            log.error(f"LLM failed: {e}")
            return ""

    def _read_file(self, path, max_chars=25000):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text) > max_chars:
                return text[:max_chars] + f"\n\n...(truncated at {max_chars}, full: {len(text)} chars)..."
            return text
        except (OSError, PermissionError):
            return None

    def _write(self, path, content):
        """Write to knowledge md and log."""
        self.store.write(path, content, mode="overwrite")
        log.info(f"Wrote: {path}")

    # ── Phase 1: Scan ────────────────────────────────────

    def _scan(self):
        print("  [ONBOARD] Phase 1: Scanning structure...")
        stats = {"files": 0, "dirs": 0}
        ext_counts = {}
        lines = []

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            depth = str(root).replace(str(self.project_path), "").count(os.sep)
            if depth > 4:
                continue
            stats["dirs"] += 1
            indent = "  " * depth
            lines.append(f"{indent}{os.path.basename(root)}/ ({len(files)} files)")
            for f in sorted(files)[:50]:
                ext = Path(f).suffix.lower()
                if ext in SKIP_EXTENSIONS:
                    continue
                stats["files"] += 1
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        content = f"# Project Structure: {self.project_name}\n\n"
        content += f"**Files:** {stats['files']} | **Dirs:** {stats['dirs']}\n\n"
        for ext, cnt in sorted(ext_counts.items(), key=lambda x: -x[1])[:10]:
            content += f"- {ext}: {cnt}\n"
        content += f"\n```\n" + "\n".join(lines[:2000]) + "\n```\n"
        self._write("structure.md", content)
        print(f"  [ONBOARD]   -> structure.md ({stats['files']} files)")

    # ── Phase 2: AST Analysis ────────────────────────────

    def _ast(self):
        print("  [ONBOARD] Phase 2: AST code analysis...")
        from memory.ast_analyzer import analyze_directory, format_file_summary, format_dependency_graph

        result = analyze_directory(self.project_path)

        # Code structure file
        content = f"# Code Structure\n\n"
        content += f"**Files:** {result['total_files']} | **Classes:** {result['total_classes']} | "
        content += f"**Functions:** {result['total_functions']} | **Lines:** {result['total_lines']:,}\n\n"

        # Critical files by dependents
        dep_count = {}
        for deps in result['dependency_graph'].values():
            for d in deps:
                dep_count[d] = dep_count.get(d, 0) + 1

        if dep_count:
            # Rank by combined score: dependents + complexity (lines/1000 + classes)
            file_scores = {}
            for f, dep in dep_count.items():
                analysis = result['files'].get(f, {})
                lines = analysis.get('lines', 0)
                classes = len(analysis.get('classes', []))
                methods = sum(len(c.get('methods', [])) for c in analysis.get('classes', []))
                # Score: dependents + lines/100 + classes*5 + methods
                score = dep + (lines / 100) + (classes * 5) + methods
                file_scores[f] = {
                    "dep": dep, "lines": lines, "classes": classes,
                    "methods": methods, "score": score
                }

            content += "## Most Critical Files (by impact)\n\n"
            for f, info in sorted(file_scores.items(), key=lambda x: -x[1]["score"])[:25]:
                content += (f"- **{f}** — {info['dep']} dependents, "
                           f"{info['lines']} lines, {info['classes']} classes, "
                           f"{info['methods']} methods\n")
                self.db.insert("open_items", {
                    "description": f"Critical: {f} ({info['dep']} deps, {info['lines']} lines, {info['methods']} methods)",
                    "type": "critical_file", "status": "tracked"
                })
            content += "\n"

        # TODOs (real ones only)
        todos = []
        for path, analysis in result['files'].items():
            for todo in analysis.get('todos', []):
                text = todo['text']
                if not any(skip in text.upper() for skip in ['DEBUG BLOCK', 'DEBUG LOG', 'DEBUGGING']):
                    todos.append(f"- `{path}:{todo['line']}` [{todo['marker']}] {text[:100]}")
        if todos:
            content += f"## TODOs ({len(todos)})\n\n" + "\n".join(todos[:100]) + "\n\n"

        # Key file summaries (top 30)
        content += "## Key Files\n\n"
        for fp in sorted(dep_count.keys(), key=lambda x: -dep_count[x])[:30]:
            if fp in result['files']:
                content += format_file_summary(result['files'][fp]) + "\n\n---\n\n"

        self._write("code_structure.md", content)
        self._write("dependencies.md", format_dependency_graph(result['dependency_graph']))

        # Write COMPLETE file index — every class, every method, every line number
        # This is Agent-0's "map" for on-demand code reading
        from memory.ast_analyzer import format_file_index
        index_content = f"# Complete Code Index\n\n"
        index_content += f"**Every class, method, and function with line numbers.**\n"
        index_content += f"**Use read_file with line_start/line_end to read specific sections.**\n\n"

        # Group by directory
        dirs = {}
        for filepath, analysis in sorted(result['files'].items()):
            parts = filepath.replace("\\", "/").split("/")
            dir_key = "/".join(parts[:-1]) if len(parts) > 1 else "(root)"
            if dir_key not in dirs:
                dirs[dir_key] = []
            dirs[dir_key].append(analysis)

        for dir_path, file_analyses in sorted(dirs.items()):
            index_content += f"\n## {dir_path}/\n\n"
            for analysis in file_analyses:
                index_content += format_file_index(analysis) + "\n\n"

        self._write("code_index.md", index_content)

        # Store dep graph data for gospel derivation
        self._dep_count = dep_count
        self._ast_result = result

        print(f"  [ONBOARD]   -> code_structure.md ({result['total_files']} files)")
        print(f"  [ONBOARD]   -> dependencies.md ({sum(len(v) for v in result['dependency_graph'].values())} edges)")

    # ── Phase 3: Code Scan (semgrep etc.) ──────────────────

    def _code_scan(self):
        """Run static analysis tools to find bugs and security issues."""
        print("  [ONBOARD] Phase 3: Running code scanners...")
        from memory.code_scanner import run_scan, format_findings

        results = run_scan(self.project_path)
        if results["total"] > 0:
            # Write findings to knowledge
            self._write("scan_results.md", format_findings(results))

            # Store ONE summary alert — not individual findings (those go in scan_results.md)
            high_count = results["by_severity"].get("HIGH", 0) + results["by_severity"].get("ERROR", 0) + results["by_severity"].get("CRITICAL", 0)
            if high_count > 0:
                self.db.insert("alerts", {
                    "message": f"Code scan complete: {results['total']} findings ({high_count} HIGH). See scan_results.md for details.",
                    "type": "code_scan_summary",
                    "severity": "high" if high_count > 10 else "medium"
                })

            # Write scan summary to state/current.md so the LLM always sees it
            high_count = results["by_severity"].get("HIGH", 0) + results["by_severity"].get("ERROR", 0) + results["by_severity"].get("CRITICAL", 0)
            med_count = results["by_severity"].get("MEDIUM", 0) + results["by_severity"].get("WARNING", 0)
            low_count = results["by_severity"].get("LOW", 0) + results["by_severity"].get("INFO", 0)
            scan_state = (
                f"\n## Latest Scan Results\n\n"
                f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"**Total findings:** {results['total']}\n"
                f"**HIGH:** {high_count} | **MEDIUM:** {med_count} | **LOW:** {low_count}\n"
                f"**Cross-referenced:** {results.get('cross_referenced', 0)} confirmed by multiple tools\n\n"
            )
            if results["findings"]:
                scan_state += "**Top findings:**\n"
                for f in results["findings"][:10]:
                    scan_state += f"- [{f['severity']}] {f['rule'].split('.')[-1]}: {f['message'][:100]} in {f['file']}:{f['line']}\n"
                scan_state += f"\n*Full details in scan_results.md*\n"

            # Store for later injection into state/current.md during synthesize phase
            self._scan_summary = scan_state

            print(f"  [ONBOARD]   -> scan_results.md ({results['total']} findings)")
            print(f"  [ONBOARD]   -> {results['by_severity']}")
        else:
            self._write("scan_results.md", "# Code Scan Results\n\nNo issues found.\n")
            self._scan_summary = "\n## Latest Scan Results\n\nNo issues found.\n"
            print("  [ONBOARD]   -> No issues found")

    # ── Phase 4: Read ALL Docs ───────────────────────────

    def _read_docs(self):
        print("  [ONBOARD] Phase 3: Reading ALL documentation...")

        # Find every .md file in the project (excluding agent-0, backups, venvs)
        all_docs = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for f in sorted(files):
                if f.endswith(".md") or f.endswith(".txt") and f.upper() in ("README.txt", "CHANGELOG.txt"):
                    full = Path(root) / f
                    rel = str(full.relative_to(self.project_path)).replace("\\", "/")
                    size = full.stat().st_size if full.exists() else 0
                    if size > 100:  # Skip tiny/empty files
                        all_docs.append((rel, full, size))

        print(f"  [ONBOARD]   -> Found {len(all_docs)} documents")

        # Check for missing key docs and create recommendations
        recommended_docs = ["ACTIVE_WORK.md", "KNOWN_ISSUES.md", "COMPLETED_WORK.md", "ROADMAP.md", "CHANGELOG.md"]
        all_doc_names = {Path(rel).name.upper() for rel, _, _ in all_docs}
        missing = [d for d in recommended_docs if d.upper() not in all_doc_names]
        if missing:
            self.db.insert("pending_pings", {
                "message": f"Recommendation: This project is missing {', '.join(missing)}. "
                           f"Creating these would help me track progress and detect drift. "
                           f"Want me to suggest templates?",
                "type": "recommendation"
            })
            print(f"  [ONBOARD]   -> Missing docs: {', '.join(missing)} (recommendation queued)")

        # Note for doc reading: when docs mention bugs/issues with status markers
        # like [x] DONE, RESOLVED, FIXED — record them as RESOLVED, not OPEN.
        # This prevents the stale-knowledge problem where Agent-0 reports
        # already-fixed bugs as current issues.

        # Categorize docs
        categories = {
            "project_overview": [],  # README, CLAUDE.md, main description files
            "current_state": [],     # ACTIVE_WORK, KNOWN_ISSUES, OUTSTANDING_WORK
            "architecture": [],      # SCRIBE_MAP, ARCHITECTURE, dependency maps
            "roadmap": [],           # ROADMAP, PHASE docs, LEAP
            "work_items": [],        # W-number docs, sprint plans, implementation plans
            "history": [],           # COMPLETED_WORK, Archive docs, handovers
            "other": [],             # Everything else
        }

        for rel, full, size in all_docs:
            name_upper = Path(rel).name.upper()
            if any(k in name_upper for k in ["README", "CLAUDE", "OVERVIEW"]):
                categories["project_overview"].append((rel, full, size))
            elif any(k in name_upper for k in ["ACTIVE", "KNOWN_ISSUE", "OUTSTANDING", "HARDENING", "CHECKLIST"]):
                categories["current_state"].append((rel, full, size))
            elif any(k in name_upper for k in ["MAP", "ARCHITECT", "DEPENDENCY", "ROUTING", "AUDIT"]):
                categories["architecture"].append((rel, full, size))
            elif any(k in name_upper for k in ["ROADMAP", "PHASE", "LEAP", "MASTER_PLAN"]):
                categories["roadmap"].append((rel, full, size))
            elif any(k in name_upper for k in ["W2", "W1", "SPRINT", "IMPLEMENTATION", "FIX"]):
                categories["work_items"].append((rel, full, size))
            elif any(k in name_upper for k in ["COMPLETED", "HISTORY", "HANDOVER", "ARCHIVE"]):
                categories["history"].append((rel, full, size))
            else:
                categories["other"].append((rel, full, size))

        # Read each category, write structured output
        for cat_name, docs in categories.items():
            if not docs:
                continue

            print(f"  [ONBOARD]   Category: {cat_name} ({len(docs)} docs)")
            cat_content = f"# {cat_name.replace('_', ' ').title()}\n\n"
            cat_content += f"**Documents:** {len(docs)}\n\n"

            for rel, full, size in docs:
                text = self._read_file(full, max_chars=20000)
                if not text:
                    continue

                # For important docs, get LLM summary
                if size > 500:
                    summary = self._llm(
                        f"Read this document from project '{self.project_name}' thoroughly. "
                        f"Extract ALL key information: goals, status, issues, decisions, rules, "
                        f"work items, phase details. Be specific — include W-numbers, I-numbers, "
                        f"file names, function names.\n\n"
                        f"IMPORTANT: If any bugs or issues are marked as FIXED, DONE, RESOLVED, "
                        f"or have [x] checkmarks, report them as RESOLVED — NOT as open issues. "
                        f"Only report issues as OPEN if they are clearly still unresolved.\n\n"
                        f"FILE: {rel}\n\n{text}"
                    )
                else:
                    summary = text  # Small files: store as-is

                cat_content += f"## {rel}\n\n{summary}\n\n---\n\n"

                # Write after EACH doc (write-as-you-go)
                self._write(f"docs/{cat_name}.md", cat_content)
                print(f"  [ONBOARD]     -> {rel}")

        print(f"  [ONBOARD]   -> docs/ written")

    # ── Phase 4: Read Code Modules ───────────────────────

    def _read_code(self):
        print("  [ONBOARD] Phase 4: Reading code modules...")

        # Find all code directories
        code_dirs = []
        for entry in sorted(self.project_path.iterdir()):
            if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            py_count = sum(1 for _ in entry.rglob("*.py") if not any(s in str(_) for s in SKIP_DIRS))
            if py_count > 0:
                code_dirs.append((entry.name, entry, py_count))

        for dir_name, dir_path, total_files in code_dirs:
            # Find ALL sub-modules (sub-directories with .py files)
            sub_modules = {}
            for py_file in sorted(dir_path.rglob("*.py")):
                if any(s in str(py_file) for s in SKIP_DIRS):
                    continue
                # Group by parent directory
                rel_dir = str(py_file.parent.relative_to(self.project_path)).replace("\\", "/")
                if rel_dir not in sub_modules:
                    sub_modules[rel_dir] = []
                sub_modules[rel_dir].append(py_file)

            # Analyze each sub-module separately
            module_content = f"# Module: {dir_name}\n\n"
            module_content += f"**Total files:** {total_files}\n"
            module_content += f"**Sub-modules:** {len(sub_modules)}\n"
            module_content += f"**Analyzed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

            for sub_path, files in sorted(sub_modules.items()):
                batch_size = 8
                sub_name = sub_path.split("/")[-1] if "/" in sub_path else sub_path

                for batch_start in range(0, min(len(files), 80), batch_size):
                    batch = files[batch_start:batch_start + batch_size]
                    batch_content = ""
                    for f in batch:
                        text = self._read_file(f, max_chars=8000)
                        if text:
                            rel = str(f.relative_to(self.project_path)).replace("\\", "/")
                            batch_content += f"\n--- {rel} ---\n{text}\n"

                    if not batch_content:
                        continue

                    # Read existing knowledge for context
                    existing = self.store.read(f"code/{dir_name}.md")
                    context = ""
                    if existing and "File not found" not in existing:
                        context = f"You already know about '{dir_name}':\n{existing[:2000]}\n\nNow analyze more files. Add NEW information only.\n\n"

                    analysis = self._llm(
                        f"{context}Analyze '{sub_name}' sub-module of '{self.project_name}/{dir_name}'. "
                        f"Describe: purpose, key classes/functions (by name), dependencies, patterns, issues.\n\n"
                        f"{batch_content}"
                    )

                    module_content += f"\n## {sub_path} (Pass {batch_start // batch_size + 1})\n\n{analysis}\n"

                    # Write after each pass
                    self._write(f"code/{dir_name}.md", module_content)

                if len(files) > 80:
                    module_content += f"\n*{len(files) - 80} additional files in {sub_path} not analyzed.*\n"
                    self._write(f"code/{dir_name}.md", module_content)

            print(f"  [ONBOARD]   -> code/{dir_name}.md ({total_files} files, {len(sub_modules)} sub-modules)")

    # ── Phase 5: Derive Gospels ──────────────────────────

    def _derive_gospels(self):
        print("  [ONBOARD] Phase 5: Deriving gospels from ALL sources...")
        gospels_md = f"# Gospel Rules\n\n"
        gospels_md += f"**Derived:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        gospels_md += f"**Sources:** Code patterns, documentation, project rules\n\n"
        gospel_count = 0

        # Source 1: Code patterns (from AST analysis)
        print("  [ONBOARD]   Source: Code patterns...")
        code_structure = self.store.read("code_structure.md")
        if code_structure and "File not found" not in code_structure:
            # Extract critical files section
            critical_section = ""
            in_critical = False
            for line in code_structure.split("\n"):
                if "Most Critical Files" in line:
                    in_critical = True
                elif line.startswith("## ") and in_critical:
                    break
                elif in_critical:
                    critical_section += line + "\n"

            if critical_section:
                # Generate SPECIFIC gospels naming actual files
                # Parse the critical files list to get real file names
                critical_files = []
                for line in critical_section.split("\n"):
                    if line.strip().startswith("- **"):
                        # Extract: "- **config.py** — 155 dependents, 747 lines..."
                        parts = line.strip().split("**")
                        if len(parts) >= 2:
                            fname = parts[1].strip()
                            rest = line.split("—")[1].strip() if "—" in line else ""
                            critical_files.append(f"{fname} ({rest[:80]})")

                # Create gospels directly from top files — no LLM needed
                for i, file_info in enumerate(critical_files[:5]):
                    fname = file_info.split(" (")[0]
                    details = file_info.split("(")[1].rstrip(")") if "(" in file_info else ""
                    rule = f"Changes to '{fname}' require thorough testing — {details}. This is a critical file."
                    gid = self.db.insert("gospels", {
                        "rule": rule,
                        "reason": f"'{fname}' is a high-impact file based on dependency + complexity analysis",
                        "category": "dependency", "scope": "module",
                        "created_by": "agent", "confidence": "medium", "status": "active"
                    })
                    gospels_md += f"### Gospel #{gid} [CODE PATTERN]\n**Rule:** {rule}\n**Source:** Dependency analysis\n\n"
                    gospel_count += 1

                # Also detect coupled files from dependency graph
                deps_content = self.store.read("dependencies.md")
                if deps_content and "File not found" not in deps_content:
                    code_gospels = self._llm(
                        f"Based on this dependency graph, identify 2-3 pairs of files that are TIGHTLY COUPLED "
                        f"(both depend on each other, or one is critical to the other). "
                        f"For each pair, write a SPECIFIC rule naming both files.\n"
                        f"Format: RULE: <specific rule naming both files>\n\n"
                        f"{deps_content[:4000]}"
                    )
                    for line in code_gospels.split("\n"):
                        line = line.strip()
                        if line.upper().startswith("RULE:"):
                            rule = line.split(":", 1)[1].strip()
                            if rule and len(rule) > 20:
                                gid = self.db.insert("gospels", {
                                    "rule": rule, "reason": "Derived from dependency coupling analysis",
                                    "category": "dependency", "scope": "module",
                                    "created_by": "agent", "confidence": "medium", "status": "active"
                                })
                                gospels_md += f"### Gospel #{gid} [CODE COUPLING]\n**Rule:** {rule}\n**Source:** Dependency graph\n\n"
                                gospel_count += 1

        # Source 2: CLAUDE.md or similar rules files
        print("  [ONBOARD]   Source: Project rules files...")
        seen_rules_files = set()
        for rules_file in ["CLAUDE.md", "claude.md", ".cursorrules", "RULES.md", "CONTRIBUTING.md"]:
            p = self.project_path / rules_file
            if not p.exists():
                p = self.project_path / "Documentation" / rules_file
            if not p.exists():
                continue
            # Skip if we already read this exact file (e.g., same CLAUDE.md found in root AND Documentation/)
            try:
                real_path = str(p.resolve())
                if real_path in seen_rules_files:
                    continue
                seen_rules_files.add(real_path)
            except Exception:
                pass

            text = self._read_file(p, max_chars=30000)
            if not text:
                continue

            print(f"  [ONBOARD]     Found: {rules_file}")

            # Parse ### headings as rules
            seen_titles = set()
            current_rule = None
            for line in text.split("\n"):
                if line.startswith("### ") and not line.startswith("####"):
                    if current_rule and len(current_rule["body"]) > 20:
                        title = current_rule["title"]
                        # Deduplicate by title
                        if title[:40] not in seen_titles:
                            seen_titles.add(title[:40])
                            # Capture full body — not just first line
                            # Clean code blocks for readability
                            body = current_rule["body"].strip()
                            # Extract the lesson (text before/after code blocks)
                            body_clean = body.replace("```python", "").replace("```bash", "").replace("```", "")
                            body_clean = " ".join(body_clean.split())[:500]
                            rule_text = f"{title}: {body_clean}"
                            gid = self.db.insert("gospels", {
                                "rule": rule_text, "reason": f"From {rules_file}",
                                "category": "code", "scope": "global",
                                "created_by": "agent", "confidence": "high", "status": "active"
                            })
                            gospels_md += f"### Gospel #{gid} [FROM {rules_file.upper()}]\n**Rule:** {rule_text}\n\n"
                            gospel_count += 1
                    current_rule = {"title": line[4:].strip(), "body": ""}
                elif current_rule and line.strip():
                    current_rule["body"] += line + "\n"
            # Last rule
            if current_rule and len(current_rule["body"]) > 20:
                title = current_rule["title"]
                if title[:40] not in seen_titles:
                    body = current_rule["body"].strip()
                    body_clean = body.replace("```python", "").replace("```bash", "").replace("```", "")
                    body_clean = " ".join(body_clean.split())[:500]
                    rule_text = f"{title}: {body_clean}"
                    gid = self.db.insert("gospels", {
                        "rule": rule_text, "reason": f"From {rules_file}",
                        "category": "code", "scope": "global",
                        "created_by": "agent", "confidence": "high", "status": "active"
                    })
                    gospels_md += f"### Gospel #{gid} [FROM {rules_file.upper()}]\n**Rule:** {rule_text}\n\n"
                    gospel_count += 1

        # Source 3: Known issues / lessons learned from docs
        print("  [ONBOARD]   Source: Lessons from documentation...")
        for doc_path in ["docs/current_state.md", "docs/history.md", "docs/work_items.md"]:
            doc_content = self.store.read(doc_path)
            if not doc_content or "File not found" in doc_content:
                continue

            lessons = self._llm(
                f"From this project documentation, extract 2-3 CRITICAL lessons or rules "
                f"that would prevent future mistakes. Format: one rule per line starting with 'RULE: '\n\n"
                f"{doc_content[:5000]}",
                tier="mid"
            )
            for line in lessons.split("\n"):
                line = line.strip()
                if line.upper().startswith("RULE:"):
                    rule = line.split(":", 1)[1].strip()
                    if rule and len(rule) > 15:
                        gid = self.db.insert("gospels", {
                            "rule": rule, "reason": "Derived from project documentation",
                            "category": "process", "scope": "global",
                            "created_by": "agent", "confidence": "medium", "status": "active"
                        })
                        gospels_md += f"### Gospel #{gid} [FROM DOCS]\n**Rule:** {rule}\n\n"
                        gospel_count += 1

        self._write("gospels/agent_gospels.md", gospels_md)
        self._write("gospels/human_gospels.md", "# Human Gospel Rules\n\n*Add your rules here.*\n")
        print(f"  [ONBOARD]   -> {gospel_count} gospel(s) from all sources")

    # ── Phase 6: Synthesize ──────────────────────────────

    def _synthesize(self):
        print("  [ONBOARD] Phase 6: Synthesizing...")

        # Read ALL own knowledge
        all_knowledge = ""
        for md_file in sorted(self.store.list_files()):
            content = self.store.read(md_file)
            if content and "File not found" not in content and len(content) > 50:
                limit = 5000 if any(k in md_file for k in ["overview", "architecture", "current_state", "code_structure"]) else 2500
                if len(content) > limit:
                    content = content[:limit] + "\n...(truncated)..."
                all_knowledge += f"\n=== {md_file} ===\n{content}\n"
        if len(all_knowledge) > 35000:
            all_knowledge = all_knowledge[:35000]

        # Cross-reference: check doc-mentioned bugs against scan findings
        # This prevents reporting already-fixed bugs as current issues
        scan_content = self.store.read("scan_results.md") or ""
        cross_ref_note = ""
        if scan_content and "File not found" not in scan_content:
            cross_ref_note = (
                "\n\nIMPORTANT CROSS-REFERENCE NOTE:\n"
                "The code scan results (scan_results.md) show what issues ACTUALLY exist in the code RIGHT NOW. "
                "If documentation mentions a bug but the scan did NOT find it, that bug is likely ALREADY FIXED. "
                "Only report issues as OPEN if they appear in BOTH the docs AND the scan results, "
                "or if they are architectural/design issues that a scanner wouldn't catch. "
                "Mark doc-only issues as 'possibly resolved — not confirmed by scan'.\n"
            )

        synthesis = self._llm(
            f"You are Agent-0, THE source of truth for project '{self.project_name}'. "
            f"Based on EVERYTHING you know, write a COMPREHENSIVE report:\n\n"
            f"1. **Project Summary** — what it is, what it does (specific, not vague)\n"
            f"2. **Architecture** — modules, how they connect, technologies, key files\n"
            f"3. **Current Phase & Status** — what's active, what's blocked, sprint status\n"
            f"4. **Known Issues** — ONLY issues confirmed by code scan OR clearly unresolved. "
            f"Do NOT list issues from docs that are marked FIXED/DONE/RESOLVED.\n"
            f"5. **Recent Activity** — sprints, work items, hotfixes\n"
            f"6. **Key Dependencies** — what breaks if what changes\n"
            f"7. **Gospel Summary** — top 5 most critical rules\n\n"
            f"Be SPECIFIC. Use file names, W-numbers, class names, counts.\n"
            f"{cross_ref_note}\n\n{all_knowledge}",
            tier="smart"
        )

        # Phase detection
        phase_text = self._llm(
            f"What development phase is '{self.project_name}' in?\n"
            f"PHASE_NAME: <name>\nPHASE_GOAL: <goal>\n\n{synthesis[:3000]}",
            tier="mid"
        )
        phase_name, phase_goal = "Unknown", "Not identified"
        for line in phase_text.split("\n"):
            if line.strip().upper().startswith("PHASE_NAME:"):
                phase_name = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("PHASE_GOAL:"):
                phase_goal = line.split(":", 1)[1].strip()

        self.db.insert("phases", {"name": phase_name, "goal": phase_goal, "status": "in_progress"})

        scan_section = getattr(self, '_scan_summary', '')
        self._write("state/current.md", (
            f"# Current State\n\n"
            f"**Project:** {self.project_name}\n"
            f"**Status:** Onboarded\n"
            f"**Onboarded:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"**Current Phase:** {phase_name}\n"
            f"**Phase Goal:** {phase_goal}\n\n"
            f"## Synthesis\n\n{synthesis}\n"
            f"{scan_section}"
        ))
        print(f"  [ONBOARD]   -> Phase: {phase_name}")

    # ── Phase 7: Confirm ─────────────────────────────────

    def _confirm(self):
        print("  [ONBOARD] Phase 7: Indexing and confirming...\n")

        # Count what we created
        all_files = self.store.list_files()
        gospels = self.db.fetchall("SELECT * FROM gospels WHERE status = 'active'")

        state = self.store.read("state/current.md")
        for line in (state or "").split("\n")[:20]:
            print(f"  {line}")

        print(f"\n  Knowledge: {len(all_files)} files")
        print(f"  Gospels: {len(gospels)}")
        print(f"\n  [ONBOARD] Indexing all knowledge...")
        self.indexer.index_all()
        print("  [ONBOARD] Done.")

        self.db.insert("sessions", {"intent": "Onboarding", "actual_outcome": "Complete"})

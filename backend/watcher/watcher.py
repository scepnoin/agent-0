"""
Agent-0 File Watcher
Event-driven file system monitoring with debouncing.
Maintains file snapshots for computing real diffs (no git dependency).
"""

import os
import time
import hashlib
import threading
from pathlib import Path
from datetime import datetime
from watchfiles import watch, Change
from logger import get_logger

log = get_logger("watcher")

# Extensions that are actual code/docs (not binary/build artifacts)
TEXT_EXTENSIONS = {
    # Code
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".c", ".cpp", ".h",
    ".kt", ".kts", ".swift", ".dart", ".rb", ".php", ".cs", ".scala", ".lua",
    # Config
    ".html", ".css", ".json", ".toml", ".yaml", ".yml", ".xml",
    ".gradle", ".properties", ".plist",
    # Docs
    ".md", ".txt", ".rst", ".cfg", ".ini", ".env", ".sh", ".bat",
    ".sql", ".graphql", ".proto",
}


class FileWatcher:
    """Watches a project folder for file changes with debouncing and snapshots."""

    def __init__(self, config, react_loop=None, db=None, store=None, reasoning=None, indexer=None, briefing=None):
        self.config = config
        self.react_loop = react_loop
        self.db = db
        self.store = store
        self.reasoning = reasoning
        self.indexer = indexer
        self.briefing = briefing
        self._changes_since_doc_update = 0
        self._code_changes_since_scan = 0  # Track code changes for auto-scan trigger
        self._module_change_counts = {}  # Track changes per module for knowledge refresh
        self._last_full_refresh = None  # Track when we last did a full knowledge refresh
        self.project_path = Path(config.get("project_path"))
        self.debounce_seconds = config.get("watcher.debounce_seconds", 5)
        self.ignore_patterns = config.get("watcher.ignore_patterns", [])
        self._running = False
        self._stop_event = threading.Event()

        # Debounce state
        self._pending_changes = {}
        self._debounce_timer = None
        self._lock = threading.Lock()

        # File snapshots for computing diffs without git
        self._snapshots = {}
        self._build_initial_snapshots()

    def _build_initial_snapshots(self):
        """Snapshot text files on startup for diff tracking. Uses os.walk with skip dirs.
        Skips files over 100KB to save memory. No hard cap — just smart filtering."""
        skip_dirs = set(self.ignore_patterns) | {
            "agent-0", ".git", "__pycache__", "node_modules", "venv", ".venv",
            "target", "dist", "build", "t5_training_env_py311", "python",
            "site-packages", "Lib", "lib", "Scripts", "Include", ".tmp",
            "logs", "backups", "backup", ".backup", "db_backups", "output",
            "tests_runtime_tmp", "benchmark-summary", ".eggs", "egg-info",
            ".tox", ".pytest_cache", ".mypy_cache",
        }
        count = 0
        skipped = 0
        total_bytes = 0
        max_file_size = 100 * 1024  # Skip files over 100KB
        max_total_bytes = 200 * 1024 * 1024  # Stop at 200MB total to prevent RAM issues

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for fname in files:
                ext = Path(fname).suffix.lower()
                if ext not in TEXT_EXTENSIONS:
                    continue
                fpath = Path(root) / fname
                if self.should_ignore(str(fpath)):
                    continue
                try:
                    size = fpath.stat().st_size
                    if size > max_file_size:
                        skipped += 1
                        continue
                    if total_bytes + size > max_total_bytes:
                        skipped += 1
                        continue
                    rel = str(fpath.relative_to(self.project_path))
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    self._snapshots[rel] = content
                    count += 1
                    total_bytes += size
                except Exception:
                    pass

        log.info(f"Snapshots: {count} files ({total_bytes/1024/1024:.1f}MB), {skipped} skipped (too large)")

        # Catch-up: detect changes made while Agent-0 was offline
        if self.db:
            self._catch_up()

    def _catch_up(self):
        """Detect changes made while Agent-0 was offline by comparing file hashes."""
        import hashlib

        # Get saved snapshots from DB
        saved = {}
        try:
            rows = self.db.fetchall("SELECT path, hash, size, lines FROM file_snapshots")
            for r in rows:
                saved[r["path"]] = {"hash": r["hash"], "size": r["size"], "lines": r["lines"]}
        except Exception:
            pass

        if not saved:
            # First run — save all current hashes, no catch-up needed
            log.info("First run — saving file hashes for future catch-up")
            self._save_snapshots()
            return

        # Compare current files against saved hashes
        changed = []
        new_files = []
        deleted = list(saved.keys())  # Start assuming all deleted, remove as we find them

        for rel_path, content in self._snapshots.items():
            norm_path = rel_path.replace("\\", "/")
            if norm_path in deleted:
                deleted.remove(norm_path)

            file_hash = hashlib.md5(content.encode()).hexdigest()

            if norm_path not in saved:
                new_files.append(norm_path)
            elif saved[norm_path]["hash"] != file_hash:
                old = saved[norm_path]
                new_lines = len(content.splitlines())
                changed.append({
                    "path": norm_path,
                    "old_size": old["size"],
                    "new_size": len(content.encode()),
                    "old_lines": old["lines"],
                    "new_lines": new_lines,
                })

        total_changes = len(changed) + len(new_files) + len(deleted)
        if total_changes == 0:
            log.info("Catch-up: no changes detected while offline")
            self._save_snapshots()
            return

        log.info(f"Catch-up: {len(changed)} modified, {len(new_files)} new, {len(deleted)} deleted while offline")

        # Log catch-up to DB and session
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M")
        date = now.strftime("%Y-%m-%d")

        summary_lines = [f"### Catch-up ({timestamp}) — Changes while Agent-0 was offline\n"]
        summary_lines.append(f"**{len(changed)} modified, {len(new_files)} new, {len(deleted)} deleted**\n")

        if changed:
            summary_lines.append("**Modified files:**")
            for c in changed[:20]:
                line_diff = c["new_lines"] - c["old_lines"]
                sign = "+" if line_diff >= 0 else ""
                summary_lines.append(f"- `{c['path']}` ({sign}{line_diff} lines)")

        if new_files:
            summary_lines.append("\n**New files:**")
            for f in new_files[:20]:
                summary_lines.append(f"- `{f}`")

        if deleted:
            summary_lines.append("\n**Deleted files:**")
            for f in deleted[:20]:
                summary_lines.append(f"- `{f}`")

        summary = "\n".join(summary_lines)

        # Write to session log
        if self.store:
            self.store.write(f"sessions/{date}.md", summary + "\n\n", mode="append")

        # Write to DB
        self.db.insert("changes", {
            "files_changed": f"CATCH-UP: {len(changed)} modified, {len(new_files)} new, {len(deleted)} deleted",
            "diff_summary": summary[:500],
            "category": "catch-up"
        })

        # Queue a ping for the next agent session
        if self.briefing:
            self.briefing.add_ping(
                f"While I was offline, {total_changes} file(s) changed: "
                f"{len(changed)} modified, {len(new_files)} new, {len(deleted)} deleted. "
                f"Check the session log for details.",
                "catch_up"
            )

        # Classify the changed files using LLM (batch)
        if self.react_loop and changed:
            try:
                files_str = ", ".join([c["path"] for c in changed[:10]])
                classify_prompt = (
                    f"These files were modified while Agent-0 was offline:\n"
                    f"{files_str}\n\n"
                    f"Based on the file names, classify the overall change in ONE WORD "
                    f"(feature, bugfix, refactor, test, config, docs, other) "
                    f"and write a ONE SENTENCE summary.\n"
                    f"CATEGORY: <word>\nSUMMARY: <sentence>"
                )
                result = self.react_loop.llm.call_tiered(
                    messages=[{"role": "user", "content": classify_prompt}],
                    tier="fast"
                )
                text = result.get("text", "")
                for line in text.split("\n"):
                    if line.strip().upper().startswith("SUMMARY:"):
                        offline_summary = line.split(":", 1)[1].strip()
                        latest = self.db.fetchone(
                            "SELECT id FROM changes WHERE category = 'catch-up' ORDER BY id DESC LIMIT 1"
                        )
                        if latest:
                            self.db.update("changes",
                                {"diff_summary": offline_summary},
                                "id = ?", (latest["id"],))
                        break
            except Exception as e:
                log.error(f"Catch-up classification failed: {e}")

        # Save new snapshots
        self._save_snapshots()

    def _save_snapshots(self):
        """Persist file hashes to DB for catch-up across restarts."""
        import hashlib

        try:
            self.db.execute("DELETE FROM file_snapshots")
            for rel_path, content in self._snapshots.items():
                norm_path = rel_path.replace("\\", "/")
                file_hash = hashlib.md5(content.encode()).hexdigest()
                self.db.execute(
                    "INSERT OR REPLACE INTO file_snapshots (path, hash, size, lines) VALUES (?, ?, ?, ?)",
                    (norm_path, file_hash, len(content.encode()), len(content.splitlines()))
                )
            self.db.conn.commit()
            log.info(f"Saved {len(self._snapshots)} file hashes for catch-up")
        except Exception as e:
            log.error(f"Failed to save snapshots: {e}")

    def should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        path_str = str(path).replace("\\", "/")

        # Agent-0's own knowledge folder
        if "/agent-0/" in path_str or path_str.endswith("/agent-0"):
            return True

        # Temp files
        if ".tmp." in path_str or path_str.endswith(".tmp") or path_str.endswith("~"):
            return True

        # Build artifacts
        if "/target/" in path_str or "/dist/" in path_str or "/build/" in path_str:
            return True

        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str.split("/"):
                return True
        return False

    def _compute_diff(self, rel_path: str) -> str:
        """Compute a real diff between the snapshot and current file content."""
        full_path = self.project_path / rel_path

        if not full_path.exists():
            old = self._snapshots.get(rel_path, "")
            if old:
                self._snapshots.pop(rel_path, None)
                return f"FILE DELETED. Previous content ({len(old.splitlines())} lines) removed."
            return "File deleted (no previous snapshot)."

        try:
            new_content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return "Cannot read file."

        old_content = self._snapshots.get(rel_path, "")

        # Update snapshot
        self._snapshots[rel_path] = new_content

        if not old_content:
            # New file
            lines = new_content.splitlines()
            preview = "\n".join(lines[:30])
            return f"NEW FILE ({len(lines)} lines):\n{preview}" + ("\n..." if len(lines) > 30 else "")

        if old_content == new_content:
            return "No actual content change (metadata only)."

        # Compute simple line diff
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        added = []
        removed = []

        # Simple diff: find lines that differ
        old_set = set(old_lines)
        new_set = set(new_lines)

        for line in new_lines:
            if line not in old_set and line.strip():
                added.append(f"+ {line}")
        for line in old_lines:
            if line not in new_set and line.strip():
                removed.append(f"- {line}")

        diff_lines = []
        if removed:
            diff_lines.extend(removed[:15])
        if added:
            diff_lines.extend(added[:15])

        if not diff_lines:
            return f"Minor change (whitespace/reordering). Lines: {len(old_lines)} -> {len(new_lines)}"

        total = len(added) + len(removed)
        result = f"Changed {total} lines ({len(added)} added, {len(removed)} removed):\n"
        result += "\n".join(diff_lines[:30])
        if total > 30:
            result += f"\n... ({total - 30} more lines)"

        return result

    def _on_changes(self, changes: set):
        """Handle a batch of file changes from watchfiles."""
        with self._lock:
            for change_type, path in changes:
                if self.should_ignore(path):
                    continue

                change_name = {
                    Change.added: "added",
                    Change.modified: "modified",
                    Change.deleted: "deleted"
                }.get(change_type, "unknown")

                self._pending_changes[path] = {
                    "path": path,
                    "type": change_name,
                    "timestamp": time.time()
                }

            if self._debounce_timer:
                self._debounce_timer.cancel()

            self._debounce_timer = threading.Timer(
                self.debounce_seconds,
                self._process_batch
            )
            self._debounce_timer.start()

    def _process_batch(self):
        """Process accumulated changes after debounce window."""
        with self._lock:
            if not self._pending_changes:
                return
            batch = dict(self._pending_changes)
            self._pending_changes.clear()

        # Filter to only real files (with extensions, not directories)
        # Deduplicate by relative path (same file changed multiple times = one entry)
        seen_files = set()
        real_changes = {}
        for path, info in batch.items():
            p = Path(path)
            if p.suffix and p.suffix.lower() in TEXT_EXTENSIONS:
                try:
                    rel = str(p.relative_to(self.project_path))
                except ValueError:
                    rel = str(p)
                if rel not in seen_files:
                    seen_files.add(rel)
                    real_changes[path] = info

        if not real_changes:
            return  # Only directories or binary files changed, skip

        num = len(real_changes)
        if num >= self.config.get("cost.bulk_threshold", 50):
            print(f"  [WATCHER] Bulk change: {num} files")
            self._handle_bulk(real_changes)
        else:
            print(f"  [WATCHER] {num} file(s) changed:")
            for path, info in real_changes.items():
                try:
                    rel = str(Path(path).relative_to(self.project_path))
                except ValueError:
                    rel = path
                print(f"            {info['type']:>8}  {rel}")
            self._handle_changes(real_changes)

    def _handle_changes(self, changes: dict):
        """Full pipeline in a background thread."""
        thread = threading.Thread(
            target=self._process_pipeline,
            args=(changes,),
            daemon=True
        )
        thread.start()

    def _process_pipeline(self, changes: dict):
        """The full Agent-0 pipeline with real diffs and content."""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M")
        date = now.strftime("%Y-%m-%d")

        # 1. Build file list and compute REAL diffs
        files_info = []
        for path, info in changes.items():
            try:
                rel = str(Path(path).relative_to(self.project_path))
            except ValueError:
                rel = path

            diff = self._compute_diff(rel)
            files_info.append({
                "path": rel,
                "type": info["type"],
                "diff": diff
            })

        file_names = [f["path"] for f in files_info]
        files_str = ", ".join(file_names[:5])
        log.info(f"Pipeline: {len(files_info)} file(s): {files_str}")

        # 2. Classify with ACTUAL DIFF CONTENT (not just filenames)
        classification = "unknown"
        diff_summary = ""
        if self.react_loop:
            try:
                # Build a prompt with real content
                diff_text = ""
                for fi in files_info[:3]:  # Limit to 3 files for token budget
                    diff_text += f"\n--- {fi['path']} ({fi['type']}) ---\n"
                    diff_text += fi["diff"][:1000]  # Limit per-file diff
                    diff_text += "\n"

                classify_prompt = (
                    f"You are reviewing code changes. Based on the ACTUAL DIFFS below, "
                    f"classify and summarize.\n\n"
                    f"Respond EXACTLY in this format:\n"
                    f"CATEGORY: <one word: feature, bugfix, refactor, patch, test, config, docs, other>\n"
                    f"SUMMARY: <one factual sentence describing what actually changed>\n\n"
                    f"DIFFS:\n{diff_text}"
                )
                result = self.react_loop.llm.call_tiered(
                    messages=[{"role": "user", "content": classify_prompt}],
                    tier="fast"
                )
                text = result.get("text", "")
                for line in text.split("\n"):
                    line = line.strip()
                    if line.upper().startswith("CATEGORY:"):
                        classification = line.split(":", 1)[1].strip().lower().split()[0]
                    elif line.upper().startswith("SUMMARY:"):
                        diff_summary = line.split(":", 1)[1].strip()
                log.info(f"Classification: {classification} | {diff_summary}")
            except Exception as e:
                log.error(f"Classification failed: {e}")

        # 3. Get active session
        active_session = None
        if self.reasoning:
            active_session = self.reasoning.get_active_session()

        # 4. Write to DB
        if self.db:
            change_id = self.db.insert("changes", {
                "files_changed": "\n".join(file_names),
                "diff_summary": diff_summary or f"{len(files_info)} file(s) changed",
                "category": classification,
                "session_id": active_session["id"] if active_session else None
            })
            log.info(f"DB: change #{change_id}")

        # 5. Write to session markdown with real details
        if self.store:
            entry = f"\n### {timestamp} | {classification}\n"
            entry += f"**Files:** {files_str}\n"
            entry += f"**Summary:** {diff_summary or 'No summary'}\n"
            # Include actual diff highlights
            for fi in files_info[:3]:
                diff_preview = fi["diff"][:300]
                entry += f"\n`{fi['path']}` ({fi['type']}):\n```\n{diff_preview}\n```\n"
            entry += "\n"
            self.store.write(f"sessions/{date}.md", entry, mode="append")
            log.info(f"MD: sessions/{date}.md")

            # Re-index so search_knowledge can find it
            if self.indexer:
                try:
                    self.indexer.reindex_if_changed(f"sessions/{date}.md")
                except Exception:
                    pass

        # 6. Reasoning checks
        if self.reasoning:
            drift = self.reasoning.check_drift(classification, file_names, diff_summary)
            if drift["drifting"]:
                log.warning(f"DRIFT: {drift['message']}")
                if self.db:
                    self.db.insert("alerts", {
                        "message": drift["message"],
                        "type": "drift",
                        "severity": "medium"
                    })

            patterns = self.reasoning.find_patterns(file_names, classification, diff_summary)
            for p in patterns:
                if p["severity"] in ("medium", "high"):
                    log.info(f"PATTERN: {p['description']}")
                    if self.db:
                        self.db.insert("alerts", {
                            "message": p["description"],
                            "type": "pattern",
                            "severity": p["severity"]
                        })

            self.reasoning.track_debt(classification, file_names, diff_summary)
            self.reasoning.detect_dependency_gospel(file_names)
            self.reasoning.track_cost(
                self.react_loop.llm.model if self.react_loop else "unknown",
                input_tokens=800, output_tokens=150
            )

            if self.reasoning.should_checkpoint():
                try:
                    from tools import execute_tool
                    execute_tool("create_checkpoint", {"trigger": "scheduled"})
                except Exception:
                    pass

        # 7. Update state (preserve phase info AND scan results)
        if self.store:
            # Read phase info from DB (source of truth)
            current_phase = "Unknown"
            phase_goal = "Unknown"
            if self.db:
                try:
                    phase = self.db.fetchone(
                        "SELECT name, goal FROM phases WHERE status IN ('open', 'in_progress') ORDER BY id DESC LIMIT 1"
                    )
                    if phase:
                        current_phase = phase["name"] or "Unknown"
                        phase_goal = phase["goal"] or "Unknown"
                except Exception:
                    pass

            # Preserve scan results section from existing state file
            scan_section = ""
            state_path = self.config.knowledge_dir / "state" / "current.md"
            if state_path.exists():
                try:
                    old_state = state_path.read_text(encoding="utf-8", errors="replace")
                    if "## Latest Scan Results" in old_state:
                        scan_section = old_state[old_state.index("\n## Latest Scan Results"):]
                except Exception:
                    pass

            self.store.write("state/current.md", (
                f"# Current State\n\n"
                f"**Project:** {self.config.get('project_name')}\n"
                f"**Status:** Active\n"
                f"**Current Phase:** {current_phase}\n"
                f"**Phase Goal:** {phase_goal}\n"
                f"**Last Change:** {timestamp}\n"
                f"**Last Classification:** {classification}\n"
                f"**Last Summary:** {diff_summary}\n"
                f"**Last Files:** {files_str}\n"
                f"**Session:** #{active_session['id'] if active_session else 'None'}\n"
                f"{scan_section}"
            ), mode="overwrite")

            if self.indexer:
                try:
                    self.indexer.reindex_if_changed("state/current.md")
                except Exception:
                    pass

        # 8. KNOWLEDGE RECONCILIATION — cross-reference change against what Agent-0 tracks
        if self.db and self.react_loop and classification in ("bugfix", "patch", "feature", "refactor"):
            self._reconcile_knowledge(files_info, classification, diff_summary, timestamp)

        # 9. Quick scan changed code files for bugs (semgrep + bandit)
        code_exts = {".py", ".kt", ".java", ".js", ".ts", ".kts"}
        code_files_changed = [fi["path"] for fi in files_info if Path(fi["path"]).suffix in code_exts]
        if code_files_changed:
            try:
                from memory.code_scanner import run_semgrep, run_bandit
                scan_findings = []
                for fpath in code_files_changed[:3]:
                    full = self.project_path / fpath
                    if full.exists():
                        findings = run_semgrep(full.parent)
                        for f in findings:
                            if full.name in f["file"]:
                                scan_findings.append(f)

                if scan_findings:
                    # Write to session log (NOT to alerts — scan findings stay in session logs and scan_results.md)
                    if self.store:
                        scan_note = f"\n**Code scan ({len(scan_findings)} finding(s) in changed files):**\n"
                        for f in scan_findings[:5]:
                            scan_note += f"- [{f['severity']}] {f['rule'].split('.')[-1]} in {Path(f['file']).name}:{f['line']}\n"
                        self.store.write(f"sessions/{date}.md", scan_note, mode="append")

                    # Ping agent
                    if self.briefing:
                        self.briefing.add_ping(
                            f"Code scan found {len(scan_findings)} issue(s) in changed files: "
                            + ", ".join(f"{f['rule'].split('.')[-1]}" for f in scan_findings[:3]),
                            "code_scan"
                        )

                    log.info(f"Quick scan: {len(scan_findings)} finding(s) in changed files")
            except Exception as e:
                log.debug(f"Quick scan skipped: {e}")

        # 10. Track changes for stale doc detection
        self._changes_since_doc_update += 1
        is_doc_change = any(fi["path"].endswith(".md") for fi in files_info)
        if is_doc_change:
            self._changes_since_doc_update = 0

        # Ping if 10+ code changes without any doc update
        if self._changes_since_doc_update >= 10 and self.briefing:
            self.briefing.add_ping(
                f"{self._changes_since_doc_update} code changes since the last doc update. "
                f"When you finish your current task, please update ACTIVE_WORK.md with what you're working on.",
                "stale_docs"
            )
            self._changes_since_doc_update = 0  # Reset after ping

        # 11. If a key doc changed, re-read it AND reconcile against tracked items
        key_docs = {"KNOWN_ISSUES", "ACTIVE_WORK", "COMPLETED_WORK", "CLAUDE",
                    "ROADMAP", "CHANGELOG", "TODO", "OUTSTANDING", "HARDENING"}
        for fi in files_info:
            fname_upper = Path(fi["path"]).stem.upper()
            if any(kd in fname_upper for kd in key_docs):
                if self.react_loop and self.store:
                    try:
                        full_path = self.project_path / fi["path"]
                        if full_path.exists():
                            text = full_path.read_text(encoding="utf-8", errors="replace")[:15000]

                            # Get current open items for cross-reference
                            open_items_ctx = ""
                            if self.db:
                                items = self.db.fetchall(
                                    "SELECT id, description, type FROM open_items WHERE status = 'open' LIMIT 15"
                                )
                                if items:
                                    open_items_ctx = (
                                        "\n\nAgent-0 currently tracks these open items:\n" +
                                        "\n".join(f"- #{i['id']}: {i['description'][:100]}" for i in items) +
                                        "\n\nIf any of these are now resolved based on the doc content, "
                                        "list them as: RESOLVED_IDS: 1, 2, 3\n"
                                    )

                            summary = self.react_loop.llm.call_tiered(
                                messages=[{"role": "user", "content":
                                    f"A key project document changed: {fi['path']}. "
                                    f"Summarize the current content thoroughly. "
                                    f"Mark items as OPEN or RESOLVED based on the document's content. "
                                    f"If items are checked off, marked DONE/FIXED/RESOLVED, treat them as resolved.\n\n"
                                    f"{text}{open_items_ctx}"}],
                                tier="mid"
                            ).get("text", "")

                            if summary:
                                self.store.write(f"docs/live_{fname_upper.lower()}.md",
                                    f"# {fi['path']} (Updated {timestamp})\n\n{summary}\n",
                                    mode="overwrite")
                                log.info(f"Updated knowledge for key doc: {fi['path']}")

                                # Check for RESOLVED_IDS in the summary
                                if self.db:
                                    for line in summary.split("\n"):
                                        if "RESOLVED_IDS:" in line.upper():
                                            ids_str = line.split(":", 1)[1].strip()
                                            for id_str in ids_str.replace(",", " ").split():
                                                try:
                                                    item_id = int(id_str.strip().lstrip("#"))
                                                    self.db.update("open_items", {
                                                        "status": "resolved",
                                                        "resolved": timestamp
                                                    }, "id = ? AND status = 'open'", (item_id,))
                                                    log.info(f"Doc reconcile: closed open_item #{item_id}")
                                                except (ValueError, Exception):
                                                    pass

                                # Re-index the updated knowledge
                                if self.indexer:
                                    try:
                                        self.indexer.reindex_if_changed(f"docs/live_{fname_upper.lower()}.md")
                                    except Exception:
                                        pass

                    except Exception as e:
                        log.error(f"Failed to update key doc knowledge: {e}")

        # 12. Track module changes and refresh knowledge when enough accumulate
        #     Also do a full refresh every 12 hours regardless
        if self.react_loop and self.store:
            self._track_and_refresh_knowledge(files_info, classification, diff_summary, timestamp)
            self._check_timed_refresh(timestamp)

        # 13. Auto-scan after 5+ code changes
        code_exts_all = {".py", ".kt", ".java", ".js", ".ts", ".kts", ".swift", ".go", ".rs", ".cpp", ".c"}
        code_changed = any(Path(fi["path"]).suffix in code_exts_all for fi in files_info)
        if code_changed:
            self._code_changes_since_scan += len([fi for fi in files_info if Path(fi["path"]).suffix in code_exts_all])
            if self._code_changes_since_scan >= 5:
                self._run_auto_scan(timestamp)
                self._code_changes_since_scan = 0

        log.info(f"Pipeline done: {len(files_info)} files, {classification}")

    def _track_and_refresh_knowledge(self, files_info: list, classification: str,
                                      diff_summary: str, timestamp: str):
        """Track which modules are changing and refresh knowledge when enough changes accumulate.
        This keeps Agent-0's deep knowledge current as the codebase evolves."""
        try:
            # Group changed files by top-level module
            for fi in files_info:
                path_parts = fi["path"].replace("\\", "/").split("/")
                module = path_parts[0] if len(path_parts) > 1 else "(root)"
                self._module_change_counts[module] = self._module_change_counts.get(module, 0) + 1

            # Check if any module has 5+ changes since last refresh
            for module, count in list(self._module_change_counts.items()):
                if count < 5:
                    continue

                # Reset counter
                self._module_change_counts[module] = 0

                # Check if we have a knowledge file for this module
                knowledge_file = f"code/{module}.md"
                existing = self.store.read(knowledge_file)
                if not existing or "File not found" in existing:
                    continue  # No knowledge file for this module, skip

                # Collect recent changes for this module from the session log
                recent_changes = []
                if self.db:
                    changes = self.db.fetchall(
                        "SELECT diff_summary, category, files_changed FROM changes "
                        "WHERE files_changed LIKE ? ORDER BY id DESC LIMIT 10",
                        (f"%{module}%",)
                    )
                    for c in changes:
                        recent_changes.append(
                            f"- [{c.get('category', '?')}] {c.get('diff_summary', '')[:150]}"
                        )

                if not recent_changes:
                    continue

                recent_text = "\n".join(recent_changes)

                # Ask LLM to update the knowledge with recent changes
                update = self.react_loop.llm.call_tiered(
                    messages=[{"role": "user", "content":
                        f"You are updating Agent-0's knowledge about the '{module}' module.\n\n"
                        f"CURRENT KNOWLEDGE:\n{existing[:4000]}\n\n"
                        f"RECENT CHANGES (newest first):\n{recent_text}\n\n"
                        f"Write an UPDATED version of the knowledge that incorporates these changes. "
                        f"Keep existing accurate information. Add new features/changes. "
                        f"Mark fixed bugs as resolved. Update file descriptions if they changed. "
                        f"Be specific — use file names, class names, function names.\n"
                        f"Start with: # Module: {module} (Updated {timestamp})"}],
                    tier="mid"
                ).get("text", "")

                if update and len(update) > 100:
                    self.store.write(knowledge_file, update, mode="overwrite")
                    log.info(f"Knowledge refresh: updated {knowledge_file} ({count} changes)")

                    if self.indexer:
                        try:
                            self.indexer.reindex_if_changed(knowledge_file)
                        except Exception:
                            pass

                    if self.briefing:
                        self.briefing.add_ping(
                            f"Updated knowledge for module '{module}' — {count} changes since last update.",
                            "knowledge_refresh"
                        )

        except Exception as e:
            log.error(f"Knowledge refresh failed: {e}")

    def _run_auto_scan(self, timestamp: str):
        """Run full code scan after 5+ code changes. Updates scan_results.md and state/current.md."""
        try:
            from memory.code_scanner import run_scan, format_findings

            log.info("Auto-scan triggered: 5+ code changes since last scan")

            results = run_scan(self.project_path)

            if results["total"] > 0:
                # Update scan_results.md
                if self.store:
                    self.store.write("scan_results.md", format_findings(results), mode="overwrite")

                # Generate curated audit report
                if self.react_loop and self.store:
                    try:
                        from memory.code_scanner import analyze_findings
                        analyze_findings(results, self.react_loop.llm, self.store, self.project_path)
                    except Exception as e:
                        log.error(f"Audit analysis failed: {e}")

                # Update scan summary in state/current.md
                state_path = self.config.knowledge_dir / "state" / "current.md"
                if state_path.exists():
                    state_content = state_path.read_text(encoding="utf-8", errors="replace")
                else:
                    state_content = f"# Current State\n\n**Project:** {self.config.get('project_name')}\n"

                # Remove old scan section
                scan_marker = "\n## Latest Scan Results"
                if scan_marker in state_content:
                    state_content = state_content[:state_content.index(scan_marker)]

                high_count = results["by_severity"].get("HIGH", 0) + results["by_severity"].get("ERROR", 0) + results["by_severity"].get("CRITICAL", 0)
                med_count = results["by_severity"].get("MEDIUM", 0) + results["by_severity"].get("WARNING", 0)
                low_count = results["by_severity"].get("LOW", 0) + results["by_severity"].get("INFO", 0)

                scan_summary = (
                    f"\n## Latest Scan Results\n\n"
                    f"**Scanned:** {timestamp}\n"
                    f"**Total findings:** {results['total']}\n"
                    f"**HIGH:** {high_count} | **MEDIUM:** {med_count} | **LOW:** {low_count}\n"
                    f"**Cross-referenced:** {results.get('cross_referenced', 0)} confirmed by multiple tools\n\n"
                )
                if results["findings"]:
                    scan_summary += "**Top findings:**\n"
                    for f in results["findings"][:10]:
                        scan_summary += f"- [{f['severity']}] {f['rule'].split('.')[-1]}: {f['message'][:100]} in {f['file']}:{f['line']}\n"
                    scan_summary += f"\n*Full details in scan_results.md*\n"

                state_content += scan_summary
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(state_content, encoding="utf-8")

                # One summary alert
                if self.db and high_count > 0:
                    self.db.insert("alerts", {
                        "message": f"Auto-scan ({timestamp}): {results['total']} findings ({high_count} HIGH). See scan_results.md.",
                        "type": "code_scan_summary",
                        "severity": "high" if high_count > 10 else "medium"
                    })

                # Ping
                if self.briefing:
                    self.briefing.add_ping(
                        f"Auto-scan complete after 5+ code changes: {results['total']} findings "
                        f"({high_count} HIGH, {med_count} MEDIUM, {low_count} LOW). "
                        f"Check scan_results.md for details.",
                        "auto_scan"
                    )

                log.info(f"Auto-scan complete: {results['total']} findings ({high_count} HIGH)")
            else:
                log.info("Auto-scan complete: no issues found")

                if self.briefing:
                    self.briefing.add_ping(
                        "Auto-scan complete after 5+ code changes: no issues found.",
                        "auto_scan"
                    )

        except Exception as e:
            log.error(f"Auto-scan failed: {e}")

    def _check_timed_refresh(self, timestamp: str):
        """Every 12 hours, do a full knowledge refresh for all modules that have had ANY changes.
        This catches the case where a module gets 1-4 changes (below the 5-change threshold)
        but still needs its knowledge updated."""
        now = datetime.now()

        # Initialize on first call
        if self._last_full_refresh is None:
            # Check DB for when knowledge was last written
            try:
                from pathlib import Path as P
                code_dir = self.config.knowledge_dir / "code"
                if code_dir.exists():
                    newest = max(
                        (f.stat().st_mtime for f in code_dir.glob("*.md")),
                        default=0
                    )
                    if newest > 0:
                        self._last_full_refresh = datetime.fromtimestamp(newest)
                    else:
                        self._last_full_refresh = now
                else:
                    self._last_full_refresh = now
            except Exception:
                self._last_full_refresh = now
            return

        hours_since = (now - self._last_full_refresh).total_seconds() / 3600
        if hours_since < 12:
            return

        # Time for a full refresh
        log.info(f"Timed knowledge refresh: {hours_since:.0f}h since last refresh")
        self._last_full_refresh = now

        # Find all code knowledge files
        try:
            code_dir = self.config.knowledge_dir / "code"
            if not code_dir.exists():
                return

            for md_file in sorted(code_dir.glob("*.md")):
                module = md_file.stem
                existing = self.store.read(f"code/{module}.md")
                if not existing or "File not found" in existing:
                    continue

                # Get changes for this module since knowledge was last written
                changes = self.db.fetchall(
                    "SELECT diff_summary, category FROM changes "
                    "WHERE files_changed LIKE ? ORDER BY id DESC LIMIT 15",
                    (f"%{module}%",)
                ) if self.db else []

                if not changes:
                    continue

                recent_text = "\n".join(
                    f"- [{c.get('category', '?')}] {c.get('diff_summary', '')[:150]}"
                    for c in changes
                )

                update = self.react_loop.llm.call_tiered(
                    messages=[{"role": "user", "content":
                        f"Update Agent-0's knowledge about '{module}' module.\n\n"
                        f"CURRENT:\n{existing[:5000]}\n\n"
                        f"RECENT CHANGES:\n{recent_text}\n\n"
                        f"Write UPDATED version incorporating changes. Keep accurate info, add new, "
                        f"mark fixed as resolved. Use file/class/function names.\n"
                        f"Start with: # Module: {module} (Updated {timestamp})"}],
                    tier="mid"
                ).get("text", "")

                if update and len(update) > 200:
                    self.store.write(f"code/{module}.md", update, mode="overwrite")
                    log.info(f"Timed refresh: updated code/{module}.md")

                    if self.indexer:
                        try:
                            self.indexer.reindex_if_changed(f"code/{module}.md")
                        except Exception:
                            pass

            # Also refresh docs/current_state.md
            state_existing = self.store.read("docs/current_state.md")
            if state_existing and "File not found" not in state_existing:
                all_changes = self.db.fetchall(
                    "SELECT diff_summary, category, timestamp FROM changes "
                    "ORDER BY id DESC LIMIT 20"
                ) if self.db else []

                if all_changes:
                    changes_text = "\n".join(
                        f"- [{c.get('category', '?')}] {c.get('diff_summary', '')[:150]}"
                        for c in all_changes
                    )

                    result = self.react_loop.llm.call_tiered(
                        messages=[{"role": "user", "content":
                            f"Update Agent-0's current state knowledge for this project.\n\n"
                            f"CURRENT:\n{state_existing[:5000]}\n\n"
                            f"RECENT CHANGES:\n{changes_text}\n\n"
                            f"Write UPDATED current state. Include active work, recent features, "
                            f"fixed bugs, known issues. Be specific.\n"
                            f"Start with: # Current State (Updated {timestamp})"}],
                        tier="mid"
                    ).get("text", "")

                    if result and len(result) > 200:
                        self.store.write("docs/current_state.md", result, mode="overwrite")
                        log.info("Timed refresh: updated docs/current_state.md")

            if self.briefing:
                self.briefing.add_ping(
                    f"Completed scheduled 12-hour knowledge refresh. All module docs updated.",
                    "knowledge_refresh"
                )

        except Exception as e:
            log.error(f"Timed knowledge refresh failed: {e}")

    def _reconcile_knowledge(self, files_info: list, classification: str, diff_summary: str, timestamp: str):
        """Cross-reference a code change against Agent-0's tracked knowledge.
        If a bugfix lands, close matching open_items/alerts.
        If code changes, update relevant knowledge docs."""
        try:
            file_names = [fi["path"] for fi in files_info]
            file_names_str = ", ".join(file_names[:5])

            # 1. PROGRAMMATIC: Check open_items and alerts that mention these files
            resolved_items = []
            for fname in file_names:
                # Normalize: use just the filename for matching
                base = Path(fname).name
                stem = Path(fname).stem

                # Search open_items for matches
                items = self.db.fetchall(
                    "SELECT id, description FROM open_items WHERE status = 'open' "
                    "AND (description LIKE ? OR description LIKE ?)",
                    (f"%{base}%", f"%{stem}%")
                )
                for item in items:
                    resolved_items.append(("open_items", item["id"], item["description"]))

                # Search undismissed alerts for matches (only if this is a bugfix)
                if classification in ("bugfix", "patch"):
                    alerts = self.db.fetchall(
                        "SELECT id, message FROM alerts WHERE dismissed = 0 "
                        "AND (message LIKE ? OR message LIKE ?)",
                        (f"%{base}%", f"%{stem}%")
                    )
                    for alert in alerts:
                        resolved_items.append(("alerts", alert["id"], alert["message"]))

            # Mark matched items as resolved
            for table, item_id, desc in resolved_items:
                if table == "open_items":
                    self.db.update("open_items", {
                        "status": "resolved",
                        "resolved": timestamp
                    }, "id = ?", (item_id,))
                    log.info(f"Reconcile: closed open_item #{item_id}: {desc[:80]}")
                elif table == "alerts":
                    self.db.update("alerts", {
                        "dismissed": 1,
                        "response": f"Auto-resolved by {classification}: {diff_summary[:100]}"
                    }, "id = ?", (item_id,))
                    log.info(f"Reconcile: dismissed alert #{item_id}: {desc[:80]}")

            # 2. LLM-ASSISTED: For significant changes, ask the LLM to identify what
            #    this change means for Agent-0's tracked knowledge
            diff_text = ""
            for fi in files_info[:2]:
                diff_text += f"{fi['path']}: {fi['diff'][:500]}\n"

            # Get current tracked issues for context
            open_items = self.db.fetchall(
                "SELECT id, description FROM open_items WHERE status = 'open' LIMIT 10"
            )
            open_items_text = "\n".join(
                f"- #{i['id']}: {i['description'][:100]}" for i in open_items
            ) if open_items else "None"

            reconcile_prompt = (
                f"A {classification} just landed in the codebase.\n"
                f"Files: {file_names_str}\n"
                f"Summary: {diff_summary}\n"
                f"Diff:\n{diff_text}\n\n"
                f"Currently tracked open items:\n{open_items_text}\n\n"
                f"Questions (answer ONLY what applies, skip if nothing):\n"
                f"1. RESOLVED_IDS: Which open item IDs (if any) does this change resolve? (comma-separated numbers, or NONE)\n"
                f"2. KNOWLEDGE_UPDATE: What should Agent-0 update in its knowledge? (one sentence, or NONE)\n"
                f"3. NEW_ISSUE: Does this change introduce a new concern? (one sentence, or NONE)\n"
            )

            result = self.react_loop.llm.call_tiered(
                messages=[{"role": "user", "content": reconcile_prompt}],
                tier="fast"
            )
            text = result.get("text", "")

            for line in text.split("\n"):
                line = line.strip()

                # Close open items the LLM identified
                if line.upper().startswith("RESOLVED_IDS:"):
                    ids_str = line.split(":", 1)[1].strip()
                    if ids_str.upper() != "NONE":
                        for id_str in ids_str.replace(",", " ").split():
                            try:
                                item_id = int(id_str.strip().lstrip("#"))
                                self.db.update("open_items", {
                                    "status": "resolved",
                                    "resolved": timestamp
                                }, "id = ? AND status = 'open'", (item_id,))
                                log.info(f"Reconcile (LLM): closed open_item #{item_id}")
                            except (ValueError, Exception):
                                pass

                # Write knowledge update
                elif line.upper().startswith("KNOWLEDGE_UPDATE:"):
                    update = line.split(":", 1)[1].strip()
                    if update.upper() != "NONE" and len(update) > 10 and self.store:
                        date = datetime.now().strftime("%Y-%m-%d")
                        self.store.write(f"sessions/{date}.md",
                            f"\n**Knowledge update ({timestamp}):** {update}\n",
                            mode="append")
                        log.info(f"Reconcile: knowledge update: {update[:80]}")

                # Track new concern
                elif line.upper().startswith("NEW_ISSUE:"):
                    issue = line.split(":", 1)[1].strip()
                    if issue.upper() != "NONE" and len(issue) > 10:
                        self.db.insert("open_items", {
                            "description": issue[:300],
                            "type": "auto_detected",
                            "status": "open"
                        })
                        log.info(f"Reconcile: new issue tracked: {issue[:80]}")

            # 3. Ping about reconciliation if anything was resolved
            if resolved_items and self.briefing:
                self.briefing.add_ping(
                    f"Change reconciled: {len(resolved_items)} tracked issue(s) auto-resolved by {classification}. "
                    f"Files: {file_names_str}",
                    "reconciliation"
                )

            if resolved_items:
                log.info(f"Reconciliation: {len(resolved_items)} items resolved programmatically")

        except Exception as e:
            log.error(f"Knowledge reconciliation failed: {e}")

    def _handle_bulk(self, changes: dict):
        """Handle bulk changes (50+ files)."""
        if not self.store or not self.db:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        date = datetime.now().strftime("%Y-%m-%d")

        dirs = {}
        for path in changes:
            try:
                rel = str(Path(path).relative_to(self.project_path))
            except ValueError:
                rel = path
            parts = rel.replace("\\", "/").split("/")
            top_dir = parts[0] if len(parts) > 1 else "(root)"
            dirs[top_dir] = dirs.get(top_dir, 0) + 1

        summary = f"### Bulk Change ({now})\n"
        summary += f"**{len(changes)} files changed**\n"
        for d, count in sorted(dirs.items(), key=lambda x: -x[1])[:10]:
            summary += f"- {d}: {count} files\n"

        self.store.write(f"sessions/{date}.md", summary + "\n", mode="append")
        self.db.insert("changes", {
            "files_changed": f"BULK: {len(changes)} files",
            "diff_summary": summary[:200],
            "category": "bulk"
        })

        # Rebuild snapshots after bulk change
        self._build_initial_snapshots()

    def start(self):
        """Start watching."""
        self._running = True
        try:
            for changes in watch(
                str(self.project_path),
                stop_event=self._stop_event,
                watch_filter=None,
                recursive=True
            ):
                if not self._running:
                    break
                self._on_changes(changes)
        except Exception as e:
            print(f"  [WATCHER] Error: {e}")

    def stop(self):
        """Stop watching. Save snapshots for catch-up on next start."""
        self._running = False
        self._stop_event.set()
        if self._debounce_timer:
            self._debounce_timer.cancel()
        # Persist snapshots so catch-up works on restart
        if self.db and self._snapshots:
            self._save_snapshots()

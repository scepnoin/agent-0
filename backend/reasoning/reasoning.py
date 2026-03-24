"""
Agent-0 Reasoning Module
Drift detection, pattern matching, debt tracking, session awareness.
This is NOT deep AI reasoning — it's simple, reliable comparison logic
that feeds into the ReACT loop's decision making.
"""

from datetime import datetime, timedelta
from logger import get_logger

log = get_logger("reasoning")


class ReasoningEngine:
    """Simple reasoning helpers for Agent-0."""

    def __init__(self, db, store, config):
        self.db = db
        self.store = store
        self.config = config

    # ── Drift Detection ──────────────────────────────────

    def check_drift(self, change_category: str, files_changed: list[str],
                    diff_summary: str) -> dict:
        """
        Check if recent changes are drifting from BOTH session intent AND phase goal.
        Session intent takes priority (more specific).
        Returns: {drifting: bool, score: float, message: str, consecutive: int}
        """
        # Check session intent first (more specific than phase goal)
        active_session = self.get_active_session()
        session_intent = active_session.get("intent", "") if active_session else ""

        # Get current phase
        active_phase = self.db.fetchone(
            "SELECT * FROM phases WHERE status IN ('open', 'in_progress') ORDER BY id DESC LIMIT 1"
        )

        # Use session intent if available, otherwise phase goal
        goal_source = "session intent"
        goal_text = session_intent
        if not goal_text:
            if active_phase and active_phase.get("goal"):
                goal_source = "phase goal"
                goal_text = active_phase["goal"]
            else:
                return {"drifting": False, "score": 0.0, "message": "No active intent or phase goal to drift from.", "consecutive": 0}

        phase_goal = goal_text
        phase_name = f"{goal_source}: {goal_text[:60]}"

        # Count recent changes that are unrelated to the phase
        recent = self.db.fetchall(
            "SELECT * FROM changes WHERE phase_id = ? ORDER BY id DESC LIMIT 10",
            (active_phase["id"],)
        )

        # Simple heuristic: if category is 'bugfix' or 'refactor' while phase goal
        # is about features, that's potential drift
        unrelated_count = 0
        for change in recent:
            cat = change.get("category", "")
            if cat in ("bugfix", "patch", "refactor") and "fix" not in phase_goal.lower():
                unrelated_count += 1

        # Count consecutive unrelated changes (most recent first)
        consecutive = 0
        for change in recent:
            cat = change.get("category", "")
            if cat in ("bugfix", "patch", "refactor"):
                consecutive += 1
            else:
                break

        # Drift score: 0.0 (on track) to 1.0 (fully drifted)
        drift_score = min(1.0, unrelated_count / 5.0)

        # Get strictness thresholds
        strictness = self.config.get("agent.strictness", "normal")
        thresholds = {"strict": 1, "normal": 3, "loose": 999}
        threshold = thresholds.get(strictness, 3)

        drifting = consecutive >= threshold

        message = ""
        if drifting:
            message = (
                f"Drift detected: {consecutive} consecutive changes unrelated to "
                f"phase '{phase_name}' (goal: {phase_goal}). "
                f"Recent work appears to be {change_category} instead."
            )
            log.warning(message)

        return {
            "drifting": drifting,
            "score": drift_score,
            "message": message,
            "consecutive": consecutive,
            "phase": phase_name,
            "goal": phase_goal
        }

    # ── Pattern Matching ─────────────────────────────────

    def find_patterns(self, files_changed: list[str], change_category: str,
                      diff_summary: str) -> list[dict]:
        """
        Search for similar past events. Returns list of matching patterns.
        Each pattern: {match_type, description, original_change_id, similarity}
        """
        patterns = []

        # Pattern 1: Same file changed before AND that same file had an alert
        # The alert must mention the same file — NOT just happen at the same time
        for filepath in files_changed:
            filename = filepath.split("/")[-1].split("\\")[-1]

            # Find alerts that actually mention THIS file
            file_alerts = self.db.fetchall(
                "SELECT id, message, severity, type FROM alerts "
                "WHERE (message LIKE ? OR message LIKE ?) "
                "AND dismissed = 0 "
                "ORDER BY id DESC LIMIT 3",
                (f"%{filename}%", f"%{filepath}%")
            )

            for alert in file_alerts:
                # Skip scan-noise alerts (pattern alerts about other files)
                if alert["type"] == "pattern":
                    continue
                patterns.append({
                    "match_type": "file_alert",
                    "description": (
                        f"File '{filename}' has an active alert: {alert['message'][:150]}"
                    ),
                    "original_change_id": alert["id"],
                    "severity": alert.get("severity", "medium")
                })

        # Pattern 2: Same file changed 3+ times in the same session (churn)
        active = self.get_active_session()
        if active:
            for filepath in files_changed:
                filename = filepath.split("/")[-1].split("\\")[-1]
                count = self.db.fetchone(
                    "SELECT COUNT(*) as cnt FROM changes "
                    "WHERE files_changed LIKE ? AND session_id = ?",
                    (f"%{filename}%", active["id"])
                )
                if count and count["cnt"] >= 3:
                    patterns.append({
                        "match_type": "churn",
                        "description": (
                            f"File '{filename}' has been changed {count['cnt']} times "
                            f"this session — possible churn or instability."
                        ),
                        "original_change_id": None,
                        "severity": "low"
                    })

        # Pattern 3: Check knowledge patterns file
        patterns_md = self.store.read("patterns/patterns.md")
        if patterns_md and "File not found" not in patterns_md:
            for filepath in files_changed:
                filename = filepath.split("/")[-1].split("\\")[-1]
                if filename in patterns_md:
                    patterns.append({
                        "match_type": "knowledge_pattern",
                        "description": f"File '{filename}' has a known pattern in patterns/patterns.md",
                        "original_change_id": None,
                        "severity": "medium"
                    })

        if patterns:
            log.info(f"Found {len(patterns)} pattern(s) for changes in {files_changed}")

        return patterns

    # ── Debt Tracking ────────────────────────────────────

    def track_debt(self, change_category: str, files_changed: list[str],
                   diff_summary: str) -> dict | None:
        """
        Detect if a change is a patch (not a real fix) and log it as debt.
        Returns debt entry if detected, None otherwise.
        """
        # Heuristic: patches are quick fixes, often small, categorized as 'patch' or 'bugfix'
        is_patch = change_category in ("patch",)

        # Also detect band-aid patterns in diff
        bandaid_keywords = [
            "TODO", "FIXME", "HACK", "WORKAROUND", "TEMPORARY",
            "# quick fix", "# band-aid", "# temp fix"
        ]

        has_bandaid = any(kw.lower() in diff_summary.lower() for kw in bandaid_keywords)

        if is_patch or has_bandaid:
            debt_entry = {
                "description": f"Patch/workaround in {', '.join(files_changed[:3])}",
                "type": "debt",
                "status": "open",
                "linked_phase": None
            }

            # Get current phase
            active_phase = self.db.fetchone(
                "SELECT id FROM phases WHERE status IN ('open', 'in_progress') ORDER BY id DESC LIMIT 1"
            )
            if active_phase:
                debt_entry["linked_phase"] = active_phase["id"]

            # Insert into open_items
            item_id = self.db.insert("open_items", debt_entry)
            log.info(f"Debt tracked (item #{item_id}): {debt_entry['description']}")

            # Also append to debt ledger
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            ledger_entry = (
                f"\n### Debt #{item_id} ({timestamp})\n"
                f"**Files:** {', '.join(files_changed[:5])}\n"
                f"**Type:** {'Patch' if is_patch else 'Workaround detected'}\n"
                f"**Status:** Open\n"
            )
            self.store.write("debt/ledger.md", ledger_entry, mode="append")

            return debt_entry

        return None

    # ── Session Management ───────────────────────────────

    def start_session(self, intent: str = None) -> int:
        """Start a new work session. Closes any open sessions first. Returns session ID."""
        # Close any unclosed sessions
        open_sessions = self.db.fetchall("SELECT id FROM sessions WHERE ended IS NULL")
        for s in open_sessions:
            self.db.update("sessions", {
                "ended": datetime.now().isoformat(),
                "actual_outcome": "Auto-closed by new session"
            }, "id = ?", (s["id"],))

        session_id = self.db.insert("sessions", {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "intent": intent or "General work session",
            "started": datetime.now().isoformat()
        })
        log.info(f"Session #{session_id} started: {intent or 'General'}")

        # Write session file
        date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H:%M")
        header = f"\n## Session started at {timestamp}\n"
        if intent:
            header += f"**Intent:** {intent}\n"
        header += "\n"
        self.store.write(f"sessions/{date}.md", header, mode="append")

        return session_id

    def end_session(self, session_id: int, outcome: str = None) -> dict:
        """End a work session. Calculates drift score."""
        session = self.db.fetchone("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not session:
            return {"error": "Session not found"}

        # Calculate drift score from changes during this session
        changes = self.db.fetchall(
            "SELECT category FROM changes WHERE session_id = ?", (session_id,)
        )

        total = len(changes)
        if total == 0:
            drift_score = 0.0
        else:
            # What proportion of changes were unrelated (bugfix/patch during feature work)
            unrelated = sum(1 for c in changes if c["category"] in ("bugfix", "patch", "refactor"))
            drift_score = unrelated / total

        # Update session
        self.db.update("sessions", {
            "ended": datetime.now().isoformat(),
            "actual_outcome": outcome or f"{total} changes made",
            "drift_score": drift_score
        }, "id = ?", (session_id,))

        # Write to session file
        date = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H:%M")
        summary = (
            f"\n**Session ended at {timestamp}**\n"
            f"- Changes: {total}\n"
            f"- Drift score: {drift_score:.1%}\n"
            f"- Outcome: {outcome or 'Not specified'}\n"
        )
        self.store.write(f"sessions/{date}.md", summary, mode="append")

        log.info(f"Session #{session_id} ended. {total} changes, drift: {drift_score:.1%}")

        return {
            "session_id": session_id,
            "total_changes": total,
            "drift_score": drift_score,
            "outcome": outcome
        }

    def get_active_session(self) -> dict | None:
        """Get the currently active session (no end time)."""
        return self.db.fetchone(
            "SELECT * FROM sessions WHERE ended IS NULL ORDER BY id DESC LIMIT 1"
        )

    # ── Gospel Auto-Creation ─────────────────────────────

    def suggest_gospel(self, rule: str, reason: str, category: str = "dependency",
                       scope: str = "global", confidence: str = "low") -> int:
        """
        Auto-create an agent gospel. Immediately active.
        Returns gospel ID.
        """
        gospel_id = self.db.insert("gospels", {
            "rule": rule,
            "reason": reason,
            "category": category,
            "scope": scope,
            "created_by": "agent",
            "confidence": confidence,
            "status": "active",
            "last_validated": datetime.now().isoformat()
        })

        # Write to agent gospels file
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = (
            f"\n### Gospel #{gospel_id} [AGENT | {confidence.upper()}]\n"
            f"**Rule:** {rule}\n"
            f"**Reason:** {reason}\n"
            f"**Category:** {category}\n"
            f"**Scope:** {scope}\n"
            f"**Created:** {timestamp}\n"
            f"**Confidence:** {confidence}\n\n"
        )
        self.store.write("gospels/agent_gospels.md", entry, mode="append")

        log.info(f"Gospel #{gospel_id} created [AGENT|{confidence}]: {rule}")
        return gospel_id

    def update_gospel_confidence(self, gospel_id: int, confirmed: bool):
        """
        Update gospel confidence based on alert feedback.
        confirmed=True: confidence goes up. confirmed=False: confidence goes down.
        """
        gospel = self.db.fetchone("SELECT * FROM gospels WHERE id = ?", (gospel_id,))
        if not gospel or gospel["created_by"] == "human":
            return  # Never modify human gospels

        confidence_ladder = ["low", "medium", "high"]
        current = gospel["confidence"]
        current_idx = confidence_ladder.index(current) if current in confidence_ladder else 0

        if confirmed:
            new_idx = min(current_idx + 1, 2)
            self.db.update("gospels", {
                "confidence": confidence_ladder[new_idx],
                "confirmed_alerts": gospel["confirmed_alerts"] + 1,
                "last_validated": datetime.now().isoformat()
            }, "id = ?", (gospel_id,))
        else:
            new_idx = max(current_idx - 1, 0)
            false_count = gospel["false_alerts"] + 1
            self.db.update("gospels", {
                "confidence": confidence_ladder[new_idx],
                "false_alerts": false_count
            }, "id = ?", (gospel_id,))

            # Auto-retire if too many false alerts
            if false_count >= 3 and gospel["confirmed_alerts"] == 0:
                self.db.update("gospels", {"status": "retired"}, "id = ?", (gospel_id,))
                log.info(f"Gospel #{gospel_id} auto-retired (3+ false alerts, 0 confirmed)")

    def detect_dependency_gospel(self, files_changed: list[str]):
        """
        Auto-detect file dependencies and create gospels.
        If files A and B always change together, suggest a gospel.
        Only tracks actual files (with extensions), not directories.
        """
        # Filter to actual files only (must have an extension)
        actual_files = [f for f in files_changed if "." in f.split("/")[-1].split("\\")[-1]]

        if len(actual_files) < 2:
            return

        # Limit to 5 files max to prevent combinatorial explosion
        actual_files = actual_files[:5]

        for i, file_a in enumerate(actual_files):
            name_a = file_a.split("/")[-1].split("\\")[-1]
            for file_b in actual_files[i+1:]:
                name_b = file_b.split("/")[-1].split("\\")[-1]

                # Skip if same filename
                if name_a == name_b:
                    continue

                # Check if gospel already exists for this pair
                existing = self.db.fetchone(
                    "SELECT id FROM gospels WHERE rule LIKE ? AND rule LIKE ? AND status = 'active'",
                    (f"%{name_a}%", f"%{name_b}%")
                )
                if existing:
                    continue  # Already have a gospel for this pair

                # Count co-occurrences
                count = self.db.fetchone(
                    "SELECT COUNT(*) as cnt FROM changes "
                    "WHERE files_changed LIKE ? AND files_changed LIKE ?",
                    (f"%{name_a}%", f"%{name_b}%")
                )

                if count and count["cnt"] >= 5:
                    self.suggest_gospel(
                        rule=f"'{name_a}' and '{name_b}' typically change together",
                        reason=f"Observed {count['cnt']} co-occurrences in change history",
                        category="dependency",
                        scope="module",
                        confidence="medium" if count["cnt"] >= 8 else "low"
                    )

    # ── Auto-Checkpoint ──────────────────────────────────

    def should_checkpoint(self) -> bool:
        """Check if it's time for an auto-checkpoint."""
        strictness = self.config.get("agent.strictness", "normal")
        hours = {"strict": 12, "normal": 24, "loose": 999}.get(strictness, 24)

        last = self.db.fetchone(
            "SELECT MAX(timestamp) as last_time FROM alerts WHERE type = 'checkpoint'"
        )

        if not last or not last["last_time"]:
            return True  # Never checkpointed

        try:
            last_time = datetime.fromisoformat(last["last_time"])
            return datetime.now() - last_time > timedelta(hours=hours)
        except Exception:
            return True

    # ── Cost Tracking ────────────────────────────────────

    def track_cost(self, model: str, input_tokens: int = 0, output_tokens: int = 0):
        """Track LLM API call costs. Stored in DB for monthly budgeting."""
        # Costs per model (per 1M tokens) — updated March 2026
        costs = {
            # Google
            "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
            "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
            "gemini-3.1-pro": {"input": 3.00, "output": 15.00},
            # Anthropic
            "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
            "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
            "claude-opus-4-6": {"input": 5.00, "output": 25.00},
            # OpenAI
            "gpt-5-mini": {"input": 0.15, "output": 0.60},
            "gpt-5.3-codex": {"input": 3.00, "output": 15.00},
            "gpt-5.4": {"input": 10.00, "output": 40.00},
        }

        model_costs = costs.get(model, {"input": 1.0, "output": 5.0})
        cost = (input_tokens * model_costs["input"] / 1_000_000 +
                output_tokens * model_costs["output"] / 1_000_000)

        # We don't have a dedicated cost table, so use a simple approach:
        # Store in config data and persist
        current_month = datetime.now().strftime("%Y-%m")
        cost_key = f"cost.tracking.{current_month}"
        current_total = self.config.get(cost_key, 0.0)
        self.config.set(cost_key, current_total + cost)
        self.config.save()  # Persist cost data

        # Check budget
        budget = self.config.get("cost.monthly_budget_cap", 50.0)
        if current_total + cost > budget * 0.8:
            log.warning(f"Cost warning: ${current_total + cost:.2f} of ${budget:.2f} budget used this month")

        return cost

    # ── Strictness Behavior ──────────────────────────────

    def get_alert_threshold(self) -> dict:
        """Get alerting thresholds based on current strictness mode."""
        mode = self.config.get("agent.strictness", "normal")

        thresholds = {
            "strict": {
                "drift_consecutive": 1,
                "alert_on_debt": True,
                "alert_on_dependency_risk": True,
                "alert_on_minor_drift": True,
                "checkpoint_hours": 12,
                "log_everything": True
            },
            "normal": {
                "drift_consecutive": 3,
                "alert_on_debt": True,
                "alert_on_dependency_risk": True,
                "alert_on_minor_drift": False,
                "checkpoint_hours": 24,
                "log_everything": False
            },
            "loose": {
                "drift_consecutive": 999,
                "alert_on_debt": False,
                "alert_on_dependency_risk": False,
                "alert_on_minor_drift": False,
                "checkpoint_hours": 999,
                "log_everything": False
            }
        }

        return thresholds.get(mode, thresholds["normal"])

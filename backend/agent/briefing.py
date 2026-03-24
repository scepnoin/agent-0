"""
Agent-0 Briefing System
Generates welcome-back briefs for new agent sessions.
Tracks connections and delivers pending pings.

Pings use an in-memory thread-safe queue instead of SQLite,
because SQLite thread-local connections prevent cross-thread visibility.
"""

import threading
from datetime import datetime, timedelta
from logger import get_logger

log = get_logger("briefing")

# Gap threshold — if no query for this long, treat as new session
NEW_SESSION_GAP_MINUTES = 30


class BriefingSystem:
    """Manages welcome-back briefs and pending pings."""

    def __init__(self, db, store, config):
        self.db = db
        self.store = store
        self.config = config
        # In-memory ping queue — thread-safe, shared between watcher and Flask threads
        self._ping_queue = []
        self._ping_lock = threading.Lock()

    def on_query(self, question: str) -> str | None:
        """Called on every query. Returns a brief to prepend if this is a new session.
        Also returns any pending pings. Returns None if nothing to prepend."""

        now = datetime.now()
        prepend = ""

        # Check if this is a new session
        conn = self.db.fetchone(
            "SELECT * FROM connections ORDER BY last_query_at DESC LIMIT 1"
        )

        is_new_session = False
        if not conn:
            is_new_session = True
            self.db.insert("connections", {"queries_count": 1, "brief_delivered": 1})
        else:
            try:
                last_query = datetime.fromisoformat(conn["last_query_at"])
                gap = now - last_query
                if gap > timedelta(minutes=NEW_SESSION_GAP_MINUTES):
                    is_new_session = True
                    # Reset brief_delivered for this connection
                    self.db.update("connections", {
                        "last_query_at": now.isoformat(),
                        "queries_count": conn["queries_count"] + 1,
                        "brief_delivered": 1
                    }, "id = ?", (conn["id"],))
                else:
                    # Same session — update timestamp, DON'T deliver brief again
                    self.db.update("connections", {
                        "last_query_at": now.isoformat(),
                        "queries_count": conn["queries_count"] + 1
                    }, "id = ?", (conn["id"],))
            except Exception:
                is_new_session = True

        # Only deliver brief if it hasn't been delivered this session
        if conn and conn.get("brief_delivered", 0) == 1:
            is_new_session = False

        # Generate welcome brief for new sessions
        if is_new_session:
            brief = self._generate_brief()
            if brief:
                prepend += brief + "\n\n---\n\n"
                log.info("Welcome-back brief delivered")

        # Check stale docs on every query (not just new sessions)
        if not is_new_session:
            stale = self._check_stale_docs()
            if stale:
                # Only ping once per hour about stale docs (check in-memory queue)
                should_ping = True
                with self._ping_lock:
                    for p in self._ping_queue:
                        if p["type"] == "stale_docs":
                            try:
                                ping_time = datetime.fromisoformat(p["created"])
                                if datetime.now() - ping_time < timedelta(hours=1):
                                    should_ping = False
                                    break
                            except Exception:
                                pass

                if should_ping:
                    self.add_ping(stale, "stale_docs")

        # ALWAYS deliver pending pings on every query
        pings = self._get_pending_pings()
        if pings:
            prepend += pings + "\n\n---\n\n"
            log.info(f"Delivered pending pings")

        return prepend if prepend else None

    def _generate_brief(self) -> str:
        """Generate a welcome-back brief."""
        parts = ["**Agent-0 Welcome Brief**\n"]

        # Current phase
        phase = self.db.fetchone(
            "SELECT name, goal FROM phases WHERE status = 'in_progress' ORDER BY id DESC LIMIT 1"
        )
        if phase:
            parts.append(f"**Phase:** {phase['name']}")
            if phase['goal']:
                parts.append(f"**Goal:** {phase['goal'][:150]}")

        # Recent changes since last session
        changes = self.db.fetchall(
            "SELECT timestamp, category, diff_summary, files_changed FROM changes "
            "ORDER BY id DESC LIMIT 10"
        )
        if changes:
            parts.append(f"\n**Recent changes ({len(changes)}):**")
            for c in changes[:5]:
                cat = c.get("category", "?")
                summary = (c.get("diff_summary") or c.get("files_changed") or "")[:100]
                parts.append(f"- [{cat}] {summary}")

        # Active gospels count
        gospel_count = self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM gospels WHERE status = 'active'"
        )
        if gospel_count:
            parts.append(f"\n**Active gospels:** {gospel_count['cnt']}")

        # Top 3 gospels as reminders
        top_gospels = self.db.fetchall(
            "SELECT rule FROM gospels WHERE status = 'active' AND confidence = 'high' LIMIT 3"
        )
        if top_gospels:
            parts.append("**Key rules to remember:**")
            for g in top_gospels:
                rule = (g["rule"] or "")[:120]
                parts.append(f"- {rule}")

        # Previous session intent
        prev_session = self.db.fetchone(
            "SELECT intent, actual_outcome, drift_score FROM sessions ORDER BY id DESC LIMIT 1"
        )
        if prev_session and prev_session.get("intent"):
            parts.append(f"\n**Last session intent:** {prev_session['intent'][:150]}")
            if prev_session.get("drift_score") is not None:
                parts.append(f"**Drift score:** {prev_session['drift_score']:.0%}")

        parts.append("\n*Set your intent for this session: POST /session/intent {\"intent\": \"what you're working on\"}*")

        # Open alerts
        alerts = self.db.fetchall(
            "SELECT message, type, severity FROM alerts WHERE dismissed = 0 ORDER BY id DESC LIMIT 3"
        )
        if alerts:
            parts.append(f"\n**Alerts ({len(alerts)}):**")
            for a in alerts:
                parts.append(f"- [{a['severity']}] {a['message'][:100]}")

        # Stale doc warnings
        stale = self._check_stale_docs()
        if stale:
            parts.append(f"\n**Stale docs:** {stale}")

        return "\n".join(parts)

    def _get_pending_pings(self) -> str | None:
        """Get and clear pending pings from the in-memory queue.
        This avoids the SQLite thread-local connection visibility problem."""
        with self._ping_lock:
            if not self._ping_queue:
                return None
            pings = list(self._ping_queue)
            self._ping_queue.clear()

        lines = ["**Agent-0 reminders:**"]
        for p in pings:
            lines.append(f"- {p['message']}")

        # Also mark DB copies as delivered (best-effort, for logging)
        try:
            self.db.execute(
                "UPDATE pending_pings SET delivered = 1 WHERE delivered = 0"
            )
            self.db.conn.commit()
        except Exception:
            pass

        return "\n".join(lines)

    def _check_stale_docs(self) -> str | None:
        """Check if key docs are stale relative to code changes."""
        key_docs = ["ACTIVE_WORK.md", "KNOWN_ISSUES.md", "COMPLETED_WORK.md"]
        stale_docs = []

        # Get latest code change time
        latest_change = self.db.fetchone(
            "SELECT MAX(timestamp) as ts FROM changes WHERE category != 'query'"
        )
        if not latest_change or not latest_change["ts"]:
            return None

        for doc_name in key_docs:
            # Check multiple locations
            import os
            from pathlib import Path
            project = Path(self.config.get("project_path"))
            for loc in [project / doc_name, project / "Documentation" / doc_name]:
                if loc.exists():
                    try:
                        mtime = datetime.fromtimestamp(loc.stat().st_mtime)
                        change_time = datetime.fromisoformat(latest_change["ts"])
                        if change_time > mtime + timedelta(hours=2):
                            stale_docs.append(doc_name)
                    except Exception:
                        pass
                    break

        if stale_docs:
            return f"{', '.join(stale_docs)} haven't been updated recently. Consider updating them."
        return None

    def add_ping(self, message: str, ping_type: str = "reminder"):
        """Queue a ping for delivery on next agent query.
        Uses in-memory queue (thread-safe) as primary delivery mechanism.
        Also writes to DB as a log/backup."""
        with self._ping_lock:
            self._ping_queue.append({
                "message": message,
                "type": ping_type,
                "created": datetime.now().isoformat()
            })

        # Also persist to DB as a log (best-effort, not used for delivery)
        try:
            self.db.insert("pending_pings", {
                "message": message,
                "type": ping_type
            })
        except Exception:
            pass  # DB write failure is OK — in-memory queue is the primary

        log.info(f"Ping queued (in-memory): {message[:80]}")

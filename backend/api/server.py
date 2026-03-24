"""
Agent-0 Flask API Server
REST API for external tools and the Tauri widget to query Agent-0.
"""

from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


def create_app(config, react_loop=None, db=None, llm_client=None, briefing=None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)  # Allow Tauri widget and external tools to connect

    # Store config and components on app for route access
    app.config["AGENT0_CONFIG"] = config
    app.config["REACT_LOOP"] = react_loop
    app.config["DB"] = db
    app.config["LLM_CLIENT"] = llm_client
    app.config["BRIEFING"] = briefing

    @app.errorhandler(Exception)
    def handle_error(e):
        import traceback
        tb = traceback.format_exc()
        print(f"  [API ERROR] {tb}")
        return jsonify({"error": str(e), "traceback": tb}), 500

    # ── Widget HTML ─────────────────────────────────────────
    @app.route("/widget", methods=["GET"])
    def widget():
        html_path = Path(__file__).parent.parent / "ui" / "app.html"
        return send_file(str(html_path))

    # ── Health ──────────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "running",
            "project": config.get("project_name"),
            "project_path": config.get("project_path"),
            "knowledge_dir": str(config.knowledge_dir),
            "provider": config.get("llm.provider"),
            "model": config.get("llm.model"),
            "strictness": config.get("agent.strictness")
        })

    # ── State ──────────────────────────────────────────────
    @app.route("/state", methods=["GET"])
    def state():
        state_file = config.knowledge_dir / "state" / "current.md"
        if state_file.exists():
            content = state_file.read_text()
            return jsonify({"state": content})
        return jsonify({"state": "No state file found."})

    # ── Query ──────────────────────────────────────────────
    @app.route("/query", methods=["POST"])
    def query():
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Missing 'question' field"}), 400

        question = data["question"]
        loop = app.config.get("REACT_LOOP")

        if loop:
            try:
                # Check for welcome-back brief
                brief_system = app.config.get("BRIEFING")
                brief_prepend = ""
                if brief_system:
                    try:
                        result = brief_system.on_query(question)
                        if result:
                            brief_prepend = result
                    except Exception:
                        pass

                trigger = f"User query: {question}\n\nSearch your knowledge and give a concise, contextual answer."
                answer = loop.run(trigger)

                # Prepend brief if this is a new session
                if brief_prepend:
                    answer = brief_prepend + answer

                # Log query to sessions table (not changes — changes is for file changes only)
                db_inst = app.config.get("DB")
                if db_inst:
                    try:
                        db_inst.execute(
                            "CREATE TABLE IF NOT EXISTS queries (id INTEGER PRIMARY KEY, timestamp TEXT DEFAULT (datetime('now')), question TEXT, answer TEXT)"
                        )
                        db_inst.execute(
                            "INSERT INTO queries (question, answer) VALUES (?, ?)",
                            (question, answer[:500])
                        )
                        db_inst.conn.commit()
                    except Exception:
                        pass

                return jsonify({
                    "question": question,
                    "answer": answer,
                    "sources": []
                })
            except Exception as e:
                return jsonify({
                    "question": question,
                    "answer": f"Error processing query: {str(e)}",
                    "sources": []
                }), 500
        else:
            return jsonify({
                "question": question,
                "answer": "[Agent-0] ReACT loop not initialized.",
                "sources": []
            })

    # ── Brief ──────────────────────────────────────────────
    @app.route("/brief", methods=["GET"])
    def brief():
        brief_system = app.config.get("BRIEFING")
        if brief_system:
            brief_text = brief_system._generate_brief()
            return jsonify({"brief": brief_text, "project": config.get("project_name")})
        return jsonify({"brief": "Briefing system not initialized.", "project": config.get("project_name")})

    # ── Gospels ────────────────────────────────────────────
    @app.route("/gospels", methods=["GET"])
    def gospels():
        db = app.config.get("DB")
        if db:
            rows = db.fetchall("SELECT * FROM gospels WHERE status = 'active'")
            return jsonify({"gospels": rows})
        return jsonify({"gospels": []})

    # ── Alerts ─────────────────────────────────────────────
    @app.route("/alerts", methods=["GET"])
    def alerts():
        db = app.config.get("DB")
        if db:
            # Only show active (undismissed) alerts
            rows = db.fetchall("SELECT * FROM alerts WHERE dismissed = 0 ORDER BY id DESC LIMIT 20")
            return jsonify({"alerts": rows})
        return jsonify({"alerts": []})

    # ── Checkpoint ─────────────────────────────────────────
    @app.route("/checkpoint", methods=["GET"])
    def checkpoint():
        # TODO: Load latest checkpoint
        return jsonify({"checkpoint": None})

    # ── Activity Feed ──────────────────────────────────────
    @app.route("/feed", methods=["GET"])
    def feed():
        """Recent activity — queries, changes, onboarding, alerts."""
        import traceback as tb
        db_inst = app.config.get("DB")
        if not db_inst:
            return jsonify({"activity": [], "error": "DB not initialized"})
        items = []
        try:
            try:
                changes = db_inst.fetchall("SELECT * FROM changes ORDER BY id DESC LIMIT 10")
                for c in changes:
                    items.append({
                        "type": "change",
                        "time": c.get("timestamp") or "",
                        "detail": (c.get("diff_summary") or c.get("files_changed") or "")[:150],
                        "category": c.get("category") or ""
                    })
            except Exception:
                pass

            try:
                alerts = db_inst.fetchall("SELECT * FROM alerts ORDER BY id DESC LIMIT 5")
                for a in alerts:
                    items.append({
                        "type": "alert",
                        "time": a.get("timestamp") or "",
                        "detail": (a.get("message") or "")[:150],
                        "severity": a.get("severity") or "medium"
                    })
            except Exception:
                pass

            try:
                sessions = db_inst.fetchall("SELECT * FROM sessions ORDER BY id DESC LIMIT 5")
                for s in sessions:
                    items.append({
                        "type": "session",
                        "time": s.get("started") or s.get("date") or "",
                        "detail": (s.get("intent") or "")[:150]
                    })
            except Exception:
                pass

            try:
                onboard = db_inst.fetchall("SELECT * FROM onboarding_progress ORDER BY id")
                for o in onboard:
                    items.append({
                        "type": "onboarding",
                        "time": o.get("completed") or o.get("started") or "",
                        "detail": f"Phase '{o.get('phase', '?')}': {o.get('status', '?')}"
                    })
            except Exception:
                pass

        except Exception as e:
            print(f"  [API ERROR] /activity: {tb.format_exc()}")
            return jsonify({"activity": items, "error": str(e)})

        items.sort(key=lambda x: x.get("time") or "", reverse=True)
        return jsonify({"activity": items[:20]})

    # ── Stats ──────────────────────────────────────────────
    @app.route("/stats", methods=["GET"])
    def stats():
        db_inst = app.config.get("DB")
        if not db_inst:
            return jsonify({"changes": 0, "gospels": 0, "alerts": 0, "sessions": 0, "open_items": 0})
        try:
            changes = db_inst.fetchone("SELECT COUNT(*) as cnt FROM changes WHERE category != 'query'") or {"cnt": 0}
            gospels = db_inst.fetchone("SELECT COUNT(*) as cnt FROM gospels WHERE status = 'active'") or {"cnt": 0}
            alerts = db_inst.fetchone("SELECT COUNT(*) as cnt FROM alerts WHERE dismissed = 0") or {"cnt": 0}
            sessions = db_inst.fetchone("SELECT COUNT(*) as cnt FROM sessions") or {"cnt": 0}
            open_items = db_inst.fetchone("SELECT COUNT(*) as cnt FROM open_items WHERE status = 'open'") or {"cnt": 0}
            return jsonify({
                "changes": changes["cnt"],
                "gospels": gospels["cnt"],
                "alerts": alerts["cnt"],
                "sessions": sessions["cnt"],
                "open_items": open_items["cnt"]
            })
        except Exception as e:
            return jsonify({"changes": 0, "gospels": 0, "alerts": 0, "error": str(e)})

    # ── Knowledge Files ────────────────────────────────────
    @app.route("/knowledge", methods=["GET"])
    def knowledge():
        """List all knowledge files and optionally read one."""
        file_path = request.args.get("file", None)

        if file_path:
            # Read a specific file
            full = config.knowledge_dir / file_path
            if full.exists():
                return jsonify({"file": file_path, "content": full.read_text(encoding="utf-8", errors="replace")})
            return jsonify({"error": f"File not found: {file_path}"}), 404

        # List all knowledge files
        files = []
        for f in sorted(config.knowledge_dir.rglob("*.md")):
            rel = str(f.relative_to(config.knowledge_dir)).replace("\\", "/")
            size = f.stat().st_size
            files.append({"path": rel, "size": size})
        return jsonify({"files": files})

    # ── Config ─────────────────────────────────────────────
    @app.route("/config/strictness", methods=["POST"])
    def set_strictness():
        data = request.get_json()
        if not data or "mode" not in data:
            return jsonify({"error": "Missing 'mode' field"}), 400

        mode = data["mode"]
        if mode not in ["strict", "normal", "loose"]:
            return jsonify({"error": "Mode must be: strict, normal, loose"}), 400

        config.set("agent.strictness", mode)
        config.save()
        return jsonify({"strictness": mode})

    # ── Config Save ────────────────────────────────────────
    @app.route("/config/save", methods=["POST"])
    def save_config():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if data.get("provider"):
            config.set("llm.provider", data["provider"])
        if data.get("model"):
            config.set("llm.model", data["model"])
        if data.get("api_key") and data["api_key"] not in ("", "***"):
            config.set("llm.api_key", data["api_key"])
        if data.get("embed_model"):
            config.set("embeddings.model", data["embed_model"])
        if data.get("embed_key"):
            config.set("embeddings.api_key", data["embed_key"])
        if data.get("strictness"):
            config.set("agent.strictness", data["strictness"])
        if data.get("debounce"):
            config.set("watcher.debounce_seconds", int(data["debounce"]))

        config.save()

        # Reload LLM client with new settings
        llm = app.config.get("LLM_CLIENT")
        if llm:
            config.load()  # Re-read from disk
            llm.reload_config(config)

        return jsonify({"status": "saved"})

    # ── Config Get ─────────────────────────────────────────
    @app.route("/config", methods=["GET"])
    def get_config():
        import copy
        data = copy.deepcopy(config.data)  # Deep copy so we don't mutate the original
        # Mask API keys
        if data.get("llm", {}).get("api_key"):
            data["llm"]["api_key_set"] = True
            data["llm"]["api_key"] = ""
        else:
            data.setdefault("llm", {})["api_key_set"] = False
        if data.get("embeddings", {}).get("api_key"):
            data["embeddings"]["api_key_set"] = True
            data["embeddings"]["api_key"] = ""
        else:
            data.setdefault("embeddings", {})["api_key_set"] = False
        return jsonify(data)

    # ── Code Scan ─────────────────────────────────────────
    @app.route("/scan", methods=["POST"])
    def scan():
        """Run semgrep code scan on the project. Returns findings."""
        from memory.code_scanner import run_scan, format_findings, analyze_findings
        from pathlib import Path

        project_path = Path(config.get("project_path"))
        results = run_scan(project_path)

        # Store results
        if results["total"] > 0:
            from memory.store import MarkdownStore
            store = MarkdownStore(config.knowledge_dir)
            store.write("scan_results.md", format_findings(results), mode="overwrite")

            # Generate curated audit report
            llm = app.config.get("LLM_CLIENT")
            if llm:
                try:
                    analyze_findings(results, llm, store, project_path)
                except Exception as e:
                    print(f"  [API] Audit analysis failed: {e}")

            # Store ONE summary alert — individual findings stay in scan_results.md
            db_inst = app.config.get("DB")
            if db_inst:
                high_count = results["by_severity"].get("HIGH", 0) + results["by_severity"].get("ERROR", 0) + results["by_severity"].get("CRITICAL", 0)
                if high_count > 0:
                    db_inst.insert("alerts", {
                        "message": f"Code scan complete: {results['total']} findings ({high_count} HIGH). See scan_results.md for details.",
                        "type": "code_scan_summary",
                        "severity": "high" if high_count > 10 else "medium"
                    })

        # Write scan summary to state/current.md so the LLM always sees it
        try:
            state_file = config.knowledge_dir / "state" / "current.md"
            if state_file.exists():
                state_content = state_file.read_text(encoding="utf-8", errors="replace")
            else:
                state_content = f"# Current State\n\n**Project:** {config.get('project_name')}\n"

            # Remove old scan section if present
            scan_marker = "\n## Latest Scan Results"
            if scan_marker in state_content:
                state_content = state_content[:state_content.index(scan_marker)]

            # Append fresh scan summary
            high_count = results["by_severity"].get("HIGH", 0) + results["by_severity"].get("ERROR", 0) + results["by_severity"].get("CRITICAL", 0)
            med_count = results["by_severity"].get("MEDIUM", 0) + results["by_severity"].get("WARNING", 0)
            low_count = results["by_severity"].get("LOW", 0) + results["by_severity"].get("INFO", 0)
            scan_summary = (
                f"\n## Latest Scan Results\n\n"
                f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"**Total findings:** {results['total']}\n"
                f"**HIGH:** {high_count} | **MEDIUM:** {med_count} | **LOW:** {low_count}\n"
                f"**Cross-referenced:** {results.get('cross_referenced', 0)} confirmed by multiple tools\n\n"
            )
            # Top 10 findings summary
            if results["findings"]:
                scan_summary += "**Top findings:**\n"
                for f in results["findings"][:10]:
                    scan_summary += f"- [{f['severity']}] {f['rule'].split('.')[-1]}: {f['message'][:100]} in {f['file']}:{f['line']}\n"
                scan_summary += f"\n*Full details in scan_results.md*\n"

            state_content += scan_summary
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(state_content, encoding="utf-8")
        except Exception as e:
            print(f"  [API] Failed to write scan summary to state: {e}")

        # Ping the working agent about findings
        brief_system = app.config.get("BRIEFING")
        if brief_system and results["total"] > 0:
            brief_system.add_ping(
                f"Code scan complete: {results['total']} issue(s) found. "
                f"{high_count} HIGH severity. "
                f"{results.get('cross_referenced', 0)} confirmed by multiple tools. "
                f"Check scan_results.md or query me for details.",
                "code_scan"
            )

        return jsonify({
            "total": results["total"],
            "by_severity": results["by_severity"],
            "findings": results["findings"][:20]
        })

    # ── Session Intent ─────────────────────────────────────
    @app.route("/session/intent", methods=["POST"])
    def set_intent():
        """Set what the agent/developer is working on this session."""
        data = request.get_json(force=True, silent=True) or {}
        intent = data.get("intent", "")
        if not intent:
            return jsonify({"error": "Missing 'intent' field"}), 400

        db_inst = app.config.get("DB")
        if db_inst:
            # Update the current open session
            session = db_inst.fetchone("SELECT id FROM sessions WHERE ended IS NULL ORDER BY id DESC LIMIT 1")
            if session:
                db_inst.update("sessions", {"intent": intent}, "id = ?", (session["id"],))
            else:
                db_inst.insert("sessions", {"intent": intent})

        return jsonify({"status": "intent set", "intent": intent})

    @app.route("/session/intent", methods=["GET"])
    def get_intent():
        db_inst = app.config.get("DB")
        if db_inst:
            session = db_inst.fetchone("SELECT intent FROM sessions WHERE ended IS NULL ORDER BY id DESC LIMIT 1")
            if session and session["intent"]:
                return jsonify({"intent": session["intent"]})
        return jsonify({"intent": None})

    # ── Restart with new project ─────────────────────────
    @app.route("/restart", methods=["POST"])
    def restart():
        """Restart Agent-0 with a new project path.
        The new process uses claim_port() to kill us, so we just spawn and exit."""
        import subprocess, sys, os
        data = request.get_json(force=True, silent=True) or {}
        new_path = data.get("project_path", "")

        if not new_path:
            return jsonify({"error": "Missing project_path"}), 400

        new_path = new_path.strip().replace("/", os.sep)
        if not os.path.isdir(new_path):
            return jsonify({"error": f"Path does not exist: {new_path}"}), 400

        main_py = str(Path(__file__).parent.parent / "main.py")
        port = request.host.split(":")[1] if ":" in request.host else "7800"

        import threading
        def do_restart():
            import time

            # 1. Spawn new process — it will claim_port() and kill us
            kwargs = {}
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0
                kwargs["startupinfo"] = si
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            subprocess.Popen(
                [sys.executable, main_py, "--project", new_path, "--port", port, "--no-ui"],
                **kwargs
            )

            # 2. Give the new process time to start and call claim_port()
            #    which will taskkill us. If it doesn't, exit ourselves.
            time.sleep(5)
            os._exit(0)

        threading.Thread(target=do_restart, daemon=True).start()

        return jsonify({"status": "restarting", "new_project": new_path})

    return app

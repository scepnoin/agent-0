"""
Agent-0 — Sentinel Agent
Main entry point. Starts the Flask API server, file watcher, and agent loop.
"""

import argparse
import os
import sys
import threading
import signal
from pathlib import Path

from config import Config
from logger import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Agent-0: Sentinel agent for project tracking"
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Path to the project folder to watch"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["anthropic", "openai", "google"],
        default=None,
        help="LLM provider (anthropic, openai, google)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="LLM provider API key"
    )
    parser.add_argument(
        "--embedding-key",
        type=str,
        default=None,
        help="Google API key for embeddings (defaults to --api-key if provider is google)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7800,
        help="Flask API port (default: 7800)"
    )
    parser.add_argument(
        "--onboard",
        action="store_true",
        help="Run onboarding (first-run deep scan of the project)"
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Run without the desktop widget (headless mode)"
    )
    return parser.parse_args()


def setup_config(args) -> Config:
    """Initialize or load config from project folder."""
    project_path = Path(args.project).resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    if not project_path.is_dir():
        print(f"Error: Project path is not a directory: {project_path}")
        sys.exit(1)

    config = Config(str(project_path))
    config.load()

    # Override with CLI args if provided
    if args.provider:
        config.set("llm.provider", args.provider)
    if args.api_key:
        config.set("llm.api_key", args.api_key)
    if args.embedding_key:
        config.set("embeddings.api_key", args.embedding_key)
    elif args.api_key and config.get("llm.provider") == "google":
        # If provider is Google and no separate embedding key, use the same key
        config.set("embeddings.api_key", args.api_key)

    # Ensure directories exist and save config
    config.ensure_dirs()
    config.save()

    return config


def print_banner(config: Config):
    """Print Agent-0 startup banner."""
    print("")
    print("  +======================================+")
    print("  |           AGENT-0  SENTINEL          |")
    print("  +======================================+")
    print("")
    print(f"  Project:    {config.get('project_name')}")
    print(f"  Path:       {config.get('project_path')}")
    print(f"  Knowledge:  {config.knowledge_dir}")
    print(f"  Provider:   {config.get('llm.provider', 'not set')}")
    print(f"  Model:      {config.get('llm.model', 'not set')}")
    print(f"  Embeddings: {config.get('embeddings.model', 'not set')}")
    print(f"  Strictness: {config.get('agent.strictness', 'normal')}")
    print(f"  API Key:    {'***set***' if config.get('llm.api_key') else 'NOT SET'}")
    print("")

    if not config.is_configured:
        print("  [!] API key not set. Use --api-key or edit .agent0/config.json")
        print("")


def start_api_server(config: Config, port: int, react_loop=None, db=None, llm_client=None, briefing=None):
    """Start the Flask API server in a background thread."""
    from api.server import create_app

    app = create_app(config, react_loop=react_loop, db=db, llm_client=llm_client, briefing=briefing)

    # Run Flask in a thread so it doesn't block
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True
    )
    server_thread.start()
    print(f"  [API]     Running on http://127.0.0.1:{port}")
    return server_thread


def start_watcher(config: Config, react_loop=None, db=None, store=None, reasoning=None, indexer=None, briefing=None):
    """Start the file watcher in a background thread."""
    from watcher.watcher import FileWatcher

    watcher = FileWatcher(config, react_loop=react_loop, db=db, store=store, reasoning=reasoning, indexer=indexer, briefing=briefing)
    watcher_thread = threading.Thread(
        target=watcher.start,
        daemon=True
    )
    watcher_thread.start()
    print(f"  [WATCHER] Watching {config.get('project_path')}")
    return watcher, watcher_thread


def check_onboarding(config: Config):
    """Check if onboarding needs to run (incomplete or never started)."""
    from memory.db import Database
    db = Database(config.db_path)
    try:
        pending = db.fetchall(
            "SELECT * FROM onboarding_progress WHERE status IN ('pending', 'in_progress', 'failed')"
        )
        if pending:
            phases = [p["phase"] for p in pending]
            print(f"  [ONBOARD] Incomplete phases: {', '.join(phases)}")
            return True
        total = db.fetchall("SELECT * FROM onboarding_progress")
        if not total:
            print("  [ONBOARD] No onboarding data — needs full onboarding")
            return True
        return False
    except Exception:
        return True


def claim_port(port: int):
    """Kill any existing process on our port before starting.
    Prevents multiple Agent-0 instances fighting over the same port.
    NOTE: Do NOT use /T (tree kill) — we might be a child of the old process."""
    import subprocess
    my_pid = os.getpid()
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid != my_pid and pid > 0:
                    print(f"  [PORT]    Killing existing process {pid} on port {port}")
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(pid)],
                            capture_output=True, timeout=5
                        )
                    except Exception:
                        pass
        # Brief wait for port release
        import time
        time.sleep(1)
    except Exception:
        pass


def main():
    args = parse_args()
    config = setup_config(args)

    # Claim our port — kill any stale processes
    claim_port(args.port)

    # Setup logging
    logger = setup_logger(str(config.log_path))
    logger.info(f"Agent-0 starting for project: {config.get('project_name')}")
    logger.info(f"Knowledge dir: {config.knowledge_dir}")
    logger.info(f"Log file: {config.log_path}")

    print_banner(config)

    # Check for existing marker
    marker = Config.find_marker(str(config.project_path))
    if marker:
        print(f"  [MARKER]  Found agent-0/agent0.json -- project already bonded")
    else:
        print(f"  [MARKER]  New project -- will create agent-0/ folder")

    if not config.is_configured:
        print("  [!] API key not set. Use --api-key flag or edit config.")
        print("  [!] Starting anyway — set key in Tauri widget Settings tab.")
        print("")

    # Initialize database
    from memory.db import Database
    db = Database(config.db_path)
    db.initialize()
    print("  [DB]      SQLite initialized")

    # Initialize memory system
    from memory.store import MarkdownStore
    from memory.search import HybridSearch
    from llm.client import LLMClient

    store = MarkdownStore(config.knowledge_dir)
    llm_client = LLMClient(config)

    # Initialize indexer (needs LLM for embeddings)
    from memory.indexer import Indexer
    indexer = Indexer(db, llm_client, config.knowledge_dir)

    # Initialize hybrid search
    search = HybridSearch(db, llm_client)

    # Initialize all 15 tools with their dependencies
    from tools import read_file, read_diff, list_files, get_state
    from tools import write_knowledge, db_write, db_query
    from tools import search_knowledge, search_project, git_info
    from tools import check_gospels, send_alert, log_question
    from tools import create_checkpoint, summarize_and_split
    from tools import list_knowledge

    read_file.init(config)
    read_diff.init(config)
    list_files.init(config)
    get_state.init(config, store)
    write_knowledge.init(store, indexer)
    db_write.init(db)
    db_query.init(db)
    search_knowledge.init(search, store=store, config=config, db=db)
    search_project.init(config)
    git_info.init(config)
    check_gospels.init(db)
    send_alert.init(db)
    log_question.init(store)
    create_checkpoint.init(db, store)
    summarize_and_split.init(store, indexer)
    list_knowledge.init(store)

    from tools import list_tools
    print(f"  [TOOLS]   {len(list_tools())} tools registered")

    # Skip re-indexing on startup — onboarding indexes at the end
    # Re-indexing large projects locks the DB and blocks queries
    print(f"  [INDEX]   Using existing index (re-index during onboarding only)")

    # Initialize reasoning engine
    from reasoning.reasoning import ReasoningEngine
    reasoning = ReasoningEngine(db, store, config)

    # Start a session
    session_id = reasoning.start_session("Agent-0 startup")
    print(f"  [SESSION] Session #{session_id} started")

    # Initialize briefing system
    from agent.briefing import BriefingSystem
    briefing = BriefingSystem(db, store, config)

    # Initialize ReACT loop
    from agent.loop import ReACTLoop
    react_loop = ReACTLoop(llm_client, config)

    # Start API server (wired to ReACT loop)
    api_thread = start_api_server(config, args.port, react_loop=react_loop, db=db, llm_client=llm_client, briefing=briefing)

    # Start MCP server
    from api.mcp import start_mcp_server
    mcp_server, mcp_thread = start_mcp_server(port=args.port + 1)

    # Onboarding
    needs_onboard = check_onboarding(config)

    if args.onboard or needs_onboard:
        from agent.onboarding import Onboarding
        onboarding = Onboarding(config, llm_client, db, store, indexer)
        onboarding.run()

    # Start file watcher (wired to ReACT loop + reasoning + indexer)
    watcher, watcher_thread = start_watcher(config, react_loop=react_loop, db=db, store=store, reasoning=reasoning, indexer=indexer, briefing=briefing)

    # Auto-scan if never done, or re-analyze if audit report is missing
    scan_file = config.knowledge_dir / "scan_results.md"
    audit_file = config.knowledge_dir / "audit_report.md"
    if not scan_file.exists() or scan_file.stat().st_size < 100 or not audit_file.exists():
        print("  [SCAN]    No scan results found — running initial code scan...")
        def run_initial_scan():
            try:
                from memory.code_scanner import run_scan, format_findings, analyze_findings
                from datetime import datetime
                results = run_scan(Path(config.get("project_path")))
                if results["total"] > 0:
                    store.write("scan_results.md", format_findings(results), mode="overwrite")
                    high_count = results["by_severity"].get("HIGH", 0) + results["by_severity"].get("ERROR", 0) + results["by_severity"].get("CRITICAL", 0)
                    med_count = results["by_severity"].get("MEDIUM", 0) + results["by_severity"].get("WARNING", 0)
                    low_count = results["by_severity"].get("LOW", 0) + results["by_severity"].get("INFO", 0)

                    # Write to state/current.md
                    scan_summary = (
                        f"\n## Latest Scan Results\n\n"
                        f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                        f"**Total findings:** {results['total']}\n"
                        f"**HIGH:** {high_count} | **MEDIUM:** {med_count} | **LOW:** {low_count}\n"
                    )
                    if results["findings"]:
                        scan_summary += "\n**Top findings:**\n"
                        for f in results["findings"][:10]:
                            scan_summary += f"- [{f['severity']}] {f['rule'].split('.')[-1]}: {f['message'][:100]} in {f['file']}:{f['line']}\n"

                    state_path = config.knowledge_dir / "state" / "current.md"
                    if state_path.exists():
                        content = state_path.read_text(encoding="utf-8", errors="replace")
                        if "## Latest Scan Results" in content:
                            content = content[:content.index("\n## Latest Scan Results")]
                        content += scan_summary
                        state_path.write_text(content, encoding="utf-8")

                    # One summary alert
                    if high_count > 0:
                        db.insert("alerts", {
                            "message": f"Initial scan: {results['total']} findings ({high_count} HIGH). See scan_results.md.",
                            "type": "code_scan_summary",
                            "severity": "high" if high_count > 10 else "medium"
                        })

                    briefing.add_ping(
                        f"Initial code scan complete: {results['total']} findings "
                        f"({high_count} HIGH, {med_count} MEDIUM, {low_count} LOW).",
                        "auto_scan"
                    )
                    # Generate curated audit report
                    try:
                        analyze_findings(results, llm_client, store, Path(config.get("project_path")))
                        print(f"  [SCAN]    Audit report generated")
                    except Exception as e:
                        print(f"  [SCAN]    Audit analysis failed: {e}")

                    print(f"  [SCAN]    Complete: {results['total']} findings ({high_count} HIGH)")
                else:
                    store.write("scan_results.md", "# Code Scan Results\n\nNo issues found.\n", mode="overwrite")
                    print("  [SCAN]    Complete: no issues found")
            except Exception as e:
                print(f"  [SCAN]    Failed: {e}")

        scan_thread = threading.Thread(target=run_initial_scan, daemon=True)
        scan_thread.start()

    print("")
    print("  Agent-0 is running. Press Ctrl+C to stop.")
    print("  -----------------------------------------")
    print("")

    # UI is handled by Tauri desktop app (separate process)
    # Backend runs headless, Tauri connects via http://127.0.0.1:{port}/widget

    # Handle graceful shutdown
    def shutdown(sig, frame):
        print("\n  Shutting down Agent-0...")
        watcher.stop()
        print("  Agent-0 stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep main thread alive
    try:
        while True:
            signal.pause()
    except AttributeError:
        # signal.pause() not available on Windows — use a loop
        import time
        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()

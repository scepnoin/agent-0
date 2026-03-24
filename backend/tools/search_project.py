"""Tool: search_project — Search the actual project codebase (grep-like)."""

import subprocess
from pathlib import Path
from tools import register_tool

_config = None

def init(config):
    global _config
    _config = config


@register_tool(
    name="search_project",
    description="Search the project codebase for text/patterns. Like grep - find where functions are used, where imports come from, where strings appear. Searches project files, NOT Agent-0 knowledge files.",
    schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text or regex pattern to search for"},
            "file_pattern": {"type": "string", "description": "Optional: glob filter (e.g. '*.py', 'core/**/*.py')"},
            "max_results": {"type": "integer", "description": "Max matches to return (default 20)"}
        },
        "required": ["query"]
    }
)
def search_project(query: str, file_pattern: str = None, max_results: int = 20) -> str:
    project_path = Path(_config.get("project_path"))
    ignore_patterns = _config.get("watcher.ignore_patterns", [])

    results = []
    search_path = project_path

    try:
        # Use git grep if available (faster, respects .gitignore)
        cmd = ["git", "grep", "-n", "--max-count", str(max_results), query]
        if file_pattern:
            cmd.append(f"-- '{file_pattern}'")

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(project_path), timeout=15
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()[:max_results]
            output = f"Found {len(lines)} match(es) for '{query}':\n\n"
            for line in lines:
                output += f"  {line}\n"
            return output

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: manual search
    try:
        for f in project_path.rglob(file_pattern or "*"):
            if f.is_dir():
                continue
            if any(p in str(f) for p in ["agent-0", ".git", "__pycache__", "node_modules", "venv"]):
                continue
            if f.suffix in [".pyc", ".exe", ".dll", ".so", ".db", ".sqlite"]:
                continue

            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.splitlines(), 1):
                    if query.lower() in line.lower():
                        rel = str(f.relative_to(project_path))
                        results.append(f"  {rel}:{i}: {line.strip()}")
                        if len(results) >= max_results:
                            break
            except Exception:
                continue

            if len(results) >= max_results:
                break

    except Exception as e:
        return f"Search error: {e}"

    if not results:
        return f"No matches found for '{query}'" + (f" in {file_pattern}" if file_pattern else "")

    output = f"Found {len(results)} match(es) for '{query}':\n\n"
    output += "\n".join(results)
    return output

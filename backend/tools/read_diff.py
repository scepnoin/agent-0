"""Tool: read_diff — Read what changed in a file. Uses git if available, otherwise file snapshots."""

import subprocess
from pathlib import Path
from tools import register_tool

_config = None

def init(config):
    global _config
    _config = config


@register_tool(
    name="read_diff",
    description="Read the diff/changes for a file. Shows what was added, removed, or changed.",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to project root"}
        },
        "required": ["path"]
    }
)
def read_diff(path: str) -> str:
    project_path = Path(_config.get("project_path"))
    full_path = project_path / path

    if not full_path.exists():
        return f"File not found (may have been deleted): {path}"

    # Try git diff first
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", str(full_path)],
            capture_output=True, text=True, cwd=str(project_path), timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            diff = result.stdout.strip()
            lines = diff.splitlines()
            if len(lines) > 200:
                return "\n".join(lines[:200]) + f"\n\n... (truncated, {len(lines)} lines)"
            return diff
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # No git — read the current file content instead
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        if len(lines) > 100:
            preview = "\n".join(lines[:100])
            return f"Current content of {path} ({len(lines)} lines, showing first 100):\n\n{preview}\n\n..."
        return f"Current content of {path} ({len(lines)} lines):\n\n{content}"
    except Exception as e:
        return f"Error reading {path}: {e}"

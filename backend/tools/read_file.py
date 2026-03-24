"""Tool: read_file — Read a file from the project or Agent-0's knowledge."""

from pathlib import Path
from tools import register_tool

# Will be set by main.py at startup
_config = None

def init(config):
    global _config
    _config = config


@register_tool(
    name="read_file",
    description="Read the contents of a file. Use for project files or Agent-0 knowledge files.",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to project root"},
            "line_start": {"type": "integer", "description": "Optional: start reading from this line"},
            "line_end": {"type": "integer", "description": "Optional: stop reading at this line"}
        },
        "required": ["path"]
    }
)
def read_file(path: str, line_start: int = None, line_end: int = None) -> str:
    project_path = Path(_config.get("project_path"))
    full_path = project_path / path

    if not full_path.exists():
        return f"File not found: {path}"

    if full_path.is_dir():
        return f"Path is a directory, not a file: {path}"

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading {path}: {e}"

    lines = content.splitlines()

    if line_start is not None or line_end is not None:
        start = (line_start or 1) - 1
        end = line_end or len(lines)
        # Include a few extra lines for context
        if start == end - 1:
            start = max(0, start - 3)
            end = min(len(lines), end + 3)
        selected = lines[start:end]
        # Show with line numbers so blank lines are visible
        numbered = [f"{start + i + 1:5}: {line}" for i, line in enumerate(selected)]
        return "\n".join(numbered)

    # Truncate very large files
    if len(lines) > 500:
        return "\n".join(lines[:500]) + f"\n\n... (truncated, {len(lines)} total lines)"

    return "\n".join(lines)

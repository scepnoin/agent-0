"""Tool: list_files — List files and folders in a directory."""

from pathlib import Path
from fnmatch import fnmatch
from tools import register_tool

_config = None

def init(config):
    global _config
    _config = config


@register_tool(
    name="list_files",
    description="List files and folders in a SINGLE directory (not recursive). For project-wide stats like total file counts, use search_knowledge to check code_structure.md instead.",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path relative to project root"},
            "pattern": {"type": "string", "description": "Optional glob pattern to filter (e.g. '*.py')"}
        },
        "required": ["path"]
    }
)
def list_files(path: str, pattern: str = None) -> str:
    project_path = Path(_config.get("project_path"))
    full_path = project_path / path

    if not full_path.exists():
        return f"Directory not found: {path}"

    if not full_path.is_dir():
        return f"Not a directory: {path}"

    entries = []
    try:
        for item in sorted(full_path.iterdir()):
            name = item.name
            if pattern and not fnmatch(name, pattern):
                continue

            if item.is_dir():
                entries.append(f"  [dir]  {name}/")
            else:
                size = item.stat().st_size
                entries.append(f"  [file] {name} ({size:,} bytes)")

        if not entries:
            return f"Directory is empty: {path}" + (f" (filter: {pattern})" if pattern else "")

        # Truncate if too many
        if len(entries) > 100:
            return "\n".join(entries[:100]) + f"\n\n... ({len(entries)} total entries, showing first 100)"

        return f"Contents of {path}:\n" + "\n".join(entries)

    except PermissionError:
        return f"Permission denied: {path}"

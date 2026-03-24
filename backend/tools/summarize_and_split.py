"""Tool: summarize_and_split — Split large markdown files."""

from datetime import datetime
from tools import register_tool

_store = None
_indexer = None

def init(store, indexer):
    global _store, _indexer
    _store = store
    _indexer = indexer


@register_tool(
    name="summarize_and_split",
    description="When a markdown file gets too large: summarize the older content, archive it to a new file, and start fresh with a reference to the archive.",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the markdown file that's too large"},
            "max_lines": {"type": "integer", "description": "Threshold - split when file exceeds this (default 200)"}
        },
        "required": ["path"]
    }
)
def summarize_and_split(path: str, max_lines: int = 200) -> str:
    if not _store.needs_split(path, max_lines):
        return f"File {path} is under {max_lines} lines. No split needed."

    content = _store.read(path)
    lines = content.splitlines()

    # Split: keep last 50 lines in current file, archive the rest
    keep_lines = 50
    archive_content = "\n".join(lines[:-keep_lines])
    current_content = "\n".join(lines[-keep_lines:])

    # Create archive file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = path.rsplit(".", 1)[0]
    archive_path = f"{base}_archive_{timestamp}.md"

    archive_header = f"# Archive of {path}\n"
    archive_header += f"**Archived:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    archive_header += f"**Lines archived:** {len(lines) - keep_lines}\n\n"

    _store.write(archive_path, archive_header + archive_content, mode="create")

    # Update current file with reference to archive
    reference = f"<!-- Archived content moved to {archive_path} -->\n\n"
    _store.write(path, reference + current_content, mode="overwrite")

    # Re-index both files
    if _indexer:
        try:
            _indexer.reindex_if_changed(path)
            _indexer.reindex_if_changed(archive_path)
        except Exception:
            pass

    return f"Split {path}: archived {len(lines) - keep_lines} lines to {archive_path}, kept last {keep_lines} lines."

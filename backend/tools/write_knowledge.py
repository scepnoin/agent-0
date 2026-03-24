"""Tool: write_knowledge — Write to Agent-0's knowledge files."""

from tools import register_tool

_store = None
_indexer = None

def init(store, indexer):
    global _store, _indexer
    _store = store
    _indexer = indexer


@register_tool(
    name="write_knowledge",
    description="Write to Agent-0's knowledge files. Can create new files, append to existing, or overwrite. Auto-triggers re-indexing.",
    schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to .agent0/ (e.g. 'sessions/2026-03-14.md')"},
            "content": {"type": "string", "description": "Content to write"},
            "mode": {"type": "string", "enum": ["create", "append", "overwrite"], "description": "Write mode"}
        },
        "required": ["path", "content", "mode"]
    }
)
def write_knowledge(path: str, content: str, mode: str) -> str:
    result = _store.write(path, content, mode)

    # Re-index the file after writing
    if _indexer and path.endswith(".md"):
        try:
            _indexer.reindex_if_changed(path)
        except Exception:
            pass  # Don't fail the write if indexing fails

    return result

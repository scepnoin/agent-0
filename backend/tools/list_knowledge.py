"""Tool: list_knowledge — List all Agent-0 knowledge files so the LLM knows what's available."""

from tools import register_tool

_store = None

def init(store):
    global _store
    _store = store


@register_tool(
    name="list_knowledge",
    description="List all of Agent-0's knowledge files with their sizes. Use this to see what knowledge is available before searching.",
    schema={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def list_knowledge() -> str:
    files = _store.list_files()
    if not files:
        return "No knowledge files found."
    result = f"Agent-0 has {len(files)} knowledge file(s):\n\n"
    for f in sorted(files):
        result += f"  - {f}\n"
    return result

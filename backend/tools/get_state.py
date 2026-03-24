"""Tool: get_state — Get the current project state."""

from tools import register_tool

_config = None
_store = None

def init(config, store):
    global _config, _store
    _config = config
    _store = store


@register_tool(
    name="get_state",
    description="Get the current project state including phase, goal, last change, and session info. Reads state/current.md.",
    schema={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_state() -> str:
    return _store.read("state/current.md")

"""
Agent-0 Tool Registry
Tools are registered here and exposed to the ReACT loop.
"""

# Tool registry — maps tool names to their functions and schemas
_TOOLS = {}


def register_tool(name: str, description: str, schema: dict):
    """Decorator to register a tool function."""
    def decorator(func):
        _TOOLS[name] = {
            "name": name,
            "description": description,
            "function": func,
            "input_schema": schema
        }
        return func
    return decorator


def get_tool_schemas() -> list:
    """Return all tool schemas in the format expected by the LLM API."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"]
        }
        for t in _TOOLS.values()
    ]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a registered tool by name with given arguments."""
    if name not in _TOOLS:
        return f"Error: Unknown tool '{name}'"
    try:
        result = _TOOLS[name]["function"](**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing {name}: {str(e)}"


def list_tools() -> list:
    """Return list of registered tool names."""
    return list(_TOOLS.keys())

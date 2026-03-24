"""Tool: db_write — Insert or update records in Agent-0's SQLite database."""

from tools import register_tool

_db = None

def init(db):
    global _db
    _db = db


@register_tool(
    name="db_write",
    description="Insert or update a record in Agent-0's SQLite database.",
    schema={
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Table name (changes, phases, gospels, open_items, sessions, alerts)"},
            "data": {"type": "object", "description": "Key-value pairs to insert/update"},
            "operation": {"type": "string", "enum": ["insert", "update"], "description": "Insert new or update existing"}
        },
        "required": ["table", "data", "operation"]
    }
)
def db_write(table: str, data: dict, operation: str) -> str:
    valid_tables = ["changes", "phases", "gospels", "open_items", "sessions", "alerts"]
    if table not in valid_tables:
        return f"Invalid table: {table}. Must be one of: {valid_tables}"

    try:
        if operation == "insert":
            row_id = _db.insert(table, data)
            return f"Inserted into {table}, row ID: {row_id}"
        elif operation == "update":
            if "id" not in data:
                return "Update requires 'id' field in data"
            row_id = data.pop("id")
            _db.update(table, data, "id = ?", (row_id,))
            return f"Updated {table} row {row_id}"
        else:
            return f"Unknown operation: {operation}"
    except Exception as e:
        return f"Database error: {e}"

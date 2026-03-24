"""Tool: db_query — Query Agent-0's SQLite database."""

from tools import register_tool

_db = None

def init(db):
    global _db
    _db = db


@register_tool(
    name="db_query",
    description="Query Agent-0's SQLite database. Returns matching records.",
    schema={
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Table name"},
            "filter": {"type": "object", "description": "Key-value filter conditions"},
            "limit": {"type": "integer", "description": "Max records to return (default 20)"}
        },
        "required": ["table"]
    }
)
def db_query(table: str, filter: dict = None, limit: int = 50) -> str:
    valid_tables = ["changes", "phases", "gospels", "open_items", "sessions", "alerts"]
    if table not in valid_tables:
        return f"Invalid table: {table}. Must be one of: {valid_tables}"

    try:
        where_clauses = []
        params = []

        if filter:
            for key, value in filter.items():
                where_clauses.append(f"{key} = ?")
                params.append(value)

        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        params.append(limit)

        rows = _db.fetchall(
            f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT ?",
            tuple(params)
        )

        if not rows:
            return f"No records found in {table}" + (f" with filter {filter}" if filter else "")

        # Get total count
        total = _db.fetchone(f"SELECT COUNT(*) as cnt FROM {table}")
        total_count = total["cnt"] if total else len(rows)

        result = f"Found {len(rows)} of {total_count} total record(s) in {table}:\n\n"
        for row in rows:
            result += "  " + " | ".join(f"{k}: {v}" for k, v in row.items()) + "\n"

        return result

    except Exception as e:
        return f"Query error: {e}"

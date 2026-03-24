"""Tool: check_gospels — Validate a change against all active gospel rules."""

from tools import register_tool

_db = None

def init(db):
    global _db
    _db = db


@register_tool(
    name="check_gospels",
    description="Check a change or action against ALL active gospel rules. Returns any violations or warnings.",
    schema={
        "type": "object",
        "properties": {
            "change_description": {"type": "string", "description": "Description of what changed or is about to happen"},
            "files_affected": {"type": "string", "description": "Which files were changed"}
        },
        "required": ["change_description"]
    }
)
def check_gospels(change_description: str, files_affected: str = "") -> str:
    # Load all active gospels
    gospels = _db.fetchall(
        "SELECT * FROM gospels WHERE status = 'active' ORDER BY created_by DESC, id"
    )

    if not gospels:
        return "No active gospels. No rules to check against."

    output = f"Checking against {len(gospels)} active gospel(s):\n\n"
    output += f"Change: {change_description}\n"
    output += f"Files: {files_affected}\n\n"

    output += "Active gospels:\n"
    for g in gospels:
        authority = "[HUMAN]" if g["created_by"] == "human" else f"[AGENT|{g['confidence']}]"
        output += f"  Gospel #{g['id']} {authority}: {g['rule']}\n"
        if g["reason"]:
            output += f"    Reason: {g['reason']}\n"
        output += f"    Scope: {g['scope']} | Category: {g['category']}\n\n"

    output += "\nAnalyze the change against each gospel above. Report any violations or concerns."

    return output

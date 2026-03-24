"""Tool: create_checkpoint — Create a point-in-time project snapshot."""

from datetime import datetime
from tools import register_tool

_db = None
_store = None

def init(db, store):
    global _db, _store
    _db = db
    _store = store


@register_tool(
    name="create_checkpoint",
    description="Create a timestamped checkpoint - a coherent summary of the entire project state right now.",
    schema={
        "type": "object",
        "properties": {
            "trigger": {"type": "string", "enum": ["manual", "scheduled", "milestone"], "description": "Why this checkpoint is being created"},
            "notes": {"type": "string", "description": "Optional: additional context for the checkpoint"}
        },
        "required": ["trigger"]
    }
)
def create_checkpoint(trigger: str, notes: str = "") -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H%M")
    filename = f"checkpoints/{timestamp}_checkpoint.md"

    from logger import get_logger
    get_logger("checkpoint").info(f"Creating checkpoint: {trigger}")

    # Gather stats from DB
    open_items = _db.fetchall("SELECT * FROM open_items WHERE status = 'open'")
    active_phases = _db.fetchall("SELECT * FROM phases WHERE status IN ('open', 'in_progress')")
    active_gospels = _db.fetchall("SELECT * FROM gospels WHERE status = 'active'")
    recent_changes = _db.fetchall(
        "SELECT * FROM changes ORDER BY id DESC LIMIT 10"
    )
    recent_alerts = _db.fetchall(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT 5"
    )

    # Build checkpoint content
    content = f"# Checkpoint: {now.strftime('%Y-%m-%d %H:%M')}\n\n"
    content += f"**Trigger:** {trigger}\n"
    if notes:
        content += f"**Notes:** {notes}\n"
    content += "\n"

    content += f"## Summary\n"
    content += f"- Active phases: {len(active_phases)}\n"
    content += f"- Open items: {len(open_items)}\n"
    content += f"- Active gospels: {len(active_gospels)}\n"
    content += f"- Recent changes (last 10): {len(recent_changes)}\n"
    content += "\n"

    if active_phases:
        content += "## Active Phases\n"
        for p in active_phases:
            content += f"- **{p['name']}** ({p['status']}): {p.get('goal', 'No goal set')}\n"
        content += "\n"

    if open_items:
        content += "## Open Items\n"
        for item in open_items:
            content += f"- [{item['type']}] {item['description']}\n"
        content += "\n"

    if recent_alerts:
        content += "## Recent Alerts\n"
        for a in recent_alerts:
            dismissed = " (dismissed)" if a['dismissed'] else ""
            content += f"- [{a['severity']}] {a['type']}: {a['message']}{dismissed}\n"
        content += "\n"

    result = _store.write(filename, content, mode="create")
    return f"Checkpoint created: {filename}"

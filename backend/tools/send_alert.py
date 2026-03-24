"""Tool: send_alert — Send a notification to the user."""

from tools import register_tool

_db = None

def init(db):
    global _db
    _db = db


@register_tool(
    name="send_alert",
    description="Send an alert/ping to the user via the desktop widget.",
    schema={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Alert message to display"},
            "type": {"type": "string", "enum": ["drift", "pattern", "debt", "gospel_violation", "risk", "info"], "description": "Alert category"},
            "severity": {"type": "string", "enum": ["low", "medium", "high"], "description": "How urgent"}
        },
        "required": ["message", "type"]
    }
)
def send_alert(message: str, type: str, severity: str = "medium") -> str:
    # Store in DB
    alert_id = _db.insert("alerts", {
        "message": message,
        "type": type,
        "severity": severity
    })

    # Print to console and log
    severity_icon = {"low": "[.]", "medium": "[!]", "high": "[!!!]"}.get(severity, "[!]")
    print(f"\n  {severity_icon} ALERT ({type}): {message}\n")
    from logger import get_logger
    get_logger("alert").info(f"[{severity}] {type}: {message}")

    return f"Alert sent (ID: {alert_id}): [{severity}] {type} - {message}"

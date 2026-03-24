"""Tool: log_question — Save a question for the human to answer later."""

from tools import register_tool

_store = None

def init(store):
    global _store
    _store = store


@register_tool(
    name="log_question",
    description="Log a question that Agent-0 wants to ask the human. Stored for next time the human checks in.",
    schema={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask"},
            "context": {"type": "string", "description": "Why Agent-0 is asking this"}
        },
        "required": ["question"]
    }
)
def log_question(question: str, context: str = "") -> str:
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"\n### Question ({timestamp})\n"
    entry += f"**Q:** {question}\n"
    if context:
        entry += f"**Context:** {context}\n"
    entry += f"**Status:** unanswered\n"

    _store.write("questions.md", entry, mode="append")

    # Print and log
    from logger import get_logger
    log = get_logger("question")
    log.info(f"QUESTION: {question}" + (f" | Context: {context}" if context else ""))
    print(f"\n  [?] QUESTION: {question}")
    if context:
        print(f"      Context: {context}")
    print()

    return f"Question logged: {question}"

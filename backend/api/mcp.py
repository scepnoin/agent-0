"""
Agent-0 MCP Server
Fully functional MCP tools for working agents (Claude Code, Cursor, etc.)
"""

import json
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler


MCP_TOOLS = [
    {
        "name": "agent0_brief",
        "description": "Get a welcome-back brief from Agent-0: current phase, recent changes, gospels, alerts. Use this at the START of every session.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "agent0_query",
        "description": "Ask Agent-0 any question about the project — architecture, code, issues, history, dependencies.",
        "inputSchema": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "Your question"}},
            "required": ["question"]
        }
    },
    {
        "name": "agent0_state",
        "description": "Get the current project state: phase, last change, session info.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "agent0_gospels",
        "description": "Get all active gospel rules — critical lessons and constraints for this project.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "agent0_changes",
        "description": "Get recent file changes with diffs and classifications.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max changes (default 10)"}},
            "required": []
        }
    },
    {
        "name": "agent0_issues",
        "description": "Get current known issues from the project's issue tracking docs.",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "agent0_set_intent",
        "description": "Tell Agent-0 what you're working on this session. Used for drift detection.",
        "inputSchema": {
            "type": "object",
            "properties": {"intent": {"type": "string", "description": "What you're working on"}},
            "required": ["intent"]
        }
    },
]

# Flask API base URL (MCP calls Flask internally)
FLASK_BASE = None


class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON"})
            return

        method = request.get("method", "")

        if method == "tools/list":
            self._respond(200, {"tools": MCP_TOOLS})
        elif method == "tools/call":
            tool_name = request.get("params", {}).get("name", "")
            tool_args = request.get("params", {}).get("arguments", {})
            result = self._call_tool(tool_name, tool_args)
            self._respond(200, {"content": [{"type": "text", "text": result}]})
        else:
            self._respond(404, {"error": f"Unknown method: {method}"})

    def _call_tool(self, name: str, args: dict) -> str:
        base = FLASK_BASE or "http://127.0.0.1:7800"
        try:
            if name == "agent0_brief":
                return self._get(f"{base}/brief")

            elif name == "agent0_query":
                question = args.get("question", "")
                return self._post(f"{base}/query", {"question": question})

            elif name == "agent0_state":
                return self._get(f"{base}/state")

            elif name == "agent0_gospels":
                resp = self._get_json(f"{base}/gospels")
                gospels = resp.get("gospels", [])
                if not gospels:
                    return "No active gospels."
                lines = [f"**{len(gospels)} active gospel(s):**\n"]
                for g in gospels:
                    lines.append(f"- [{g.get('category','')}] {g.get('rule','')[:150]}")
                return "\n".join(lines)

            elif name == "agent0_changes":
                limit = args.get("limit", 10)
                resp = self._get_json(f"{base}/feed")
                items = [i for i in resp.get("activity", []) if i.get("type") == "change"][:limit]
                if not items:
                    return "No changes recorded."
                lines = [f"**{len(items)} recent change(s):**\n"]
                for i in items:
                    lines.append(f"- [{i.get('category','')}] {i.get('detail','')[:120]}")
                return "\n".join(lines)

            elif name == "agent0_set_intent":
                intent = args.get("intent", "")
                self._post(f"{base}/session/intent", {"intent": intent})
                return f"Intent set: {intent}. I'll track drift against this goal."

            elif name == "agent0_issues":
                return self._post(f"{base}/query", {
                    "question": "Read Documentation/KNOWN_ISSUES.md and list all open issues with their I-numbers and severities."
                })

        except Exception as e:
            return f"Error: {str(e)}"

        return f"Unknown tool: {name}"

    def _get(self, url) -> str:
        resp = urllib.request.urlopen(url, timeout=30)
        data = json.loads(resp.read())
        # Return the most relevant text field
        for key in ["brief", "state", "answer"]:
            if key in data and data[key]:
                return data[key]
        return json.dumps(data, indent=2)

    def _get_json(self, url) -> dict:
        resp = urllib.request.urlopen(url, timeout=30)
        return json.loads(resp.read())

    def _post(self, url, data) -> str:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        return result.get("answer", result.get("brief", json.dumps(result)))

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, format, *args):
        pass


def start_mcp_server(port: int = 7801):
    global FLASK_BASE
    FLASK_BASE = f"http://127.0.0.1:{port - 1}"
    server = HTTPServer(("127.0.0.1", port), MCPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"  [MCP]     Running on http://127.0.0.1:{port}")
    return server, thread

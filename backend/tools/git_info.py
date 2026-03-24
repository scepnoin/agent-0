"""Tool: git_info — Read git state (log, status, branch, blame, diff)."""

import subprocess
from pathlib import Path
from tools import register_tool

_config = None

def init(config):
    global _config
    _config = config


def _run_git(args: list, cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True,
            cwd=cwd, timeout=15
        )
        if result.returncode != 0:
            return f"Git error: {result.stderr.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "Git is not installed or not in PATH."
    except subprocess.TimeoutExpired:
        return "Git command timed out."


@register_tool(
    name="git_info",
    description="Read git information for the project. Commit history, current branch, status, blame, detect reverts.",
    schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["log", "status", "branch", "blame", "diff_staged"], "description": "What git info to retrieve"},
            "path": {"type": "string", "description": "Optional: specific file for blame/log"},
            "limit": {"type": "integer", "description": "Optional: number of log entries (default 10)"}
        },
        "required": ["action"]
    }
)
def git_info(action: str, path: str = None, limit: int = 10) -> str:
    project_path = str(Path(_config.get("project_path")))

    if action == "log":
        args = ["log", f"--oneline", f"-{limit}"]
        if path:
            args += ["--", path]
        return _run_git(args, project_path)

    elif action == "status":
        return _run_git(["status", "--short"], project_path)

    elif action == "branch":
        current = _run_git(["branch", "--show-current"], project_path)
        all_branches = _run_git(["branch", "--list"], project_path)
        return f"Current: {current}\n\nAll branches:\n{all_branches}"

    elif action == "blame":
        if not path:
            return "blame requires a file path"
        output = _run_git(["blame", "--line-porcelain", path], project_path)
        # Truncate blame output
        lines = output.splitlines()
        if len(lines) > 200:
            return "\n".join(lines[:200]) + f"\n\n... (truncated, {len(lines)} lines)"
        return output

    elif action == "diff_staged":
        return _run_git(["diff", "--staged"], project_path)

    return f"Unknown action: {action}"

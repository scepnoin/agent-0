"""
Agent-0 Configuration v0.1
Knowledge and config stored in Agent-0's own home directory, NOT inside the project folder.

Structure:
  %LOCALAPPDATA%/Agent0/              (Windows)
  ~/.local/share/agent0/              (Linux)
  ~/Library/Application Support/Agent0/ (macOS)
    config.json                       ← global config (API keys, etc.)
    projects/
      <project-name-hash>/            ← per-project knowledge
        config.json                   ← project-specific config
        agent0.db
        state/current.md
        gospels/
        phases/
        sessions/
        ...
"""

import json
import os
import hashlib
import platform
from pathlib import Path


DEFAULT_CONFIG = {
    "project_path": "",
    "project_name": "",

    # LLM Provider
    "llm": {
        "provider": "google",
        "api_key": "",
        "model": "gemini-2.5-flash"
    },

    # Embeddings (always Google Gemini - free tier)
    "embeddings": {
        "provider": "google",
        "api_key": "",
        "model": "gemini-embedding-001",
        "task_type": "RETRIEVAL_DOCUMENT"
    },

    # Watcher
    "watcher": {
        "debounce_seconds": 5,
        "ignore_patterns": [
            "agent-0",
        ".git",
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
            "*.pyc",
            "*.pyo",
            "*.exe",
            "*.dll",
            "*.so",
            "*.db-journal",
            "tmp*",
            "*.log",
            "*.tmp"
        ]
    },

    # Agent behavior
    "agent": {
        "max_iterations": 15,
        "strictness": "normal"
    },

    # Cost controls
    "cost": {
        "max_batch_size": 20,
        "bulk_threshold": 50,
        "monthly_budget_cap": 50.00,
        "alert_at_percentage": 80
    }
}


def get_agent0_home() -> Path:
    """Get Agent-0's home directory (platform-specific)."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / "Agent0"


def project_hash(project_path: str) -> str:
    """Create a short, unique hash for a project path."""
    # Use first 8 chars of hash + project folder name for readability
    h = hashlib.md5(project_path.encode()).hexdigest()[:8]
    name = Path(project_path).name
    # Clean name for filesystem
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return f"{safe_name}_{h}"


class Config:
    """
    Agent-0 configuration manager.
    - Global config (API keys): stored in AppData/Agent0/config.json
    - Per-project knowledge: stored in <project>/agent-0/ folder (visible inside the project)
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.home_dir = get_agent0_home()
        self.project_id = project_hash(str(self.project_path))
        # Knowledge lives INSIDE the project folder in agent-0/
        self.project_dir = self.project_path / "agent-0"
        self.global_config_file = self.home_dir / "config.json"
        self.project_config_file = self.project_dir / "config.json"
        self.data = dict(DEFAULT_CONFIG)
        self.data["project_path"] = str(self.project_path)
        self.data["project_name"] = self.project_path.name

    @property
    def marker_file(self) -> Path:
        """The marker file inside the agent-0 folder."""
        return self.project_dir / "agent0.json"

    def ensure_dirs(self):
        """Create Agent-0 directory structure and project marker."""
        # Agent-0 home
        self.home_dir.mkdir(parents=True, exist_ok=True)

        # Project knowledge directories (in AppData)
        dirs = [
            self.project_dir,
            self.project_dir / "gospels",
            self.project_dir / "phases",
            self.project_dir / "sessions",
            self.project_dir / "state",
            self.project_dir / "patterns",
            self.project_dir / "checkpoints",
            self.project_dir / "debt",
            self.project_dir / "modules",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Create initial state file
        state_file = self.project_dir / "state" / "current.md"
        if not state_file.exists():
            state_file.write_text(
                f"# Current State\n\n"
                f"**Project:** {self.data['project_name']}\n"
                f"**Status:** Initializing\n"
                f"**Current Phase:** None\n"
                f"**Last Updated:** Never\n"
            )

        # Drop marker file in the project root
        self._write_marker()

        # Add agent-0/ to .gitignore
        gitignore = self.project_path / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            if "agent-0/" not in content:
                with open(gitignore, "a") as f:
                    f.write("\n# Agent-0 sentinel knowledge\nagent-0/\n")

    def _write_marker(self):
        """Write the small .agent0.json marker in the project root."""
        marker = {
            "agent0": True,
            "project_id": self.project_id,
            "project_name": self.data["project_name"],
            "knowledge_dir": str(self.project_dir),
            "status": "connected",
            "bonded": True
        }
        with open(self.marker_file, "w") as f:
            json.dump(marker, f, indent=2)

    @staticmethod
    def find_marker(project_path: str) -> dict | None:
        """Check if a project folder has an Agent-0 folder. Returns marker data or None."""
        marker_file = Path(project_path) / "agent-0" / "agent0.json"
        if marker_file.exists():
            with open(marker_file, "r") as f:
                return json.load(f)
        return None

    def load(self) -> dict:
        """Load config — project first, then global API keys override (keys are never in project config)."""
        # Load project config first (settings, preferences)
        if self.project_config_file.exists():
            with open(self.project_config_file, "r") as f:
                saved = json.load(f)
            self._deep_merge(self.data, saved)

        # Load global config LAST — API keys from AppData override project's empty keys
        if self.global_config_file.exists():
            with open(self.global_config_file, "r") as f:
                saved = json.load(f)
            # Only merge keys that have values (don't let empty project keys win)
            if saved.get("llm", {}).get("api_key"):
                self.data.setdefault("llm", {})["api_key"] = saved["llm"]["api_key"]
            if saved.get("llm", {}).get("provider"):
                self.data.setdefault("llm", {})["provider"] = saved["llm"]["provider"]
            if saved.get("llm", {}).get("model"):
                self.data.setdefault("llm", {})["model"] = saved["llm"]["model"]
            if saved.get("embeddings", {}).get("api_key"):
                self.data.setdefault("embeddings", {})["api_key"] = saved["embeddings"]["api_key"]

        return self.data

    def save(self):
        """Save config — API keys in AppData ONLY, project config without keys."""
        self.ensure_dirs()

        # Save global config WITH API keys (in AppData — safe)
        global_data = {
            "llm": dict(self.data.get("llm", {})),
            "embeddings": dict(self.data.get("embeddings", {})),
        }
        with open(self.global_config_file, "w") as f:
            json.dump(global_data, f, indent=2)

        # Save project config WITHOUT API keys (in project folder — may be public)
        import copy
        project_data = copy.deepcopy(self.data)
        if "llm" in project_data and "api_key" in project_data["llm"]:
            project_data["llm"]["api_key"] = ""  # Strip key from project config
        if "embeddings" in project_data and "api_key" in project_data["embeddings"]:
            project_data["embeddings"]["api_key"] = ""  # Strip key
        with open(self.project_config_file, "w") as f:
            json.dump(project_data, f, indent=2)

    def get(self, key: str, default=None):
        """Get a config value. Supports dot notation: 'llm.provider'."""
        keys = key.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value):
        """Set a config value. Supports dot notation: 'llm.api_key'."""
        keys = key.split(".")
        d = self.data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """Merge override into base, recursively."""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                Config._deep_merge(base[k], v)
            else:
                base[k] = v

    @property
    def is_configured(self) -> bool:
        """Check if minimum config is set."""
        return bool(self.get("llm.api_key")) and bool(self.get("project_path"))

    @property
    def db_path(self) -> Path:
        return self.project_dir / "agent0.db"

    @property
    def knowledge_dir(self) -> Path:
        return self.project_dir

    @property
    def log_path(self) -> Path:
        return self.project_dir / "agent0.log"

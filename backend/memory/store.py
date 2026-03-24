"""
Agent-0 Markdown Store
Read, write, append, and manage markdown knowledge files.
"""

from pathlib import Path
from datetime import datetime


class MarkdownStore:
    """Manages markdown files in the .agent0/ knowledge directory."""

    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir

    def read(self, relative_path: str) -> str:
        """Read a markdown file. Path is relative to .agent0/."""
        full_path = self.knowledge_dir / relative_path
        if not full_path.exists():
            return f"File not found: {relative_path}"
        return full_path.read_text(encoding="utf-8")

    def write(self, relative_path: str, content: str, mode: str = "create") -> str:
        """
        Write to a markdown file.
        mode: 'create' (new file), 'append' (add to end), 'overwrite' (replace)
        """
        full_path = self.knowledge_dir / relative_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if mode == "create":
            if full_path.exists():
                return f"File already exists: {relative_path}. Use 'append' or 'overwrite'."
            full_path.write_text(content, encoding="utf-8")
            return f"Created: {relative_path}"

        elif mode == "append":
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(f"\n{content}")
            return f"Appended to: {relative_path}"

        elif mode == "overwrite":
            full_path.write_text(content, encoding="utf-8")
            return f"Overwrote: {relative_path}"

        return f"Unknown mode: {mode}"

    def list_files(self, subdirectory: str = "") -> list[str]:
        """List all markdown files in a subdirectory."""
        target = self.knowledge_dir / subdirectory if subdirectory else self.knowledge_dir
        if not target.exists():
            return []
        return [
            str(f.relative_to(self.knowledge_dir))
            for f in target.rglob("*.md")
        ]

    def get_line_count(self, relative_path: str) -> int:
        """Get the line count of a file."""
        full_path = self.knowledge_dir / relative_path
        if not full_path.exists():
            return 0
        return len(full_path.read_text(encoding="utf-8").splitlines())

    def needs_split(self, relative_path: str, max_lines: int = 200) -> bool:
        """Check if a file exceeds the line threshold."""
        return self.get_line_count(relative_path) > max_lines

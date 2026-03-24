"""
Agent-0 Knowledge Indexer
Chunks markdown files, generates embeddings, indexes for hybrid search.
All paths normalized to forward slashes for consistency.
"""

import re
import json
from pathlib import Path
from logger import get_logger

log = get_logger("indexer")


def normalize_path(path: str) -> str:
    """Normalize path separators to forward slash."""
    return path.replace("\\", "/")


class Indexer:
    """Indexes markdown knowledge files for hybrid search."""

    def __init__(self, db, llm_client, knowledge_dir: Path):
        self.db = db
        self.llm = llm_client
        self.knowledge_dir = knowledge_dir

    def chunk_markdown(self, content: str, source_file: str) -> list[dict]:
        """Split markdown into semantic chunks by heading and paragraph."""
        source_file = normalize_path(source_file)
        chunks = []
        current_chunk = []

        for line in content.split("\n"):
            if line.startswith("#"):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text and len(chunk_text) > 20:
                        chunks.append({"source_file": source_file, "chunk": chunk_text})
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text and len(chunk_text) > 20:
                chunks.append({"source_file": source_file, "chunk": chunk_text})

        # Fallback: chunk by paragraphs
        if not chunks and content.strip():
            for para in re.split(r"\n\n+", content.strip()):
                para = para.strip()
                if para and len(para) > 20:
                    chunks.append({"source_file": source_file, "chunk": para})

        return chunks

    # Files too large for embedding — use FTS5 only
    SKIP_EMBEDDING_FILES = {"code_index.md", "dependencies.md"}

    def index_file(self, relative_path: str):
        """Index a single markdown file."""
        relative_path = normalize_path(relative_path)
        full_path = self.knowledge_dir / relative_path
        if not full_path.exists():
            return

        # Skip very large files entirely (searchable via raw grep instead)
        filename = Path(relative_path).name
        if filename in self.SKIP_EMBEDDING_FILES:
            log.debug(f"Skipping embedding for large file: {relative_path}")
            return

        content = full_path.read_text(encoding="utf-8", errors="replace")
        chunks = self.chunk_markdown(content, relative_path)

        # Remove ALL old entries for this file (both slash variants)
        for path_variant in [relative_path, relative_path.replace("/", "\\")]:
            self.db.execute("DELETE FROM memory_index WHERE source_file = ?", (path_variant,))
            try:
                self.db.execute("DELETE FROM memory_fts WHERE source_file = ?", (path_variant,))
            except Exception:
                pass

        for chunk_data in chunks:
            # Skip embedding for very large chunks (just use FTS5)
            chunk_text = chunk_data["chunk"]
            if len(chunk_text) > 5000:
                embedding_blob = None
            else:
                try:
                    embedding = self.llm.embed(chunk_text[:2000])  # Cap embedding input
                    embedding_blob = json.dumps(embedding).encode()
                except Exception:
                    embedding_blob = None

            row_id = self.db.insert("memory_index", {
                "source_file": chunk_data["source_file"],
                "chunk": chunk_data["chunk"],
                "embedding": embedding_blob
            })

            try:
                self.db.execute(
                    "INSERT INTO memory_fts(rowid, source_file, chunk) VALUES (?, ?, ?)",
                    (row_id, chunk_data["source_file"], chunk_data["chunk"])
                )
            except Exception:
                pass

        self.db.conn.commit()
        log.debug(f"Indexed {relative_path}: {len(chunks)} chunks")

    def index_all(self):
        """Re-index all markdown files."""
        count = 0
        for md_file in self.knowledge_dir.rglob("*.md"):
            relative = normalize_path(str(md_file.relative_to(self.knowledge_dir)))
            self.index_file(relative)
            count += 1
        log.info(f"Indexed {count} files")

    def reindex_if_changed(self, relative_path: str):
        """Re-index a file after it's been written to."""
        relative_path = normalize_path(relative_path)
        full_path = self.knowledge_dir / relative_path
        if full_path.exists() and full_path.suffix == ".md":
            self.index_file(relative_path)

"""
Agent-0 Hybrid Search
Combines vector similarity (semantic) + FTS5 BM25 (keyword) with score fusion.
"""

import json
import math


class HybridSearch:
    """Hybrid search across Agent-0's knowledge base."""

    def __init__(self, db, llm_client):
        self.db = db
        self.llm = llm_client

    def search(self, query: str, scope: str = "all", limit: int = 10) -> list[dict]:
        """
        Search knowledge using hybrid approach.
        Returns list of {source_file, chunk, score} sorted by relevance.
        """
        # Get results from both search methods
        keyword_results = self._keyword_search(query, scope, limit * 2)
        vector_results = self._vector_search(query, scope, limit * 2)

        # Fuse results using Reciprocal Rank Fusion (RRF)
        fused = self._rrf_fusion(keyword_results, vector_results)

        # Sort by fused score, return top results
        fused.sort(key=lambda x: x["score"], reverse=True)
        return fused[:limit]

    def _keyword_search(self, query: str, scope: str, limit: int) -> list[dict]:
        """FTS5 keyword search."""
        try:
            scope_filter = ""
            params = [query]

            if scope != "all":
                scope_filter = "AND source_file LIKE ?"
                params.append(f"{scope}/%")

            rows = self.db.fetchall(f"""
                SELECT source_file, chunk, rank
                FROM memory_fts
                WHERE memory_fts MATCH ?
                {scope_filter}
                ORDER BY rank
                LIMIT ?
            """, tuple(params + [limit]))

            return [
                {
                    "source_file": row["source_file"],
                    "chunk": row["chunk"],
                    "score": -row["rank"]  # FTS5 rank is negative (lower = better)
                }
                for row in rows
            ]
        except Exception:
            return []

    def _vector_search(self, query: str, scope: str, limit: int) -> list[dict]:
        """Vector similarity search. Uses sqlite-vec if available, falls back to manual."""
        try:
            query_embedding = self.llm.embed_query(query)

            # Try sqlite-vec first (SIMD-accelerated)
            try:
                import sqlite_vec
                from sqlite_vec import serialize_float32

                query_blob = serialize_float32(query_embedding)
                scope_filter = ""
                params = [query_blob, limit]
                if scope != "all":
                    # sqlite-vec doesn't support WHERE with MATCH easily,
                    # so we filter after
                    pass

                rows = self.db.fetchall("""
                    SELECT rowid, distance FROM vec_embeddings
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """, tuple(params))

                results = []
                for row in rows:
                    # Get the actual chunk data
                    chunk_data = self.db.fetchone(
                        "SELECT source_file, chunk FROM memory_index WHERE id = ?",
                        (row["rowid"],)
                    )
                    if chunk_data:
                        if scope != "all" and not chunk_data["source_file"].startswith(f"{scope}/"):
                            continue
                        results.append({
                            "source_file": chunk_data["source_file"],
                            "chunk": chunk_data["chunk"],
                            "score": 1.0 - row["distance"]  # Convert distance to similarity
                        })
                return results

            except (ImportError, Exception):
                pass  # Fall back to manual search

            # Fallback: manual cosine similarity
            scope_filter = ""
            params = []
            if scope != "all":
                scope_filter = "WHERE source_file LIKE ?"
                params.append(f"{scope}/%")

            rows = self.db.fetchall(f"""
                SELECT id, source_file, chunk, embedding
                FROM memory_index
                {scope_filter}
            """, tuple(params))

            results = []
            for row in rows:
                if row["embedding"] is None:
                    continue
                stored_embedding = json.loads(row["embedding"])
                similarity = self._cosine_similarity(query_embedding, stored_embedding)
                results.append({
                    "source_file": row["source_file"],
                    "chunk": row["chunk"],
                    "score": similarity
                })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

        except Exception:
            return []

    def _rrf_fusion(self, keyword_results: list, vector_results: list, k: int = 60) -> list[dict]:
        """
        Reciprocal Rank Fusion — combines rankings from multiple search methods.
        Higher k = more weight to lower-ranked results.
        """
        scores = {}

        for rank, result in enumerate(keyword_results):
            key = (result["source_file"], result["chunk"][:100])
            if key not in scores:
                scores[key] = {"source_file": result["source_file"], "chunk": result["chunk"], "score": 0}
            scores[key]["score"] += 1.0 / (k + rank + 1)

        for rank, result in enumerate(vector_results):
            key = (result["source_file"], result["chunk"][:100])
            if key not in scores:
                scores[key] = {"source_file": result["source_file"], "chunk": result["chunk"], "score": 0}
            scores[key]["score"] += 1.0 / (k + rank + 1)

        return list(scores.values())

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

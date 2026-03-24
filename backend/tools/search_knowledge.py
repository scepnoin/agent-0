"""Tool: search_knowledge — Search ALL of Agent-0's knowledge (markdown files + DB)."""

import os
from pathlib import Path
from tools import register_tool

_search = None
_store = None
_config = None
_db = None

def init(search, store=None, config=None, db=None):
    global _search, _store, _config, _db
    _search = search
    _store = store
    _config = config
    _db = db


@register_tool(
    name="search_knowledge",
    description="Search ALL of Agent-0's knowledge: markdown files (full text grep + semantic search) and database tables. Returns relevant chunks from all sources.",
    schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "scope": {"type": "string", "enum": ["all", "docs", "code", "gospels", "db"], "description": "Optional: limit search scope"}
        },
        "required": ["query"]
    }
)
def search_knowledge(query: str, scope: str = "all") -> str:
    results = []

    # Source 1: FTS5 + vector hybrid search (existing)
    if _search and scope in ("all", "docs", "code", "gospels"):
        try:
            hybrid_results = _search.search(query, scope="all", limit=5)
            for r in hybrid_results:
                results.append({
                    "source": f"[index] {r['source_file']}",
                    "text": r["chunk"][:400]
                })
        except Exception:
            pass

    # Source 2: Raw grep across ALL knowledge markdown files
    if _config and scope in ("all", "docs", "code", "gospels"):
        try:
            knowledge_dir = _config.knowledge_dir
            query_lower = query.lower()
            # Search for each word in query
            query_words = [w for w in query_lower.split() if len(w) > 2]

            for root, dirs, files in os.walk(knowledge_dir):
                for fname in files:
                    if not fname.endswith(".md"):
                        continue
                    fpath = Path(root) / fname
                    rel = str(fpath.relative_to(knowledge_dir)).replace("\\", "/")

                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue

                    # Check if any query word appears in this file
                    content_lower = content.lower()
                    matches = sum(1 for w in query_words if w in content_lower)
                    if matches == 0:
                        continue

                    # Find the most relevant section (paragraph containing the query words)
                    best_section = ""
                    best_score = 0
                    paragraphs = content.split("\n\n")
                    for para in paragraphs:
                        para_lower = para.lower()
                        score = sum(1 for w in query_words if w in para_lower)
                        if score > best_score:
                            best_score = score
                            best_section = para.strip()

                    if best_section and best_score >= max(1, len(query_words) // 2):
                        # Avoid duplicates from hybrid search
                        already_found = any(best_section[:100] in r["text"] for r in results)
                        if not already_found:
                            results.append({
                                "source": f"[grep] {rel}",
                                "text": best_section[:500]
                            })
        except Exception:
            pass

    # Source 3: DB tables (for structured data)
    if _db and scope in ("all", "db"):
        try:
            query_lower = query.lower()

            # Search gospels
            if any(w in query_lower for w in ["gospel", "rule", "constraint", "must", "never"]):
                gospels = _db.fetchall("SELECT id, rule, reason, category FROM gospels WHERE status = 'active'")
                for g in gospels:
                    if any(w in (g["rule"] or "").lower() for w in query_lower.split() if len(w) > 2):
                        results.append({
                            "source": f"[db] gospel #{g['id']}",
                            "text": f"Rule: {g['rule'][:200]} | Reason: {(g['reason'] or '')[:100]} | Category: {g['category']}"
                        })

            # Search phases
            if any(w in query_lower for w in ["phase", "goal", "status", "current", "roadmap"]):
                phases = _db.fetchall("SELECT * FROM phases")
                for p in phases:
                    results.append({
                        "source": "[db] phase",
                        "text": f"Phase: {p['name']} | Goal: {(p['goal'] or '')[:200]} | Status: {p['status']}"
                    })

            # Search open items
            if any(w in query_lower for w in ["issue", "bug", "critical", "dependency", "risk"]):
                items = _db.fetchall("SELECT * FROM open_items LIMIT 10")
                for item in items:
                    if any(w in (item["description"] or "").lower() for w in query_lower.split() if len(w) > 2):
                        results.append({
                            "source": f"[db] open_item",
                            "text": f"{item['type']}: {item['description'][:200]}"
                        })
        except Exception:
            pass

    if not results:
        return f"No results found for: {query}"

    # Sort: grep results first (more specific), then index, then DB
    output = f"Found {len(results)} result(s) for '{query}':\n\n"
    for i, r in enumerate(results[:15], 1):
        output += f"--- {r['source']} ---\n{r['text']}\n\n"

    return output

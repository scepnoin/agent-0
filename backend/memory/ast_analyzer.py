"""
Agent-0 AST Analyzer
Parses Python files programmatically to extract real structure:
- Imports (what depends on what)
- Classes (names, bases, methods)
- Functions (names, args, decorators)
- TODOs/FIXMEs
- File-level docstrings

No LLM needed — pure Python ast module.
"""

import ast
import os
from pathlib import Path
from logger import get_logger

log = get_logger("ast")


def analyze_python_file(filepath: Path) -> dict | None:
    """Parse a Python file and extract its structure."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return {"error": "SyntaxError", "path": str(filepath)}

    result = {
        "path": str(filepath),
        "lines": len(source.splitlines()),
        "docstring": ast.get_docstring(tree) or "",
        "imports": [],
        "from_imports": [],
        "classes": [],
        "functions": [],
        "todos": [],
        "global_vars": [],
    }

    # Extract imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                result["from_imports"].append({
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname
                })

    # Extract top-level classes and functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            cls = {
                "name": node.name,
                "bases": [_name(b) for b in node.bases],
                "methods": [],
                "decorators": [_name(d) for d in node.decorator_list],
                "docstring": ast.get_docstring(node) or "",
                "line": node.lineno,
            }
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    cls["methods"].append({
                        "name": item.name,
                        "args": [a.arg for a in item.args.args if a.arg != "self"],
                        "decorators": [_name(d) for d in item.decorator_list],
                        "docstring": ast.get_docstring(item) or "",
                        "line": item.lineno,
                    })
            result["classes"].append(cls)

        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            result["functions"].append({
                "name": node.name,
                "args": [a.arg for a in node.args.args],
                "decorators": [_name(d) for d in node.decorator_list],
                "docstring": ast.get_docstring(node) or "",
                "line": node.lineno,
            })

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result["global_vars"].append(target.id)

    # Extract TODOs and FIXMEs from comments
    for i, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        for marker in ["TODO", "FIXME", "HACK", "WORKAROUND", "XXX", "BUG"]:
            if marker in stripped and stripped.startswith("#"):
                result["todos"].append({
                    "line": i,
                    "marker": marker,
                    "text": stripped.lstrip("# ").strip()
                })

    return result


def analyze_directory(directory: Path, skip_dirs: set = None) -> dict:
    """Analyze all Python files in a directory. Returns structured data."""
    if skip_dirs is None:
        skip_dirs = {"__pycache__", ".git", "venv", ".venv", "node_modules",
                     "agent-0", ".agent0", "target", "dist", "build",
                     "t5_training_env_py311", "python", "site-packages",
                     ".tox", ".pytest_cache", ".mypy_cache", "egg-info",
                     ".eggs", "Lib", "lib", "Scripts", "Include",
                     "third_party", "vendor", "vendors", "vendored",
                     "llama.cpp", "ggml", "whisper.cpp",
                     "external", "deps"}

    files = {}
    dependency_graph = {}  # file -> [files it imports from]
    all_modules = {}  # module.path -> filepath

    # Walk directory with proper skip dirs (much faster than rglob)
    py_files = []
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(Path(os.path.join(root, f)))

    # First pass: map module paths
    for py_file in sorted(py_files):
        rel = str(py_file.relative_to(directory)).replace("\\", "/")
        module_path = rel.replace("/", ".").replace(".py", "")
        if module_path.endswith(".__init__"):
            module_path = module_path[:-9]
        all_modules[module_path] = rel

    # Second pass: analyze each file
    for py_file in sorted(py_files):
        rel = str(py_file.relative_to(directory)).replace("\\", "/")
        analysis = analyze_python_file(py_file)
        if analysis and "error" not in analysis:
            analysis["path"] = rel
            files[rel] = analysis

            # Build dependency edges (use prefix set for fast matching)
            deps = set()
            for imp in analysis["imports"]:
                if imp in all_modules:
                    deps.add(all_modules[imp])
                else:
                    # Check first component: "core.agency" -> check "core"
                    parts = imp.split(".")
                    for i in range(len(parts), 0, -1):
                        prefix = ".".join(parts[:i])
                        if prefix in all_modules:
                            deps.add(all_modules[prefix])
                            break

            for fi in analysis["from_imports"]:
                mod = fi["module"]
                if mod in all_modules:
                    deps.add(all_modules[mod])
                else:
                    parts = mod.split(".")
                    for i in range(len(parts), 0, -1):
                        prefix = ".".join(parts[:i])
                        if prefix in all_modules:
                            deps.add(all_modules[prefix])
                            break

            deps.discard(rel)  # Don't depend on yourself
            dependency_graph[rel] = sorted(deps)

    return {
        "files": files,
        "dependency_graph": dependency_graph,
        "module_map": all_modules,
        "total_files": len(files),
        "total_classes": sum(len(f.get("classes", [])) for f in files.values()),
        "total_functions": sum(len(f.get("functions", [])) for f in files.values()),
        "total_todos": sum(len(f.get("todos", [])) for f in files.values()),
        "total_lines": sum(f.get("lines", 0) for f in files.values()),
    }


def format_file_summary(analysis: dict) -> str:
    """Format a single file's analysis as readable text with line numbers for every method."""
    lines = [f"### {analysis['path']} ({analysis['lines']} lines)"]

    if analysis.get("docstring"):
        lines.append(f"*{analysis['docstring'][:200]}*")

    if analysis.get("classes"):
        for cls in analysis["classes"]:
            bases = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
            lines.append(f"\n**class {cls['name']}{bases}** (line {cls['line']})")
            if cls["docstring"]:
                lines.append(f"  {cls['docstring'][:150]}")
            for m in cls["methods"]:
                args = ", ".join(m["args"][:5])
                dec = f" @{m['decorators'][0]}" if m["decorators"] else ""
                doc = f" — {m['docstring'][:80]}" if m["docstring"] else ""
                lines.append(f"  - `{m['name']}({args})` line {m['line']}{dec}{doc}")

    if analysis.get("functions"):
        for fn in analysis["functions"]:
            args = ", ".join(fn["args"][:5])
            dec = f" @{fn['decorators'][0]}" if fn["decorators"] else ""
            doc = f" — {fn['docstring'][:80]}" if fn["docstring"] else ""
            lines.append(f"\n**def {fn['name']}({args})** line {fn['line']}{dec}{doc}")

    if analysis.get("imports") or analysis.get("from_imports"):
        imp_list = analysis["imports"] + [f"{fi['module']}.{fi['name']}" for fi in analysis["from_imports"]]
        lines.append(f"\nImports: {', '.join(imp_list[:20])}")

    if analysis.get("todos"):
        lines.append(f"\nTODOs:")
        for todo in analysis["todos"][:10]:
            lines.append(f"  - [{todo['marker']}] line {todo['line']}: {todo['text'][:80]}")

    return "\n".join(lines)


def format_file_index(analysis: dict) -> str:
    """Format a compact index: every class, every method, every function with line numbers.
    This is the skeleton Agent-0 uses to know WHERE things are for on-demand reading."""
    lines = [f"### {analysis['path']} ({analysis['lines']} lines)"]

    if analysis.get("docstring"):
        lines.append(f"  Doc: {analysis['docstring'][:100]}")

    for cls in analysis.get("classes", []):
        bases = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
        lines.append(f"  class {cls['name']}{bases} @ line {cls['line']} ({len(cls['methods'])} methods)")
        for m in cls["methods"]:
            args = ", ".join(m["args"][:4])
            lines.append(f"    .{m['name']}({args}) @ line {m['line']}")

    for fn in analysis.get("functions", []):
        args = ", ".join(fn["args"][:4])
        lines.append(f"  def {fn['name']}({args}) @ line {fn['line']}")

    return "\n".join(lines)


def format_dependency_graph(graph: dict) -> str:
    """Format dependency graph as readable text."""
    lines = ["# Dependency Graph\n"]
    for file, deps in sorted(graph.items()):
        if deps:
            lines.append(f"**{file}** depends on:")
            for d in deps:
                lines.append(f"  -> {d}")
            lines.append("")
    return "\n".join(lines)


def _name(node) -> str:
    """Extract name from an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Call):
        return _name(node.func)
    elif isinstance(node, ast.Constant):
        return str(node.value)
    return "?"

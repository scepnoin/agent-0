"""
Agent-0 Code Scanner
Runs MULTIPLE static analysis tools and cross-references findings.

Tools:
- semgrep: Multi-language security patterns (Python, Kotlin, JS, etc.)
- bandit: Python-specific security vulnerabilities
- radon: Python complexity metrics (finds risky complex functions)

Cross-referencing: if multiple tools flag the same file/line, confidence goes UP.
"""

import subprocess
import json as json_mod
import os
from pathlib import Path
from logger import get_logger

log = get_logger("scanner")

SKIP_DIRS = {
    "agent-0", ".git", "__pycache__", "node_modules", "venv", ".venv",
    "target", "dist", "build", "third_party", "vendor", "vendors", "vendored",
    "t5_training_env_py311", "python", "site-packages",
    "Lib", "lib", "Scripts", "Include",
    # Backup/archive dirs — not part of running application
    ".backup", "backup", "backups", "db_backups", "archive",
    # Third-party / vendored code
    "llama.cpp", "ggml", "whisper.cpp", "external", "deps",
    # Test/output dirs
    "tests_runtime_tmp", "benchmark-summary", "output",
    ".eggs", "egg-info", ".tox", ".pytest_cache", ".mypy_cache",
}


def run_semgrep(project_path: Path) -> list:
    """Run semgrep security scan."""
    findings = []
    try:
        # Detect languages
        configs = []
        try:
            if any(project_path.rglob("*.py")):
                configs.append("p/python")
            if any(project_path.rglob("*.kt")):
                configs.append("p/kotlin")
            if any(project_path.rglob("package.json")):
                configs.append("p/javascript")
        except Exception:
            pass

        if not configs:
            configs = ["p/default"]

        cmd = ["semgrep", "scan", "--json", "--timeout", "60", "--max-target-bytes", "500000"]
        for c in configs:
            cmd.extend(["--config", c])
        for skip in SKIP_DIRS:
            cmd.extend(["--exclude", skip])
        cmd.append(str(project_path))

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=300
        )

        if result.stdout:
            json_start = result.stdout.find('{"')
            output = result.stdout[json_start:] if json_start >= 0 else result.stdout
            data = json_mod.loads(output)
            for r in data.get("results", []):
                findings.append({
                    "tool": "semgrep",
                    "rule": r.get("check_id", "unknown"),
                    "severity": r.get("extra", {}).get("severity", "WARNING"),
                    "message": r.get("extra", {}).get("message", ""),
                    "file": r.get("path", ""),
                    "line": r.get("start", {}).get("line", 0),
                    "code": r.get("extra", {}).get("lines", "")[:200],
                })

        log.info(f"Semgrep: {len(findings)} finding(s)")
    except subprocess.TimeoutExpired:
        log.warning("Semgrep timed out")
    except FileNotFoundError:
        log.warning("Semgrep not installed")
    except Exception as e:
        log.error(f"Semgrep failed: {e}")

    return findings


def run_bandit(project_path: Path) -> list:
    """Run bandit Python security scanner."""
    findings = []
    try:
        # Find Python directories to scan
        py_dirs = []
        for item in project_path.iterdir():
            if item.is_dir() and item.name not in SKIP_DIRS:
                if any(item.rglob("*.py")):
                    py_dirs.append(str(item))
        if not py_dirs:
            return []

        cmd = ["bandit", "-r", "-f", "json", "-q"]
        # Exclude patterns
        excludes = ",".join(f"*/{s}/*" for s in SKIP_DIRS)
        cmd.extend(["--exclude", excludes])
        cmd.extend(py_dirs[:5])  # Limit to 5 dirs

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=300
        )

        if result.stdout:
            data = json_mod.loads(result.stdout)
            for r in data.get("results", []):
                severity = r.get("issue_severity", "MEDIUM")
                findings.append({
                    "tool": "bandit",
                    "rule": r.get("test_id", "unknown") + ": " + r.get("test_name", ""),
                    "severity": severity,
                    "message": r.get("issue_text", ""),
                    "file": r.get("filename", ""),
                    "line": r.get("line_number", 0),
                    "code": r.get("code", "")[:200],
                })

        log.info(f"Bandit: {len(findings)} finding(s)")
    except subprocess.TimeoutExpired:
        log.warning("Bandit timed out")
    except FileNotFoundError:
        log.warning("Bandit not installed")
    except Exception as e:
        log.error(f"Bandit failed: {e}")

    return findings


def run_radon(project_path: Path) -> list:
    """Run radon complexity checker. Flags functions with complexity > 15 (high risk)."""
    findings = []
    try:
        cmd = ["radon", "cc", "-j", "-n", "C"]  # Only show C+ (complexity >= 11)

        # Find Python dirs
        py_dirs = []
        for item in project_path.iterdir():
            if item.is_dir() and item.name not in SKIP_DIRS:
                if any(item.rglob("*.py")):
                    py_dirs.append(str(item))
        if not py_dirs:
            return []

        cmd.extend(py_dirs[:5])

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=120
        )

        if result.stdout:
            data = json_mod.loads(result.stdout)
            for filepath, functions in data.items():
                for func in functions:
                    complexity = func.get("complexity", 0)
                    if complexity >= 15:  # High risk
                        severity = "HIGH" if complexity >= 25 else "WARNING"
                        findings.append({
                            "tool": "radon",
                            "rule": f"complexity:{complexity}",
                            "severity": severity,
                            "message": f"Function '{func.get('name', '?')}' has cyclomatic complexity {complexity} (high risk, hard to test/maintain)",
                            "file": filepath,
                            "line": func.get("lineno", 0),
                            "code": f"class={func.get('classname', '')} type={func.get('type', '')}",
                        })

        log.info(f"Radon: {len(findings)} finding(s)")
    except subprocess.TimeoutExpired:
        log.warning("Radon timed out")
    except FileNotFoundError:
        log.warning("Radon not installed")
    except Exception as e:
        log.error(f"Radon failed: {e}")

    return findings


def run_scan(project_path: Path) -> dict:
    """Run ALL scanners and cross-reference results."""
    log.info(f"Full scan: {project_path}")

    all_findings = []

    # Run all tools
    all_findings.extend(run_semgrep(project_path))
    all_findings.extend(run_bandit(project_path))
    all_findings.extend(run_radon(project_path))

    # Deduplicate by file+line (keep all tools' perspectives)
    seen = set()
    unique = []
    for f in all_findings:
        key = f"{f['file']}:{f['line']}:{f['tool']}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    # Cross-reference: if multiple tools flag the same file+line, boost severity
    file_line_count = {}
    for f in unique:
        key = f"{f['file']}:{f['line']}"
        file_line_count[key] = file_line_count.get(key, 0) + 1

    for f in unique:
        key = f"{f['file']}:{f['line']}"
        if file_line_count[key] > 1:
            f["cross_referenced"] = True
            f["tools_agreeing"] = file_line_count[key]
            # Boost severity if multiple tools agree
            if f["severity"] == "WARNING":
                f["severity"] = "HIGH"
        else:
            f["cross_referenced"] = False

    # Sort: cross-referenced first, then by severity
    severity_order = {"ERROR": 0, "CRITICAL": 0, "HIGH": 1, "WARNING": 2, "MEDIUM": 2, "INFO": 3, "LOW": 3}
    unique.sort(key=lambda x: (0 if x["cross_referenced"] else 1, severity_order.get(x["severity"], 5)))

    log.info(f"Total: {len(unique)} findings ({sum(1 for f in unique if f['cross_referenced'])} cross-referenced)")

    return {
        "total": len(unique),
        "findings": unique,
        "by_severity": _count_by(unique, "severity"),
        "by_tool": _count_by(unique, "tool"),
        "by_file": _count_by(unique, "file"),
        "cross_referenced": sum(1 for f in unique if f["cross_referenced"]),
    }


def format_findings(results: dict) -> str:
    """Format scan results as markdown."""
    lines = [f"# Code Scan Results\n"]
    lines.append(f"**Total:** {results['total']} | **Cross-referenced:** {results.get('cross_referenced', 0)}\n")

    if results['by_severity']:
        lines.append("**By severity:**")
        for sev, count in sorted(results['by_severity'].items()):
            lines.append(f"- {sev}: {count}")
    if results['by_tool']:
        lines.append("\n**By tool:**")
        for tool, count in results['by_tool'].items():
            lines.append(f"- {tool}: {count}")
    lines.append("")

    # Cross-referenced findings first
    cross = [f for f in results['findings'] if f.get('cross_referenced')]
    if cross:
        lines.append("## Cross-Referenced (Multiple Tools Agree)\n")
        for f in cross:
            lines.append(f"### [{f['severity']}] {f['rule']} ({f.get('tools_agreeing', 0)} tools)")
            lines.append(f"**File:** `{f['file']}:{f['line']}`")
            lines.append(f"**Tool:** {f['tool']} | **Message:** {f['message'][:200]}")
            lines.append("")

    # Other findings
    others = [f for f in results['findings'] if not f.get('cross_referenced')]
    if others:
        lines.append("## Other Findings\n")
        for f in others[:30]:
            lines.append(f"### [{f['severity']}] {f['rule']}")
            lines.append(f"**File:** `{f['file']}:{f['line']}` | **Tool:** {f['tool']}")
            lines.append(f"**Message:** {f['message'][:200]}")
            lines.append("")

    return "\n".join(lines)


def analyze_findings(results: dict, llm_client, store, project_path: Path) -> str:
    """Cross-reference scan findings against codebase context.
    Produces a curated audit_report.md that separates real issues from noise.
    This is the whole point — raw tool output is noise, Agent-0 adds intelligence."""

    if results["total"] == 0:
        report = "# Audit Report\n\nNo issues found. Codebase is clean.\n"
        store.write("audit_report.md", report, mode="overwrite")
        return report

    # Categorize findings by location to identify noise patterns
    backup_findings = []
    third_party_findings = []
    real_findings = []

    noise_patterns = [
        ".backup", "backup", "backups", "db_backups", "archive",
        "third_party", "vendor", "llama.cpp", "ggml", "whisper.cpp",
        "external", "deps", "site-packages", "venv", ".venv",
        "Documentation/backups", "Documentation/archive",
    ]

    for f in results["findings"]:
        fpath = f["file"].replace("\\", "/")
        is_noise = any(noise in fpath for noise in noise_patterns)

        if is_noise:
            if "backup" in fpath.lower() or "archive" in fpath.lower():
                backup_findings.append(f)
            else:
                third_party_findings.append(f)
        else:
            real_findings.append(f)

    # Build a summary of real findings for LLM analysis
    real_high = [f for f in real_findings if f["severity"] in ("ERROR", "CRITICAL", "HIGH")]
    real_med = [f for f in real_findings if f["severity"] in ("MEDIUM", "WARNING")]
    real_low = [f for f in real_findings if f["severity"] in ("LOW", "INFO")]

    # Format real HIGH findings for LLM
    high_text = ""
    for f in real_high[:30]:
        high_text += (
            f"- [{f['severity']}] {f['rule'].split('.')[-1]} in "
            f"{Path(f['file']).name}:{f['line']} — {f['message'][:150]}\n"
        )
    if not high_text:
        high_text = "None\n"

    # Ask LLM to analyze the real findings
    analysis = ""
    if llm_client and real_high:
        try:
            analysis = llm_client.call_tiered(
                messages=[{"role": "user", "content":
                    f"You are Agent-0 analyzing code scan results for project at '{project_path}'.\n\n"
                    f"REAL HIGH-SEVERITY FINDINGS (in application code, NOT backups/third-party):\n{high_text}\n\n"
                    f"For each finding, determine:\n"
                    f"1. Is this a REAL security issue or a false positive?\n"
                    f"   - MD5/SHA1 used for checksums/caching (not security) → FALSE POSITIVE, fix is trivial: add usedforsecurity=False\n"
                    f"   - subprocess shell=True with hardcoded commands → LOW RISK\n"
                    f"   - subprocess shell=True with user input → REAL ISSUE\n"
                    f"   - assert used in production code → LOW RISK (unless in security path)\n"
                    f"2. How hard is the fix? (trivial/moderate/significant)\n"
                    f"3. Priority: FIX NOW / FIX LATER / IGNORE\n\n"
                    f"Format each as:\n"
                    f"### <file>:<line> — <rule>\n"
                    f"**Verdict:** REAL ISSUE / FALSE POSITIVE / LOW RISK\n"
                    f"**Fix:** <what to do>\n"
                    f"**Priority:** FIX NOW / FIX LATER / IGNORE\n"}],
                tier="mid"
            ).get("text", "")
        except Exception as e:
            log.error(f"Audit analysis failed: {e}")
            analysis = f"*LLM analysis failed: {e}*"

    # Build the curated report
    report_lines = [
        f"# Audit Report",
        f"",
        f"**Generated:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Project:** {project_path.name}",
        f"",
        f"## Summary",
        f"",
        f"| Category | Count | Action |",
        f"|----------|-------|--------|",
        f"| Real HIGH findings | {len(real_high)} | Review below |",
        f"| Real MEDIUM/WARNING | {len(real_med)} | Review when time permits |",
        f"| Real LOW | {len(real_low)} | Informational |",
        f"| Backup/archive dirs (noise) | {len(backup_findings)} | Ignored — not running code |",
        f"| Third-party/vendored (noise) | {len(third_party_findings)} | Ignored — not our code |",
        f"| **Total raw findings** | **{results['total']}** | |",
        f"| **Actionable findings** | **{len(real_high) + len(real_med)}** | |",
        f"",
    ]

    # LLM analysis of real findings
    if analysis:
        report_lines.append("## Analysis of HIGH-Severity Findings\n")
        report_lines.append(analysis)
        report_lines.append("")

    # List real HIGH findings
    if real_high:
        report_lines.append("## All HIGH Findings (Application Code)\n")
        for f in real_high:
            fname = Path(f["file"]).name
            report_lines.append(
                f"- **{fname}:{f['line']}** [{f['tool']}] "
                f"{f['rule'].split('.')[-1]}: {f['message'][:120]}"
            )
        report_lines.append("")

    # Summary of medium findings
    if real_med:
        report_lines.append(f"## MEDIUM/WARNING Findings ({len(real_med)} total)\n")
        # Group by rule
        by_rule = {}
        for f in real_med:
            rule = f["rule"].split(".")[-1]
            by_rule[rule] = by_rule.get(rule, 0) + 1
        for rule, count in sorted(by_rule.items(), key=lambda x: -x[1])[:15]:
            report_lines.append(f"- {rule}: {count} occurrences")
        report_lines.append("")

    # Note about noise
    report_lines.append("## Filtered Out (Noise)\n")
    report_lines.append(
        f"**{len(backup_findings)}** findings in backup/archive directories and "
        f"**{len(third_party_findings)}** in third-party/vendored code were excluded "
        f"from this report. These are not part of the running application.\n"
    )
    report_lines.append("*Full raw scan data in scan_results.md*\n")

    report = "\n".join(report_lines)
    store.write("audit_report.md", report, mode="overwrite")
    log.info(
        f"Audit report: {len(real_high)} real HIGH, {len(real_med)} MEDIUM, "
        f"{len(backup_findings)} backup noise, {len(third_party_findings)} third-party noise"
    )

    return report


def _count_by(items, key):
    counts = {}
    for item in items:
        val = item.get(key, "unknown")
        if key == "file":
            val = Path(val).name
        counts[val] = counts.get(val, 0) + 1
    return counts

#!/usr/bin/env python3
"""
Agent-0 Development Setup
Run once to prepare your environment for running or building Agent-0 from source.

Usage:
    python scripts/setup.py
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
VENV = ROOT / "venv"
REQUIREMENTS = ROOT / "backend" / "requirements.txt"


def check(condition, message):
    if not condition:
        print(f"\n  ERROR: {message}")
        sys.exit(1)


def run(cmd, **kwargs):
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\n  FAILED: {' '.join(str(c) for c in cmd)}")
        sys.exit(1)
    return result


def main():
    print("=" * 60)
    print("  Agent-0 Setup")
    print("=" * 60)

    # 1. Python version
    print("\n[1/4] Checking Python version...")
    version = sys.version_info
    check(
        version >= (3, 10),
        f"Python 3.10+ required. You have {version.major}.{version.minor}.\n"
        f"       Download from https://python.org"
    )
    print(f"      Python {version.major}.{version.minor}.{version.micro}  OK")

    # 2. Create virtual environment
    print("\n[2/4] Creating virtual environment...")
    if VENV.exists():
        print("      venv/ already exists — skipping creation")
    else:
        run([sys.executable, "-m", "venv", str(VENV)])
        print("      Created venv/  OK")

    # 3. Install Python dependencies
    print("\n[3/4] Installing Python dependencies...")
    pip = VENV / ("Scripts" if sys.platform == "win32" else "bin") / "pip"
    check(pip.exists(), f"pip not found at {pip}")
    run([str(pip), "install", "--upgrade", "pip"], capture_output=True)
    run([str(pip), "install", "-r", str(REQUIREMENTS)])
    print("      Dependencies installed  OK")

    # 4. Check optional tools
    print("\n[4/4] Checking optional tools (for desktop build)...")

    node = shutil.which("node")
    if node:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"      Node.js {result.stdout.strip()}  OK")
    else:
        print("      Node.js not found — needed only for Tauri desktop build")
        print("      Download from https://nodejs.org")

    cargo = shutil.which("cargo")
    if cargo:
        result = subprocess.run(["cargo", "--version"], capture_output=True, text=True)
        print(f"      {result.stdout.strip()}  OK")
    else:
        print("      Rust/Cargo not found — needed only for Tauri desktop build")
        print("      Install from https://rustup.rs")

    # Done
    python_bin = VENV / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    sep = "\\" if sys.platform == "win32" else "/"

    print("\n" + "=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()
    print("  Run the backend (headless):")
    if sys.platform == "win32":
        print(f"    venv\\Scripts\\python backend\\main.py --project C:\\path\\to\\project")
    else:
        print(f"    ./venv/bin/python backend/main.py --project /path/to/project")
    print()
    print("  Run with Tauri desktop:")
    print("    Terminal 1: (run backend command above with --no-ui flag)")
    print("    Terminal 2: cd desktop && npm install && npx tauri dev")
    print()
    print("  Build standalone .exe:")
    if sys.platform == "win32":
        print("    venv\\Scripts\\pyinstaller backend\\main.py --onefile --name agent0-backend")
        print("    cd desktop && npx tauri build")
    else:
        print("    ./venv/bin/pyinstaller backend/main.py --onefile --name agent0-backend")
        print("    cd desktop && npx tauri build")
    print()


if __name__ == "__main__":
    main()

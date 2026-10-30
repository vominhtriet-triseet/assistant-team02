#!/usr/bin/env python3
"""Check that the development environment is set up correctly.

Run from the repository root:  python scripts/check_env.py
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

OK, FAIL = "[ OK ]", "[FAIL]"
problems = 0


def check(label: str, passed: bool, hint: str = "") -> None:
    global problems
    print(f"{OK if passed else FAIL} {label}")
    if not passed:
        problems += 1
        if hint:
            print(f"       -> {hint}")


root = Path(__file__).resolve().parents[1]
check(f"Python >= 3.10 (found {sys.version.split()[0]})", sys.version_info >= (3, 10), "install Python 3.10+")
in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix) or bool(os.environ.get("VIRTUAL_ENV"))
check("running inside a virtual environment", in_venv, "activate .venv first (see README)")
check("pytest installed", importlib.util.find_spec("pytest") is not None, "pip install -r requirements.txt")
check("git available", shutil.which("git") is not None, "install Git")
check("inside a git repository", (root / ".git").exists(), "clone the repo, or run git init")
check(".gitignore present", (root / ".gitignore").exists(), "restore .gitignore from Git")
readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""
check("README has no TODO left", "TODO" not in readme, "finish the setup instructions in README.md")
if shutil.which("git") and (root / ".git").exists():
    email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True, cwd=root).stdout.strip()
    check(f"git user.email set ({email or 'missing'})", bool(email), "git config --global user.email ...")
try:
    import assistant

    installed = Path(assistant.__file__).resolve().is_relative_to(root / "src")
    check("assistant package installed from this repository", installed, "python -m pip install -e .")
    from assistant.service import process_request

    check("assistant answers an office question", "B.201" in process_request("where is the library?")["message"])
    check("assistant reads a planning request", process_request("essay due Friday")["tasks"] != [])
except Exception as exc:  # noqa: BLE001 - report any import problem
    check("assistant package installed from this repository", False, f"python -m pip install -e .  ({exc!r})")
check("data/offices.csv present", (root / "data" / "offices.csv").exists(), "restore data/offices.csv from Git")
check("chat page present", (root / "ui" / "index.html").exists(), "restore ui/index.html from Git")
print()
print("All good!" if problems == 0 else f"{problems} problem(s) found.")
sys.exit(1 if problems else 0)

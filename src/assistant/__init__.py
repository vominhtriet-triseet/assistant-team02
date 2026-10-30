"""Student Learning Assistant: a planning-first study assistant for CSC10014."""
from __future__ import annotations

import os
from pathlib import Path

__version__ = "0.2.0"

# The package is installed in editable mode from the repository, so data and UI
# files are read from the repository root. ASSISTANT_DATA_DIR overrides the data path.
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("ASSISTANT_DATA_DIR", REPO_ROOT / "data"))
UI_DIR = REPO_ROOT / "ui"

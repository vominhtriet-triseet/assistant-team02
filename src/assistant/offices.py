"""Office lookup from data/offices.csv, including partial names."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from assistant import DATA_DIR

# Words that appear in many office names and say nothing about which one is meant.
STOPWORDS = {
    "office", "of", "the", "service", "campus", "and", "where", "is", "when", "does", "do",
    "open", "it", "a", "an", "at", "in", "to", "what", "time", "room", "hours", "how", "i", "find",
}

Office = dict[str, str]


def load_offices(path: Path | None = None) -> list[Office]:
    path = path or DATA_DIR / "offices.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


def find_offices(text: str, offices: list[Office]) -> list[Office]:
    """Return the best matching offices; more than one result means the query is ambiguous."""
    query = _words(text)
    scored = [(len(query & _words(o["name"])), o) for o in offices]
    best = max((s for s, _ in scored), default=0)
    if best == 0:
        return []
    candidates = [o for s, o in scored if s == best]
    # Among equally good matches, a name written out in full ("the library") is the one meant.
    exact = [o for o in candidates if o["name"].lower() in text.lower()]
    return [max(exact, key=lambda o: len(o["name"]))] if exact else candidates


def describe(office: Office) -> str:
    if office["room"].lower().startswith("not listed"):
        return f"{office['name']}: the room and opening hours are not published."
    return f"{office['name']}: room {office['room']}, open {office['hours']}."


def answer(text: str, offices: list[Office] | None = None) -> str | None:
    """Answer an office question, or return None when no office matches."""
    matches = find_offices(text, offices if offices is not None else load_offices())
    if not matches:
        return None
    if len(matches) == 1:
        return describe(matches[0])
    names = "\n".join(f"- {o['name']}" for o in matches)
    return f"Several offices match. Which one do you mean?\n{names}"

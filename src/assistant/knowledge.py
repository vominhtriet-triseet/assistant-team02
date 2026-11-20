"""Feature 2, knowledge management: save, search, list, link, and delete the student's own notes.

Search is accent-insensitive word overlap ("giai tich" finds "Giải tích"). Sources are
only what the student supplied: a link they pasted, or "your note #3". Nothing is invented.
"""
from __future__ import annotations

import re
import unicodedata

from assistant.i18n import t
from assistant.planning.models import Note

SAVE_RE = re.compile(
    r"^(?:save|add|lưu|ghi)(?:\s+(?:a|an|lại|một))?\s+(?P<kind>note|link|ghi chú|liên kết)\s*[:\-]?\s*(?P<body>.+)$",
    re.I | re.S,
)
LIST_RE = re.compile(
    r"^(?:(?:show|list)(?: me)?(?: my| all)? notes|my notes"
    r"|(?:xem|liệt kê|danh sách)(?: tất cả)?(?: các)? ghi chú(?: của (?:tôi|mình|em))?|ghi chú của (?:tôi|mình|em))$"
)
SEARCH_RE = re.compile(
    r"^(?:(?:find|search)(?: my)? notes?(?: about| for| on| tagged)?|notes? (?:about|on|tagged)"
    r"|tìm(?: kiếm)? ghi chú(?: về| có tag)?)\s+(?P<q>.+)$"
    r"|^(?:find|search|tìm)\s+(?P<tag>#[\w-]+)$"  # "find the library" stays an office question
)
LINK_RE = re.compile(
    r"^(?:link|connect|attach) note (?P<note>\d+) (?:to|with) (?:task )?(?P<task>.+)$"
    r"|^(?:gắn|liên kết|nối) ghi chú (?P<note2>\d+) (?:với|vào) (?:task |việc |công việc )?(?P<task2>.+)$"
)
DELETE_RE = re.compile(r"^(?:delete|remove) note (?P<id>\d+)$|^xóa ghi chú (?P<id2>\d+)$")
URL_RE = re.compile(r"https?://[^\s<>\"]+", re.I)
TAG_RE = re.compile(r"#([\w-]+)")
STOP = {"the", "a", "an", "of", "and", "to", "in", "on", "for", "is", "about", "my", "note", "notes",
        "ve", "cua", "va", "la", "cac", "nhung", "mot", "ghi", "chu", "toi", "minh"}
MAX_TITLE, MAX_CONTENT = 120, 4000


def fold(text: str) -> str:
    """Lowercase and drop Vietnamese accents so 'Giải tích' and 'giai tich' compare equal."""
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", fold(text))) - STOP


def parse_note(body: str, kind: str) -> Note | None:
    """'Title - content #tag https://...' -> Note. Returns None when nothing usable is left."""
    tags = list(dict.fromkeys(tag.lower() for tag in TAG_RE.findall(body)))
    body = TAG_RE.sub(" ", body)
    url = URL_RE.search(body)
    source_url = url.group(0).rstrip(".,)") if url else None
    body = URL_RE.sub(" ", body).strip(" -:|\n\t")
    parts = re.split(r"\s+-\s+|:\s+|\s+\|\s+|\n", body, maxsplit=1)
    title, content = parts if len(parts) == 2 else (" ".join(body.split()[:8]), body)
    title, content = title.strip(), content.strip()
    if not title and source_url:
        title = re.sub(r"^https?://(?:www\.)?", "", source_url)[:60]
    if not title:
        return None
    if kind in ("link", "liên kết") and not source_url:
        return None
    return Note(title=title[:MAX_TITLE], content=content[:MAX_CONTENT], source_url=source_url, tags=tags)


def search(notes: list[Note], query: str) -> list[Note]:
    """Notes ranked by overlap with the query; '#tag' searches tags only."""
    query = query.strip()
    if query.startswith("#"):
        tag = query[1:].lower()
        return [n for n in notes if tag in n.tags]
    wanted = words(query)
    scored = []
    for note in notes:
        score = 2 * len(wanted & words(note.title)) + 2 * len(wanted & {fold(tag) for tag in note.tags})
        score += len(wanted & words(note.content))
        if score:
            scored.append((score, note.id, note))
    return [note for _, _, note in sorted(scored, key=lambda item: (-item[0], item[1]))]


def describe(note: Note, lang: str) -> str:
    line = f"#{note.id} {note.title}"
    if note.tags:
        line += " " + " ".join(f"#{tag}" for tag in note.tags)
    source = note.source_url or t(lang, "your note #{id}", id=note.id)
    return line + "\n   " + t(lang, "Source: {source}", source=source)


def citations(notes: list[Note]) -> list[dict]:
    """Only what the student supplied: their link, or None for their own note."""
    return [{"note_id": n.id, "title": n.title, "source_url": n.source_url} for n in notes]


if __name__ == "__main__":
    note = parse_note("Giải tích: đạo hàm của x^2 là 2x #toan https://example.edu/calc", "note")
    assert note and note.title == "Giải tích" and note.tags == ["toan"] and note.source_url == "https://example.edu/calc"
    note.id = 1
    assert search([note], "giai tich") == [note] and search([note], "#toan") == [note] and search([note], "physics") == []
    print("ok")

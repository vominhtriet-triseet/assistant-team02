"""SQLite storage for one Session per AssistantContext, using the 8 tables of the report's data model.

Every record belongs to a context, and ids are numbered per context ("note 3" means the
student's third note), so child tables use (context_id, id) keys and cascade on delete.
save() rewrites one context in a single transaction.
ponytail: delete-and-reinsert per request, fine for one student's handful of rows; switch to row diffs if contexts grow large.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from assistant.planning.models import Note, Study, Task
from assistant.service import Session

SCHEMA = """
CREATE TABLE IF NOT EXISTS contexts (                 -- AssistantContext
    context_id    TEXT PRIMARY KEY,
    user_goal     TEXT NOT NULL DEFAULT '',
    next_actions  TEXT NOT NULL DEFAULT '[]',         -- JSON list
    lang          TEXT NOT NULL DEFAULT 'en' CHECK (lang IN ('en', 'vi')),
    availability  TEXT NOT NULL DEFAULT '{}',         -- JSON {weekday: hours}
    blocked       TEXT NOT NULL DEFAULT '[]',         -- JSON list of weekdays
    awaiting      TEXT,
    assumptions   TEXT NOT NULL DEFAULT '[]',
    next_task_id  INTEGER NOT NULL DEFAULT 1,
    next_item_id  INTEGER NOT NULL DEFAULT 1,
    next_session_id INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tasks (
    context_id    TEXT NOT NULL REFERENCES contexts(context_id) ON DELETE CASCADE,
    task_id       INTEGER NOT NULL,
    title         TEXT NOT NULL,
    kind          TEXT NOT NULL,
    deadline      TEXT,                               -- ISO date
    deadline_time TEXT,                               -- HH:MM
    duration_min  INTEGER NOT NULL CHECK (duration_min > 0),
    duration_assumed INTEGER NOT NULL CHECK (duration_assumed IN (0, 1)),
    priority      TEXT NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
    priority_reason TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL CHECK (status IN ('pending', 'done')),
    source        TEXT NOT NULL CHECK (source IN ('user', 'llm', 'system')),
    PRIMARY KEY (context_id, task_id)
);
CREATE TABLE IF NOT EXISTS schedule_blocks (
    context_id    TEXT NOT NULL,
    block_id      INTEGER NOT NULL,
    task_id       INTEGER NOT NULL,
    day           TEXT NOT NULL,                      -- ISO date; the scheduler plans hours per day
    hours         REAL NOT NULL CHECK (hours >= 0),
    status        TEXT NOT NULL CHECK (status IN ('proposed', 'deadline')),
    assumption    TEXT,
    PRIMARY KEY (context_id, block_id),
    FOREIGN KEY (context_id, task_id) REFERENCES tasks(context_id, task_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS task_dependencies (
    context_id    TEXT NOT NULL,
    task_id       INTEGER NOT NULL,
    depends_on_id INTEGER NOT NULL CHECK (depends_on_id <> task_id),
    PRIMARY KEY (context_id, task_id, depends_on_id),
    FOREIGN KEY (context_id, task_id) REFERENCES tasks(context_id, task_id) ON DELETE CASCADE,
    FOREIGN KEY (context_id, depends_on_id) REFERENCES tasks(context_id, task_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS knowledge_items (
    context_id    TEXT NOT NULL REFERENCES contexts(context_id) ON DELETE CASCADE,
    item_id       INTEGER NOT NULL,
    title         TEXT NOT NULL,
    content       TEXT NOT NULL DEFAULT '',
    source_url    TEXT,
    tags          TEXT NOT NULL DEFAULT '[]',         -- JSON list
    created_at    TEXT NOT NULL,
    PRIMARY KEY (context_id, item_id)
);
CREATE TABLE IF NOT EXISTS task_knowledge (
    context_id    TEXT NOT NULL,
    task_id       INTEGER NOT NULL,
    item_id       INTEGER NOT NULL,
    PRIMARY KEY (context_id, task_id, item_id),
    FOREIGN KEY (context_id, task_id) REFERENCES tasks(context_id, task_id) ON DELETE CASCADE,
    FOREIGN KEY (context_id, item_id) REFERENCES knowledge_items(context_id, item_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS study_sessions (
    context_id    TEXT NOT NULL REFERENCES contexts(context_id) ON DELETE CASCADE,
    session_id    INTEGER NOT NULL,
    topic         TEXT NOT NULL,
    progress      TEXT NOT NULL,                      -- "correct/total"
    questions     TEXT NOT NULL DEFAULT '[]',         -- JSON list of {question, answer, correct}
    current       INTEGER NOT NULL DEFAULT 0,
    review_notes  TEXT NOT NULL DEFAULT '',
    review_due    TEXT,
    started_at    TEXT NOT NULL,
    PRIMARY KEY (context_id, session_id)
);
CREATE TABLE IF NOT EXISTS study_session_items (
    context_id    TEXT NOT NULL,
    session_id    INTEGER NOT NULL,
    item_id       INTEGER NOT NULL,
    PRIMARY KEY (context_id, session_id, item_id),
    FOREIGN KEY (context_id, session_id) REFERENCES study_sessions(context_id, session_id) ON DELETE CASCADE,
    FOREIGN KEY (context_id, item_id) REFERENCES knowledge_items(context_id, item_id) ON DELETE CASCADE
);
"""
TABLES = ("contexts", "tasks", "schedule_blocks", "task_dependencies",
          "knowledge_items", "task_knowledge", "study_sessions", "study_session_items")


BUSY_TIMEOUT = 10  # seconds a connection waits for the write lock
_ready: set[str] = set()  # database files whose schema and WAL mode are already set up in this process


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # per connection
    if str(path) == ":memory:" or str(path) not in _ready:
        # Profiling showed this took 40% of each request when run on every connection.
        if str(path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")  # stored in the file: readers don't wait for the writer
            _ready.add(str(path))
        conn.executescript(SCHEMA)
    return conn


def _day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def load(conn: sqlite3.Connection, context_id: str) -> Session | None:
    row = conn.execute("SELECT * FROM contexts WHERE context_id = ?", (context_id,)).fetchone()
    if row is None:
        return None
    rows = lambda sql: conn.execute(sql, (context_id,)).fetchall()  # noqa: E731
    session = Session(
        lang=row["lang"], user_goal=row["user_goal"], next_actions=json.loads(row["next_actions"]),
        availability={int(k): v for k, v in json.loads(row["availability"]).items()},
        blocked=set(json.loads(row["blocked"])), awaiting=row["awaiting"], assumptions=json.loads(row["assumptions"]),
        next_id=row["next_task_id"], next_note_id=row["next_item_id"], next_study_id=row["next_session_id"],
    )
    session.tasks = [
        Task(id=r["task_id"], title=r["title"], kind=r["kind"], deadline=_day(r["deadline"]), deadline_time=r["deadline_time"],
             hours=r["duration_min"] / 60, hours_assumed=bool(r["duration_assumed"]), priority=r["priority"],
             priority_reason=r["priority_reason"], status=r["status"], source=r["source"])
        for r in rows("SELECT * FROM tasks WHERE context_id = ? ORDER BY task_id")
    ]
    session.dependencies = {(r["task_id"], r["depends_on_id"]) for r in rows("SELECT * FROM task_dependencies WHERE context_id = ?")}
    session.notes = [
        Note(id=r["item_id"], title=r["title"], content=r["content"], source_url=r["source_url"],
             tags=json.loads(r["tags"]), created_at=r["created_at"])
        for r in rows("SELECT * FROM knowledge_items WHERE context_id = ? ORDER BY item_id")
    ]
    session.links = {(r["task_id"], r["item_id"]) for r in rows("SELECT * FROM task_knowledge WHERE context_id = ?")}
    items: dict[int, list[int]] = {}
    for r in rows("SELECT * FROM study_session_items WHERE context_id = ? ORDER BY item_id"):
        items.setdefault(r["session_id"], []).append(r["item_id"])
    session.studies = [
        Study(id=r["session_id"], topic=r["topic"], item_ids=items.get(r["session_id"], []), questions=json.loads(r["questions"]),
              current=r["current"], review_notes=r["review_notes"], review_due=_day(r["review_due"]), started_at=r["started_at"])
        for r in rows("SELECT * FROM study_sessions WHERE context_id = ? ORDER BY session_id")
    ]
    by_day: dict[str, list[dict]] = {}
    for r in rows("SELECT b.*, t.title FROM schedule_blocks b JOIN tasks t USING (context_id, task_id) "
                  "WHERE b.context_id = ? ORDER BY b.block_id"):
        by_day.setdefault(r["day"], []).append(
            {"task_id": r["task_id"], "title": r["title"], "hours": r["hours"], "event": r["status"] == "deadline"})
    session.schedule = [{"date": d, "blocks": b} for d, b in by_day.items()]
    return session


def save(conn: sqlite3.Connection, context_id: str, session: Session) -> None:
    """Write the whole context in one transaction."""
    cid = context_id
    task_ids = {task.id for task in session.tasks}
    note_ids = {note.id for note in session.notes}
    with conn:
        conn.execute(
            "INSERT INTO contexts (context_id, user_goal, next_actions, lang, availability, blocked, awaiting, assumptions,"
            " next_task_id, next_item_id, next_session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (context_id) DO UPDATE SET user_goal = excluded.user_goal, next_actions = excluded.next_actions,"
            " lang = excluded.lang, availability = excluded.availability, blocked = excluded.blocked,"
            " awaiting = excluded.awaiting, assumptions = excluded.assumptions, next_task_id = excluded.next_task_id,"
            " next_item_id = excluded.next_item_id, next_session_id = excluded.next_session_id, updated_at = CURRENT_TIMESTAMP",
            (cid, session.user_goal, json.dumps(session.next_actions, ensure_ascii=False), session.lang,
             json.dumps(session.availability), json.dumps(sorted(session.blocked)), session.awaiting,
             json.dumps(session.assumptions, ensure_ascii=False), session.next_id, session.next_note_id, session.next_study_id),
        )
        for table in ("tasks", "knowledge_items", "study_sessions"):  # cascades to the other five tables
            conn.execute(f"DELETE FROM {table} WHERE context_id = ?", (cid,))
        conn.executemany(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(cid, t.id, t.title, t.kind, t.deadline.isoformat() if t.deadline else None, t.deadline_time,
              max(1, round(t.hours * 60)), int(t.hours_assumed), t.priority, t.priority_reason, t.status, t.source)
             for t in session.tasks],
        )
        conn.executemany(
            "INSERT INTO task_dependencies VALUES (?, ?, ?)",
            [(cid, a, b) for a, b in session.dependencies if a in task_ids and b in task_ids],
        )
        blocks = [(d["date"], b) for d in session.schedule for b in d["blocks"] if b["task_id"] in task_ids]
        conn.executemany(
            "INSERT INTO schedule_blocks VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(cid, i, b["task_id"], day, b["hours"], "deadline" if b["event"] else "proposed", None)
             for i, (day, b) in enumerate(blocks, start=1)],
        )
        conn.executemany(
            "INSERT INTO knowledge_items VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(cid, n.id, n.title, n.content, n.source_url, json.dumps(n.tags, ensure_ascii=False), n.created_at)
             for n in session.notes],
        )
        conn.executemany(
            "INSERT INTO task_knowledge VALUES (?, ?, ?)",
            [(cid, a, b) for a, b in session.links if a in task_ids and b in note_ids],
        )
        conn.executemany(
            "INSERT INTO study_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(cid, s.id, s.topic, s.progress(), json.dumps(s.questions, ensure_ascii=False), s.current, s.review_notes,
              s.review_due.isoformat() if s.review_due else None, s.started_at) for s in session.studies],
        )
        conn.executemany(
            "INSERT INTO study_session_items VALUES (?, ?, ?)",
            [(cid, s.id, item) for s in session.studies for item in s.item_ids if item in note_ids],
        )


def delete(conn: sqlite3.Connection, context_id: str) -> None:
    with conn:
        conn.execute("DELETE FROM contexts WHERE context_id = ?", (context_id,))

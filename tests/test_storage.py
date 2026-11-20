import sqlite3

import pytest

from assistant import storage
from assistant.service import Session, process_request


@pytest.fixture
def conn():
    connection = storage.connect(":memory:")
    yield connection
    connection.close()


def full_session(today) -> Session:
    session = Session()
    for message in [
        "essay due Friday and a midterm next Wednesday",
        "3 hours on weekdays, busy on Saturday",
        "do the midterm after the essay",
        "save note: Photosynthesis - Photosynthesis turns light energy into chemical energy in chloroplasts. #bio https://example.edu/photo",
        "link note 1 to essay",
        "quiz me on photosynthesis",
        "chloroplasts",
        "add review to plan",
    ]:
        process_request(message, session, today=today)
    return session


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_all_eight_tables_exist(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert set(storage.TABLES) <= names and len(storage.TABLES) == 8


def test_round_trip_keeps_every_record(conn, today):
    session = full_session(today)
    storage.save(conn, "c1", session)
    for table in storage.TABLES:
        assert count(conn, table) > 0, table
    loaded = storage.load(conn, "c1")
    assert [t.to_dict() for t in loaded.tasks] == [t.to_dict() for t in session.tasks]
    assert [n.to_dict() for n in loaded.notes] == [n.to_dict() for n in session.notes]
    assert [s.to_dict() for s in loaded.studies] == [s.to_dict() for s in session.studies]
    assert loaded.dependencies == session.dependencies and loaded.links == session.links
    assert loaded.availability == session.availability and loaded.blocked == session.blocked
    # The loaded session keeps working: the next message replans with the stored data.
    assert process_request("show my plan", loaded, today=today)["schedule"]


def test_saving_twice_does_not_duplicate(conn, today):
    session = full_session(today)
    storage.save(conn, "c1", session)
    storage.save(conn, "c1", session)
    assert count(conn, "tasks") == len(session.tasks) and count(conn, "contexts") == 1


def test_deleting_a_context_cascades(conn, today):
    storage.save(conn, "c1", full_session(today))
    storage.delete(conn, "c1")
    assert all(count(conn, table) == 0 for table in storage.TABLES)


def test_database_rejects_invalid_rows(conn, today):
    storage.save(conn, "c1", full_session(today))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO task_dependencies VALUES ('c1', 1, 1)")  # a task cannot depend on itself
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO task_knowledge VALUES ('c1', 99, 1)")  # unknown task


def test_unknown_context_loads_as_none(conn):
    assert storage.load(conn, "missing") is None

"""Integration tests: two or more components working together (IT-01 .. IT-07).

Each test name starts with its ID so the evaluation report can cite it.
"""
import json
import threading
import urllib.error
import urllib.request
from contextlib import closing

import pytest

from assistant import llm, storage
from assistant.server import make_server
from assistant.service import Session, process_request


@pytest.fixture
def server(tmp_path):
    db = str(tmp_path / "it.db")
    srv = make_server("127.0.0.1", 0, db_path=db)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", db
    srv.shutdown()
    srv.server_close()


def post(base, path, payload):
    req = urllib.request.Request(base + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def stored(db, session_id):
    with closing(storage.connect(db)) as conn:
        return storage.load(conn, session_id)


def test_IT01_api_passes_the_message_to_the_service(server):
    base, _ = server
    status, body = post(base, "/api/chat", {"message": "essay due Friday, 3 hours"})
    assert status == 200 and body["intent"] == "clarification"
    assert [t["title"] for t in body["tasks"]] == ["Essay"] and body["tasks"][0]["hours"] == 3


def test_IT02_service_result_is_saved_in_storage(server):
    base, db = server
    _, body = post(base, "/api/chat", {"message": "essay due Friday, 3 hours. 2 hours a day."})
    session = stored(db, body["session_id"])
    assert [t.to_dict() for t in session.tasks] == body["tasks"]
    assert session.availability == {d: 2.0 for d in range(7)}


def test_IT03_storage_carries_the_conversation_between_requests(server):
    base, _ = server
    _, first = post(base, "/api/chat", {"message": "essay due Friday"})
    _, second = post(base, "/api/chat", {"message": "2 hours", "session_id": first["session_id"]})
    assert first["intent"] == "clarification" and second["intent"] == "planning" and second["schedule"]


def test_IT04_task_update_reaches_scheduler_and_stored_blocks(server):
    base, db = server
    _, body = post(base, "/api/chat", {"message": "essay due Friday, 3 hours, and slides due Friday, 2 hours. 2 hours a day."})
    sid = body["session_id"]
    post(base, "/api/chat", {"message": "mark essay as done", "session_id": sid})
    with closing(storage.connect(db)) as conn:
        rows = conn.execute("SELECT t.title, b.status FROM schedule_blocks b JOIN tasks t USING (context_id, task_id) "
                            "WHERE b.context_id = ?", (sid,)).fetchall()
    assert rows and all(title != "Essay" or status == "deadline" for title, status in rows)


def test_IT05_a_failing_request_does_not_change_stored_data(server, monkeypatch):
    base, db = server
    _, body = post(base, "/api/chat", {"message": "essay due Friday, 3 hours"})
    before = [t.to_dict() for t in stored(db, body["session_id"]).tasks]

    def boom(*args, **kwargs):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr("assistant.server.process_request", boom)
    status, err = post(base, "/api/chat", {"message": "slides due Monday", "session_id": body["session_id"]})
    assert status == 500 and "simulated" not in err["error"]  # no internals leaked
    assert [t.to_dict() for t in stored(db, body["session_id"]).tasks] == before


class FailingProvider:
    name = "fake"

    def complete_json(self, system, user, timeout=60):
        raise llm.LLMError("offline")


def test_IT06_model_failure_falls_back_to_rules_without_losing_data(today):
    session = Session()
    process_request("essay due Friday", session, today=today)
    response = process_request("plan the stuff for my physics class", session, today=today, provider=FailingProvider())
    assert "unavailable" in response["warnings"][0] and [t["title"] for t in response["tasks"]] == ["Essay"]


def test_IT07_note_quiz_and_review_task_are_linked_in_storage(today):
    session = Session()
    for message in ["save note: Photosynthesis - Photosynthesis turns light energy into chemical energy in chloroplasts.",
                    "quiz me on photosynthesis", "chloroplasts", "add review to plan"]:
        process_request(message, session, today=today)
    with closing(storage.connect(":memory:")) as conn:
        storage.save(conn, "c", session)
        links = conn.execute("SELECT task_id, item_id FROM task_knowledge").fetchall()
        items = conn.execute("SELECT session_id, item_id FROM study_session_items").fetchall()
    assert [tuple(r) for r in links] == [(1, 1)] and [tuple(r) for r in items] == [(1, 1)]

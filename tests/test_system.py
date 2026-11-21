"""System tests: the whole application end to end over HTTP with SQLite (ST-01 .. ST-07).

Dates are relative ("in 5 days"), so these run on any day.
"""
import json
import threading
import urllib.request
from datetime import date, timedelta

import pytest

from assistant.server import make_server


def start(db):
    srv = make_server("127.0.0.1", 0, db_path=db)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


@pytest.fixture
def app(tmp_path):
    db = str(tmp_path / "st.db")
    srv, base = start(db)
    yield base, db
    srv.shutdown()
    srv.server_close()


def chat(base, message, sid=None):
    req = urllib.request.Request(base + "/api/chat", json.dumps({"message": message, "session_id": sid}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def work_days(body, title):
    return [d["date"] for d in body["schedule"] or [] for b in d["blocks"] if b["title"] == title and not b["event"]]


def test_ST01_new_task_appears_in_the_plan(app):
    base, _ = app
    body = chat(base, "Essay due in 5 days, 4 hours. 2 hours every day.")
    assert body["intent"] == "planning" and work_days(body, "Essay") and body["warnings"] == []


def test_ST02_earlier_deadline_reschedules_the_task(app):
    base, _ = app
    first = chat(base, "Essay due in 6 days, 4 hours. 2 hours every day.")
    second = chat(base, "Essay due tomorrow", first["session_id"])
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert second["tasks"][0]["deadline"] == tomorrow and max(work_days(second, "Essay")) <= tomorrow


def test_ST03_finished_task_is_no_longer_scheduled(app):
    base, _ = app
    first = chat(base, "Essay due in 5 days, 3 hours, and slides due in 5 days, 2 hours. 2 hours every day.")
    second = chat(base, "mark essay as done", first["session_id"])
    assert work_days(second, "Essay") == [] and work_days(second, "Slides")


def test_ST04_missing_information_gets_a_question_not_a_plan(app):
    base, _ = app
    body = chat(base, "I have an essay due in 5 days")
    assert body["intent"] == "clarification" and body["schedule"] is None and "how many hours" in body["message"]


def test_ST05_infeasible_plan_is_warned_not_forced(app):
    base, _ = app
    body = chat(base, "Final exam tomorrow and I can study 2 hours a day")
    assert body["warnings"] and sum(b["hours"] for d in body["schedule"] for b in d["blocks"] if not b["event"]) <= 2


def test_ST06_data_survives_a_server_restart(tmp_path):
    db = str(tmp_path / "restart.db")
    srv, base = start(db)
    sid = chat(base, "Essay due in 5 days, 3 hours. 2 hours every day.")["session_id"]
    srv.shutdown()
    srv.server_close()
    srv, base = start(db)
    try:
        assert [t["title"] for t in chat(base, "show my plan", sid)["tasks"]] == ["Essay"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_ST07_vietnamese_conversation_end_to_end(app):
    base, _ = app
    first = chat(base, "Tôi có bài tập giải tích hạn 5 ngày nữa")
    second = chat(base, "Mỗi ngày tôi học được 2 tiếng", first["session_id"])
    assert first["lang"] == "vi" and "mấy tiếng" in first["message"]
    assert second["intent"] == "planning" and second["message"].startswith("Đây là lịch nháp")

import pytest

from assistant import llm
from assistant.service import process_request

REQUEST = "I have a calculus problem set due Friday and a Data Structures midterm next Wednesday. Can you help me plan this week?"


@pytest.mark.parametrize("bad", ["", "   ", None, 42])
def test_invalid_input_raises(bad, session):
    with pytest.raises(ValueError):
        process_request(bad, session)


def test_response_keeps_the_documented_fields(session, today):
    response = process_request("hello", session, today=today)
    for key in ("tasks", "priorities", "schedule", "message"):
        assert key in response
    assert response["intent"] == "greeting"


def test_help_lists_capabilities(session, today):
    response = process_request("HELP", session, today=today)
    assert response["intent"] == "help" and "Plan" in response["message"]


def test_office_question(session, today):
    assert process_request("Where is the IT helpdesk?", session, today=today)["message"].startswith("IT Helpdesk")


def test_unknown_request_falls_back(session, today):
    response = process_request("what is the weather", session, today=today)
    assert response["intent"] == "fallback" and response["tasks"] == [] and response["schedule"] is None


def test_planning_conversation(session, today):
    first = process_request(REQUEST, session, today=today)
    assert first["intent"] == "clarification"
    assert first["schedule"] is None and len(first["tasks"]) == 2
    assert "2 hours" in first["suggestions"]

    second = process_request("About 3 hours on weekdays. I'm busy all Saturday.", session, today=today)
    assert second["intent"] == "planning"
    assert second["schedule"][0]["date"] == "2026-10-26"
    assert any("Not enough time for Prepare for Data Structures midterm" in w for w in second["warnings"])
    assert "Busy on Sat" in second["facts"]
    assert any("takes about 8 h" in a for a in second["assumptions"])

    done = process_request("mark calculus problem set as done", session, today=today)
    assert done["message"].startswith('Marked "Calculus problem set" as done')
    assert [t["status"] for t in done["tasks"]] == ["done", "pending"]


def test_chip_answer_to_clarification(session, today):
    process_request("essay due Friday", session, today=today)
    response = process_request("2 hours", session, today=today)
    assert response["intent"] == "planning" and response["schedule"]


def test_reset_clears_the_plan(session, today):
    process_request("essay due Friday", session, today=today)
    assert process_request("reset", session, today=today)["tasks"] == []


def test_repeated_task_is_merged(session, today):
    process_request("essay due Friday", session, today=today)
    response = process_request("essay due Thursday, about 2 hours", session, today=today)
    assert len(response["tasks"]) == 1
    assert response["tasks"][0]["deadline"] == "2026-10-29" and response["tasks"][0]["hours"] == 2


class FakeProvider:
    name = "fake"

    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error

    def complete_json(self, system, user, timeout=60):
        if self.error:
            raise llm.LLMError(self.error)
        return self.reply


def test_language_model_output_is_validated(session, today):
    reply = {"tasks": [
        {"title": "Physics lab write-up", "kind": "assignment", "deadline": "2026-10-29", "hours": 3},
        {"title": "", "deadline": "soon"},
        {"title": "Group meeting prep", "kind": "nonsense", "deadline": "not a date", "hours": 500},
    ], "hours_per_day": 2}
    response = process_request("plan the stuff for my physics class", session, today=today, provider=FakeProvider(reply))
    titles = [t["title"] for t in response["tasks"]]
    assert titles == ["Physics lab write-up", "Group meeting prep"]
    assert response["tasks"][1]["deadline"] is None and response["tasks"][1]["hours_assumed"]
    assert any("fake language model" in a for a in response["assumptions"])


def test_language_model_failure_falls_back(session, today):
    response = process_request("plan the stuff for my physics class", session, today=today, provider=FakeProvider(error="offline"))
    assert response["intent"] == "fallback"
    assert "AI service is unavailable" in response["warnings"][0]


def test_rules_are_used_before_the_language_model(session, today):
    provider = FakeProvider(error="should not be called")
    response = process_request("essay due Friday", session, today=today, provider=provider)
    assert response["tasks"][0]["title"] == "Essay" and response["warnings"] == []

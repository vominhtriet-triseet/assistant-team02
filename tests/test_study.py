from assistant import llm
from assistant.service import process_request

NOTE = ("save note: Photosynthesis - Photosynthesis turns light energy into chemical energy in chloroplasts. "
        "It releases oxygen as a by-product.")


def test_quiz_feedback_and_review_task(session, today):
    process_request(NOTE, session, today=today)
    first = process_request("quiz me on photosynthesis", session, today=today)
    assert first["intent"] == "study" and "Question 1/2" in first["message"] and "_____" in first["message"]
    assert first["citations"][0]["note_id"] == 1

    second = process_request("chloroplasts", session, today=today)
    assert second["message"].startswith("Correct!") and "Question 2/2" in second["message"]

    done = process_request("skip", session, today=today)
    assert done["message"].startswith("Not quite. The answer is: product.")
    assert done["study"]["progress"] == "1/2" and done["study"]["review_due"] == "2026-10-27"  # under 60% -> review tomorrow
    assert "add review to plan" in done["suggestions"]

    added = process_request("add review to plan", session, today=today)
    review = added["tasks"][-1]
    assert review["title"] == "Review Photosynthesis" and review["source"] == "system" and review["deadline"] == "2026-10-27"
    assert (review["id"], 1) in session.links


def test_quiz_can_be_stopped(session, today):
    process_request(NOTE, session, today=today)
    process_request("study note 1", session, today=today)
    stopped = process_request("stop", session, today=today)
    assert stopped["message"].startswith("Quiz stopped") and session.awaiting is None


def test_no_material_asks_for_a_note(session, today):
    response = process_request("quiz me on thermodynamics", session, today=today)
    assert response["intent"] == "clarification" and "Save a note first" in response["message"]


def test_study_with_a_date_is_still_a_planning_task(session, today):
    response = process_request("study chapter 3 tomorrow for 2 hours", session, today=today)
    assert response["intent"] == "clarification" and response["tasks"][0]["hours"] == 2


def test_vietnamese_quiz(session, today):
    process_request("lưu ghi chú: Quang hợp - Quang hợp diễn ra trong lục lạp của tế bào thực vật.", session, today=today)
    first = process_request("kiểm tra tôi về quang hợp", session, today=today)
    assert first["lang"] == "vi" and "Câu 1/1: Quang hợp diễn ra trong lục lạp của tế bào _____." in first["message"]
    done = process_request("thuc vat", session, today=today)  # accents optional
    assert done["message"].startswith("Chính xác!") and "Thêm việc ôn tập" in done["message"]


class FakeProvider:
    name = "fake"

    def __init__(self, replies):
        self.replies = list(replies)

    def complete_json(self, system, user, timeout=60):
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_model_questions_are_validated_and_graded(session, today):
    process_request(NOTE, session, today=today)
    provider = FakeProvider([
        {"summary": "Plants make sugar from light.", "questions": [
            {"question": "Where does photosynthesis happen?", "answer": "In chloroplasts"},
            {"question": "", "answer": "dropped"}, {"question": 5, "answer": "dropped"}, "nonsense"]},
        {"correct": True, "feedback": "Right, chloroplasts."},
    ])
    first = process_request("quiz me on photosynthesis", session, today=today, provider=provider)
    assert "Plants make sugar" in first["message"] and first["study"]["question_count"] == 1
    assert any("fake model" in a for a in first["assumptions"])
    done = process_request("the chloroplast", session, today=today, provider=provider)
    assert done["message"].startswith("Right, chloroplasts.") and done["study"]["progress"] == "1/1"


def test_model_failure_falls_back_to_note_questions(session, today):
    process_request(NOTE, session, today=today)
    provider = FakeProvider([llm.LLMError("offline")])
    first = process_request("quiz me on photosynthesis", session, today=today, provider=provider)
    assert first["intent"] == "study" and "_____" in first["message"] and "unavailable" in first["warnings"][0]

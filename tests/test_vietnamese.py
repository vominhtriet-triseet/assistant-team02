import re
from datetime import date
from pathlib import Path

from assistant import i18n
from assistant.planning.parser import parse
from assistant.service import process_request


def test_detect_language():
    assert i18n.detect("Thư viện ở đâu?") == "vi"
    assert i18n.detect("where is the library") == "en"
    assert i18n.detect("3", previous="vi") == "vi"


def test_vietnamese_tasks_dates_and_durations(today):
    result = parse("Tôi có bài tập giải tích hạn thứ 6 và thi giữa kỳ Cấu trúc dữ liệu thứ 4 tuần sau", today, lang="vi")
    assert [(t.title, t.kind, t.deadline) for t in result.tasks] == [
        ("Bài tập giải tích", "assignment", date(2026, 10, 30)),
        ("Ôn tập: Thi giữa kỳ Cấu trúc dữ liệu", "exam", date(2026, 11, 4)),  # "tuần sau" = next calendar week
    ]


def test_vietnamese_time_duration_priority(today):
    task = parse("nộp báo cáo vật lý lúc 5 giờ chiều mai, mất khoảng 2 tiếng, gấp", today, lang="vi").tasks[0]
    assert (task.title, task.deadline, task.deadline_time, task.hours, task.priority) == (
        "Báo cáo vật lý", date(2026, 10, 27), "17:00", 2.0, "high")
    assert parse("đồ án không gấp hạn 17h30 thứ 5", today, lang="vi").tasks[0].priority == "low"


def test_vietnamese_availability(today):
    result = parse("Mỗi ngày tôi học được 3 tiếng, thứ 7 bận", today, lang="vi")
    assert result.availability == {d: 3.0 for d in range(7)} and result.blocked == {5} and result.tasks == []
    assert parse("2 tiếng ngày thường, 4 tiếng chủ nhật", today, lang="vi").availability == {0: 2, 1: 2, 2: 2, 3: 2, 4: 2, 6: 4}


def test_replies_follow_the_message_language(session, today):
    first = process_request("Tôi có bài tiểu luận hạn thứ 6", session, today=today)
    assert first["lang"] == "vi" and "mỗi ngày bạn học được mấy tiếng" in first["message"]
    assert first["suggestions"][0] == "2 tiếng"
    plan = process_request("2 tiếng", session, today=today)
    assert plan["intent"] == "planning" and plan["schedule"][0]["day"] == "T2 26/10"
    english = process_request("show my plan", session, today=today)
    assert english["lang"] == "en" and english["message"].startswith("Here is a draft schedule")


def test_vietnamese_commands(session, today):
    assert process_request("giúp", session, today=today)["intent"] == "help"
    process_request("bài tập giải tích hạn thứ 6, mỗi ngày 2 tiếng", session, today=today)
    done = process_request("đánh dấu bài tập giải tích là xong", session, today=today)
    assert done["message"].startswith('Đã đánh dấu "Bài tập giải tích" là xong')
    assert process_request("làm lại", session, today=today)["tasks"] == []


def test_vietnamese_office_question(session, today):
    response = process_request("Thư viện ở đâu?", session, today=today)
    assert response["intent"] == "office" and response["message"] == "Library: phòng B.201, mở cửa Mon-Sat 07:00-20:00."


def test_every_reply_has_a_vietnamese_translation():
    """Each English text passed to t() needs a Vietnamese version, or Vietnamese users see English."""
    src = Path(__file__).resolve().parents[1] / "src" / "assistant"
    keys = set()
    for path in src.rglob("*.py"):
        found = re.findall(r'\bt\([^,()]+,\s*"((?:[^"\\]|\\.)*)"', path.read_text(encoding="utf-8"))
        keys |= {k.replace('\\"', '"') for k in found}
    # Texts chosen in a variable before t() is called.
    keys |= {"every day", "weekdays", "weekends",
             "Questions were written by the {name} model from your notes.",
             "Not enough time for {title}: it needs about {need}, but only {placed} fit before {limit}."}
    assert sorted(k for k in keys if k not in i18n.VI) == []


def test_casual_vietnamese_shares_the_closing_deadline():
    saturday = date(2026, 11, 21)
    result = parse("Tuần này mình phải lo vụ lab hóa với cái slide nhóm môn kinh tế, cuối tuần nộp", saturday, lang="vi")
    assert [(t.title, t.deadline) for t in result.tasks] == [
        ("Lab hóa", date(2026, 11, 22)), ("Slide nhóm môn kinh tế", date(2026, 11, 22))]
    assert result.assumptions == ["Hiểu 'cuối tuần' là CN 22/11."]

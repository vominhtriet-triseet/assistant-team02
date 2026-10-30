from datetime import date

from assistant.planning.parser import parse


def test_two_tasks_with_deadlines(today):
    result = parse("I have a calculus problem set due Friday and a Data Structures midterm next Wednesday.", today)
    titles = [t.title for t in result.tasks]
    assert titles == ["Calculus problem set", "Prepare for Data Structures midterm"]
    assert result.tasks[0].deadline == date(2026, 10, 30)
    assert result.tasks[1].deadline == date(2026, 10, 28)
    assert result.tasks[1].kind == "exam" and result.tasks[1].hours == 8
    assert any("next Wednesday" in a for a in result.assumptions)


def test_names_containing_and_stay_together(today):
    result = parse("Data Structures and Algorithms exam on Friday", today)
    assert [t.title for t in result.tasks] == ["Prepare for Data Structures and Algorithms exam"]


def test_explicit_duration_and_time(today):
    result = parse("finish my programming assignment before 5 PM, about 3 hours", today)
    task = result.tasks[0]
    assert task.title == "Finish programming assignment"
    assert task.deadline == today and task.deadline_time == "17:00"
    assert task.hours == 3 and not task.hours_assumed


def test_day_month_date(today):
    task = parse("essay due 12/11", today).tasks[0]
    assert task.deadline == date(2026, 11, 12)


def test_availability_weekdays_and_busy_day(today):
    result = parse("About 3 hours on weekdays. I'm busy all Saturday.", today)
    assert result.tasks == []
    assert result.availability == {0: 3.0, 1: 3.0, 2: 3.0, 3: 3.0, 4: 3.0}
    assert result.blocked == {5}


def test_bare_hours_only_count_when_asked(today):
    assert parse("3 hours", today).availability == {}
    assert parse("3 hours", today, awaiting_availability=True).availability == {d: 3.0 for d in range(7)}


def test_availability_and_task_in_one_sentence(today):
    result = parse("I can study 2 hours a day and need to finish my essay by Friday", today)
    assert result.availability[0] == 2.0
    assert [t.title for t in result.tasks] == ["Finish essay"]


def test_request_without_task_details_is_ignored(today):
    assert parse("Can you help me study?", today).tasks == []


def test_priority_from_deadline(today):
    tasks = parse("report due tomorrow, project due Saturday, reading due in 10 days", today).tasks
    assert [t.priority for t in tasks] == ["high", "medium", "low"]


def test_highlights_point_at_the_original_text(today):
    text = "I have a calculus problem set due Friday"
    result = parse(text, today)
    assert {"text": "due Friday", "kind": "date"} in result.highlights
    assert {"text": "calculus problem set", "kind": "task"} in result.highlights

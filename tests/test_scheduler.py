from datetime import date

from assistant.planning.models import Task
from assistant.planning.scheduler import build_schedule

WEEKDAYS_3H = {d: 3.0 for d in range(5)}


def hours_by_task(schedule):
    totals = {}
    for day in schedule:
        for block in day["blocks"]:
            if not block["event"]:
                totals[block["title"]] = totals.get(block["title"], 0) + block["hours"]
    return totals


def test_exam_work_stops_the_day_before(today):
    exam = Task("Prepare for midterm", kind="exam", deadline=date(2026, 10, 28), hours=4, id=1)
    schedule, warnings, _ = build_schedule([exam], WEEKDAYS_3H, today)
    work_days = [d["date"] for d in schedule if any(not b["event"] for b in d["blocks"])]
    assert work_days == ["2026-10-26", "2026-10-27"]
    assert warnings == []


def test_not_enough_time_is_reported_not_hidden(today):
    exam = Task("Prepare for midterm", kind="exam", deadline=date(2026, 10, 28), hours=8, id=1)
    schedule, warnings, _ = build_schedule([exam], WEEKDAYS_3H, today)
    assert hours_by_task(schedule) == {"Prepare for midterm": 6}
    assert len(warnings) == 1 and "only 6 h fit" in warnings[0]


def test_earliest_deadline_goes_first(today):
    later = Task("Essay", kind="assignment", deadline=date(2026, 10, 30), hours=3, id=1)
    sooner = Task("Lab report", kind="assignment", deadline=date(2026, 10, 26), hours=3, id=2)
    schedule, warnings, _ = build_schedule([later, sooner], WEEKDAYS_3H, today)
    assert schedule[0]["blocks"][0]["title"] == "Lab report"
    assert warnings == []


def test_blocked_and_unlisted_days_get_no_work(today):
    task = Task("Project", kind="project", deadline=date(2026, 11, 2), hours=20, id=1)
    schedule, _, _ = build_schedule([task], WEEKDAYS_3H, today)
    days = {d["date"] for d in schedule for b in d["blocks"] if not b["event"]}
    assert "2026-10-31" not in days and "2026-11-01" not in days


def test_done_tasks_are_skipped(today):
    task = Task("Essay", kind="assignment", deadline=date(2026, 10, 30), hours=3, status="done", id=1)
    schedule, warnings, _ = build_schedule([task], WEEKDAYS_3H, today)
    assert schedule == [] and warnings == []


def test_past_deadline(today):
    task = Task("Old lab", kind="assignment", deadline=date(2026, 10, 20), hours=2, id=1)
    _, warnings, _ = build_schedule([task], WEEKDAYS_3H, today)
    assert "can no longer be scheduled" in warnings[0]


def test_task_without_deadline_uses_one_week(today):
    task = Task("Read chapter 4", kind="reading", hours=2, id=1)
    schedule, warnings, assumptions = build_schedule([task], WEEKDAYS_3H, today)
    assert hours_by_task(schedule) == {"Read chapter 4": 2}
    assert "next 7 days" in assumptions[0]

"""Greedy earliest-deadline-first scheduler with daily study capacity."""
from __future__ import annotations

from datetime import date, timedelta

from assistant.planning.models import PRIORITY_RANK, Task
from assistant.planning.parser import format_day, format_hours

DEFAULT_HORIZON_DAYS = 6


def _event(task: Task) -> dict:
    if task.kind in ("exam", "quiz"):
        title = task.title.removeprefix("Prepare for ")
    else:
        title = f"{task.title} due"
    if task.deadline_time:
        title += f" at {task.deadline_time}"
    return {"task_id": task.id, "title": title, "hours": 0, "event": True}


def build_schedule(tasks: list[Task], hours_per_weekday: dict[int, float], today: date) -> tuple[list[dict], list[str], list[str]]:
    """Return (schedule by day, warnings, assumptions).

    Tasks are placed in order of their last possible work day, then priority. Each task
    fills the earliest free study time it is allowed to use. Work that does not fit is
    reported as a warning instead of being squeezed in.
    """
    pending = [t for t in tasks if t.status != "done"]
    default_end = today + timedelta(days=DEFAULT_HORIZON_DAYS)
    ends = [t.deadline for t in pending if t.deadline] + [default_end]
    days = [today + timedelta(days=i) for i in range((max(ends) - today).days + 1)]
    free = {d: hours_per_weekday.get(d.weekday(), 0.0) for d in days}
    plan: dict[date, list[dict]] = {d: [] for d in days}
    warnings: list[str] = []
    assumptions: list[str] = []

    order = sorted(pending, key=lambda t: (t.last_work_day() or date.max, PRIORITY_RANK[t.priority], t.id))
    for task in order:
        last = task.last_work_day() or default_end
        if task.deadline is None:
            assumptions.append(f"{task.title} has no deadline, so it is planned within the next 7 days.")
        need = task.hours
        for day in days:
            if day > last or need <= 0:
                break
            take = min(need, free[day])
            if take > 0:
                plan[day].append({"task_id": task.id, "title": task.title, "hours": round(take, 2), "event": False})
                free[day] -= take
                need -= take
        if need > 0:
            if last < today:
                warnings.append(f"{task.title} was due {format_day(task.deadline)}, so it can no longer be scheduled.")
            else:
                placed = task.hours - need
                limit = format_day(task.deadline) if task.deadline else "the end of the week"
                warnings.append(
                    f"Not enough time for {task.title}: it needs about {format_hours(task.hours)}, "
                    f"but only {format_hours(round(placed, 2))} fit before {limit}."
                )
        if task.deadline and task.deadline in plan:
            plan[task.deadline].append(_event(task))

    schedule = [
        {"date": d.isoformat(), "day": format_day(d), "blocks": plan[d]}
        for d in days
        if plan[d]
    ]
    return schedule, warnings, assumptions

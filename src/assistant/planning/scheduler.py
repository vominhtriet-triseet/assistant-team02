"""Greedy earliest-deadline-first scheduler with daily study capacity and task dependencies."""
from __future__ import annotations

from datetime import date, timedelta

from assistant.i18n import t
from assistant.planning.models import EXAM_KINDS, PRIORITY_RANK, Task
from assistant.planning.parser import exam_name, format_day, format_hours

DEFAULT_HORIZON_DAYS = 6


def _event(task: Task, lang: str) -> dict:
    title = exam_name(task.title) if task.kind in EXAM_KINDS else t(lang, "{title} due", title=task.title)
    if task.deadline_time:
        title += t(lang, " at {time}", time=task.deadline_time)
    return {"task_id": task.id, "title": title, "hours": 0, "event": True}


def _dependency_order(order: list[Task], waits: dict[int, set[int]], lang: str, warnings: list[str]) -> list[Task]:
    """Keep the deadline order, but never place a task before the tasks it depends on."""
    result: list[Task] = []
    placed: set[int] = set()
    order = list(order)
    while order:
        ready = next((task for task in order if waits[task.id] <= placed), None)
        if ready is None:  # a loop such as A after B and B after A
            warnings.append(t(lang, "These tasks depend on each other in a loop, so that order was ignored: {titles}.",
                              titles=", ".join(task.title for task in order)))
            for task in order:
                waits[task.id] = set()
            ready = order[0]
        order.remove(ready)
        result.append(ready)
        placed.add(ready.id)
    return result


def build_schedule(
    tasks: list[Task], hours_per_weekday: dict[int, float], today: date,
    lang: str = "en", dependencies: set[tuple[int, int]] | None = None,
) -> tuple[list[dict], list[str], list[str]]:
    """Return (schedule by day, warnings, assumptions).

    Tasks are placed in order of their last possible work day, then priority. A task
    that depends on another starts no earlier than the day that task is finished. Each
    task fills the earliest free study time it is allowed to use. Work that does not fit
    is reported as a warning instead of being squeezed in.
    """
    pending = [task for task in tasks if task.status != "done"]
    by_id = {task.id: task for task in pending}
    default_end = today + timedelta(days=DEFAULT_HORIZON_DAYS)
    ends = [task.deadline for task in pending if task.deadline] + [default_end]
    days = [today + timedelta(days=i) for i in range((max(ends) - today).days + 1)]
    free = {d: hours_per_weekday.get(d.weekday(), 0.0) for d in days}
    plan: dict[date, list[dict]] = {d: [] for d in days}
    warnings: list[str] = []
    assumptions: list[str] = []

    waits = {task.id: {dep for a, dep in (dependencies or set()) if a == task.id and dep in by_id} for task in pending}
    order = sorted(pending, key=lambda task: (task.last_work_day() or date.max, PRIORITY_RANK[task.priority], task.id))
    order = _dependency_order(order, waits, lang, warnings)
    finished: dict[int, date] = {}

    for task in order:
        last = task.last_work_day() or default_end
        start = max((finished[dep] for dep in waits[task.id]), default=today)
        for dep in waits[task.id]:
            assumptions.append(t(lang, "{task} is planned after {dep} because it depends on it.", task=task.title, dep=by_id[dep].title))
        if task.deadline is None:
            assumptions.append(t(lang, "{title} has no deadline, so it is planned within the next 7 days.", title=task.title))
        need = task.hours
        finished[task.id] = start
        for day in days:
            if day > last or need <= 0:
                break
            take = min(need, free[day]) if day >= start else 0
            if take > 0:
                plan[day].append({"task_id": task.id, "title": task.title, "hours": round(take, 2), "event": False})
                free[day] -= take
                need -= take
                finished[task.id] = day
        if need > 0:
            finished[task.id] = max(last, start)  # unfinished work pushes dependents past its deadline
            if last < today:
                warnings.append(t(lang, "{title} was due {date}, so it can no longer be scheduled.",
                                  title=task.title, date=format_day(task.deadline, lang)))
            else:
                placed = task.hours - need
                values = {
                    "title": task.title, "need": format_hours(task.hours), "placed": format_hours(round(placed, 2)),
                    "limit": format_day(task.deadline, lang) if task.deadline else t(lang, "the end of the week"),
                }
                users = list(dict.fromkeys(
                    b["title"] for d in days if d <= last for b in plan[d] if not b["event"]
                ))
                if placed:
                    template = "Not enough time for {title}: it needs about {need}, but only {placed} fit before {limit}."
                elif users:
                    # Say where the time went, so a zero is not mistaken for a bug.
                    template = ("Not enough time for {title}: it needs about {need}, but only {placed} fit before {limit}: "
                                "that time is already used by {users}.")
                    values["users"] = ", ".join(users)
                else:
                    template = ("Not enough time for {title}: it needs about {need}, but only {placed} fit before {limit}: "
                                "there is no study time on those days.")
                warnings.append(t(lang, template, **values))
        if task.deadline and task.deadline in plan:
            plan[task.deadline].append(_event(task, lang))

    schedule = [
        {"date": d.isoformat(), "day": format_day(d, lang), "blocks": plan[d]}
        for d in days
        if plan[d]
    ]
    return schedule, warnings, assumptions

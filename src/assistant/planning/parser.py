"""Rule-based extraction of tasks, deadlines, durations, and study availability.

The parser only reads what the student wrote. Anything it has to guess, such as a
task duration or which week "next Wednesday" means, is returned as an assumption.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from assistant.planning.models import ParseResult, Task

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ALIASES = {
    "mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3, "thurs": 3, "fri": 4, "sat": 5, "sun": 6,
    **{name: i for i, name in enumerate(DAY_NAMES)},
}
DAY_PATTERN = "|".join(sorted(DAY_ALIASES, key=len, reverse=True))
WEEKDAYS, WEEKEND, ALL_DAYS = set(range(5)), {5, 6}, set(range(7))

# (kind, pattern, default hours). The first match wins, so exams come before reviews.
KINDS = [
    ("quiz", r"\bquiz(?:zes)?\b", 2.0),
    ("exam", r"\b(?:exam|midterm|final|test)s?\b", 8.0),
    ("project", r"\bprojects?\b", 6.0),
    ("presentation", r"\b(?:presentation|slides|talk)\b", 3.0),
    ("assignment", r"\b(?:assignment|homework|problem set|exercises?|lab|report|essay)s?\b", 4.0),
    ("reading", r"\b(?:read|reading|chapter)\b", 2.0),
    ("review", r"\b(?:review|revise|study|practi[cs]e|learn)\b", 2.0),
]

PREP = r"(?:(?:due|by|before|on|until)\s+)?"
DEADLINE_RE = re.compile(
    PREP + rf"(?:\b(?P<rel>next|this)\s+)?\b(?P<day>{DAY_PATTERN})\b"
    r"|" + PREP + r"\b(?P<word>today|tonight|tomorrow)\b"
    r"|" + PREP + r"\bin\s+(?P<n>\d+)\s+days?\b"
    r"|" + PREP + r"\b(?P<iso>\d{4}-\d{2}-\d{2})\b"
    r"|" + PREP + r"\b(?P<dd>\d{1,2})/(?P<mm>\d{1,2})\b",
    re.I,
)
TIME_RE = re.compile(
    r"(?:(?:by|before|at|until)\s+)?\b(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm)\b"
    r"|(?:(?:by|before|at|until)\s+)?\b(?P<h24>\d{1,2}):(?P<m24>\d{2})\b",
    re.I,
)
DURATION_RE = re.compile(
    r"(?:\b(?:for|about|around)\s+|~)?\b(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|h|minutes?|mins?)\b", re.I
)
AVAILABILITY_HINT = re.compile(
    rf"\b(?:per day|a day|each day|every day|daily|a night|weekdays?|weekends?|can study|can work|free)\b"
    rf"|\bon\s+(?:{DAY_PATTERN})\b",
    re.I,
)
# "I can study 2 hours a day" is about study time even though it contains "study".
STUDY_TIME_RE = re.compile(r"\b(?:can study|can work|per day|a day|each day|every day|daily)\b", re.I)
BLOCKED_RE = re.compile(
    r"\b(?:busy|not free|not available|unavailable|no time|can't study|cannot study|none|no study|day off|off)\b", re.I
)
PRIORITY_HIGH = re.compile(r"\b(?:urgent|asap|important|high priority)\b", re.I)
PRIORITY_LOW = re.compile(r"\blow priority\b", re.I)
SPLIT_RE = re.compile(r",|;|\band\b|\bthen\b|\bbut\b", re.I)
LEADING_WORDS = [
    r"(?:so|also|then|and|but|plus|please)\b",
    r"(?:can|could|would|will) you(?: please)?(?: help me)?(?: to)?\b",
    r"help me(?: to)?\b",
    r"(?:i|we)(?:'ve|'ll|'m)?\b",
    r"(?:have got|have to|need to|must|should|want to|got to|am going to|going to|will|have|has|got)\b",
    r"to\b",
    r"(?:a|an|my|the|our|some)\b",
    r"(?:there is|there's)\b",
]
TRAILING_WORDS = re.compile(r"\s*\b(?:due|by|before|on|until|for|at|is|which|that|in|next|this)\s*$", re.I)


def format_day(day: date) -> str:
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"


def format_hours(hours: float) -> str:
    return f"{hours:g} h"


def task_kind(text: str) -> tuple[str, float] | None:
    for kind, pattern, hours in KINDS:
        if re.search(pattern, text, re.I):
            return kind, hours
    return None


def _day_scope(text: str) -> set[int]:
    lowered = text.lower()
    days: set[int] = set()
    if re.search(r"\bweekdays?\b", lowered):
        days |= WEEKDAYS
    if re.search(r"\bweekends?\b", lowered):
        days |= WEEKEND
    days |= {DAY_ALIASES[m] for m in re.findall(rf"\b({DAY_PATTERN})\b", lowered)}
    return days


def _hours(match: re.Match) -> float:
    value = float(match.group("n"))
    return value / 60 if match.group("unit").lower().startswith("m") else value


def _resolve_date(m: re.Match, today: date, assumptions: list[str]) -> date | None:
    if m.group("day"):
        target = DAY_ALIASES[m.group("day").lower()]
        delta = (target - today.weekday()) % 7
        if m.group("rel") and m.group("rel").lower() == "next":
            delta = delta or 7
            day = today + timedelta(days=delta)
            assumptions.append(f"Read 'next {DAY_NAMES[target].title()}' as {format_day(day)}.")
            return day
        return today + timedelta(days=delta)
    if m.group("word"):
        return today + timedelta(days=1 if m.group("word").lower() == "tomorrow" else 0)
    if m.group("n"):
        return today + timedelta(days=int(m.group("n")))
    if m.group("iso"):
        try:
            return date.fromisoformat(m.group("iso"))
        except ValueError:
            return None
    try:
        day = date(today.year, int(m.group("mm")), int(m.group("dd")))
    except ValueError:
        return None
    if day < today:
        day = day.replace(year=today.year + 1)
    assumptions.append(f"Read {m.group('dd')}/{m.group('mm')} as {format_day(day)} (day/month).")
    return day


def _clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" .,!?;:-")
    changed = True
    while changed:
        changed = False
        for pattern in LEADING_WORDS:
            stripped = re.sub(r"^" + pattern + r"\s*", "", text, flags=re.I)
            if stripped != text:
                text, changed = stripped, True
    while TRAILING_WORDS.search(text):
        text = TRAILING_WORDS.sub("", text)
    text = re.sub(r"\b(?:my|our)\s+", "", text, flags=re.I).strip(" .,!?;:-")
    return text[:1].upper() + text[1:]


def _clauses(sentence: str) -> list[str]:
    """Split a sentence into one clause per task, keeping names like 'Data Structures and Algorithms exam'."""
    clauses: list[str] = []
    carry = ""
    for part in (p.strip() for p in SPLIT_RE.split(sentence)):
        if not part:
            continue
        if task_kind(part):
            clauses.append(f"{carry} and {part}" if carry else part)
            carry = ""
        elif clauses and (DEADLINE_RE.search(part) or TIME_RE.search(part) or DURATION_RE.search(part)) and len(part.split()) <= 4:
            clauses[-1] += " " + part
        elif not clauses:
            carry = f"{carry} and {part}" if carry else part
    return clauses


def _parse_task(clause: str, today: date, result: ParseResult) -> Task | None:
    found = task_kind(clause)
    if not found:
        return None
    kind, default_hours = found
    work = clause
    task = Task(title="", kind=kind, hours=default_hours)

    m = DEADLINE_RE.search(work)
    if m:
        task.deadline = _resolve_date(m, today, result.assumptions)
        result.highlights.append({"text": m.group(0).strip(), "kind": "date"})
        work = work[: m.start()] + " " + work[m.end():]
    t = TIME_RE.search(work)
    if t:
        hour = int(t.group("h") or t.group("h24"))
        minute = int(t.group("m") or t.group("m24") or 0)
        if t.group("ap"):
            hour = hour % 12 + (12 if t.group("ap").lower() == "pm" else 0)
        task.deadline_time = f"{hour:02d}:{minute:02d}"
        result.highlights.append({"text": t.group(0).strip(), "kind": "date"})
        work = work[: t.start()] + " " + work[t.end():]
        if task.deadline is None:
            task.deadline = today
            result.assumptions.append(f"No date was given for the {task.deadline_time} deadline, so it is read as today.")
    d = DURATION_RE.search(work)
    if d:
        task.hours, task.hours_assumed = _hours(d), False
        result.highlights.append({"text": d.group(0).strip(), "kind": "time"})
        work = work[: d.start()] + " " + work[d.end():]
    if PRIORITY_HIGH.search(work):
        task.priority, task.priority_reason = "high", "marked as important"
        work = PRIORITY_HIGH.sub(" ", work)
    elif PRIORITY_LOW.search(work):
        task.priority, task.priority_reason = "low", "marked as low priority"
        work = PRIORITY_LOW.sub(" ", work)

    name = _clean_title(work)
    if len(name.split()) < 2 and task.deadline is None and task.hours_assumed:
        return None  # e.g. "Can you help me study?" carries no task details
    if name.lower() in clause.lower():
        result.highlights.append({"text": clause[clause.lower().index(name.lower()):][: len(name)], "kind": "task"})
    if kind in ("exam", "quiz") and not re.match(r"(?:prepare|review|study|revise)\b", name, re.I):
        name = f"Prepare for {name}"
    task.title = name
    if not task.priority_reason:
        set_priority(task, today)
    return task


def set_priority(task: Task, today: date) -> None:
    if task.priority_reason.startswith("marked"):
        return
    if task.deadline is None:
        task.priority, task.priority_reason = "low", "no deadline given"
        return
    days = (task.deadline - today).days
    if days <= 2:
        task.priority, task.priority_reason = "high", "due within 2 days"
    elif days <= 5:
        task.priority, task.priority_reason = "medium", "due within 5 days"
    else:
        task.priority, task.priority_reason = "low", f"due in {days} days"


def _parse_availability(segment: str, result: ParseResult, bare_ok: bool) -> bool:
    """Read study time or busy days from one segment. Returns True if the segment was about availability."""
    if task_kind(segment) and not STUDY_TIME_RE.search(segment):
        return False
    m = DURATION_RE.search(segment)
    if m and (AVAILABILITY_HINT.search(segment) or bare_ok):
        for day in _day_scope(segment) or ALL_DAYS:
            result.availability[day] = _hours(m)
        result.highlights.append({"text": m.group(0).strip(), "kind": "time"})
        return True
    if BLOCKED_RE.search(segment):
        days = _day_scope(segment)
        if days:
            result.blocked |= days
            return True
    return False


def parse(text: str, today: date, awaiting_availability: bool = False) -> ParseResult:
    result = ParseResult()
    for sentence in (s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text)):
        if not sentence:
            continue
        # A bare "3 hours" answers the study-time question, unless the sentence also names a task.
        bare_ok = awaiting_availability and not task_kind(sentence)
        remaining = [seg for seg in SPLIT_RE.split(sentence) if seg and seg.strip()]
        kept = [seg for seg in remaining if not _parse_availability(seg, result, bare_ok)]
        if len(kept) != len(remaining):
            sentence = " and ".join(seg.strip() for seg in kept)
        for clause in _clauses(sentence):
            task = _parse_task(clause, today, result)
            if task:
                result.tasks.append(task)
    return result

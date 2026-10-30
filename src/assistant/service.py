"""The single entry point used by the CLI, the web server, and the evaluator.

process_request() follows docs/ai-interface.md: it validates the input, routes it,
and returns a dictionary with at least tasks, priorities, schedule, and message.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from assistant import llm, offices
from assistant.planning.models import Task
from assistant.planning.parser import (
    DAY_NAMES,
    format_day,
    format_hours,
    parse,
    set_priority,
    task_kind,
)
from assistant.planning.scheduler import build_schedule

GREETINGS = {"hi", "hello", "hey", "xin chao", "chao", "good morning", "good evening"}
HELP_RE = re.compile(r"^(?:help|commands|what can you do|how do i use (?:this|you))$")
RESET_RE = re.compile(r"^(?:reset|start over|clear(?: my)? plan|new plan)$")
SHOW_RE = re.compile(r"^(?:show(?: me)?(?: my)? (?:plan|schedule)|my (?:plan|schedule)|what(?:'s| is) my (?:plan|schedule))$")
DONE_RE = re.compile(
    r"^(?:mark|set)\s+(?P<a>.+?)\s+(?:as\s+)?(?:done|complete|completed|finished)$"
    r"|^(?:i(?:'ve| have)?\s+)?(?:finished|completed|done with)\s+(?P<b>.+)$"
)
OFFICE_QUESTION_RE = re.compile(r"\b(?:where|when|open|opens|opening|room|hours|located|location|find)\b")
PLANNING_HINT_RE = re.compile(r"\b(?:plan|schedule|deadline|due|exam|study|homework|assignment|task)\b")
VARIES_RE = re.compile(r"\b(?:changes|varies|depends|different)\b")

HELP_TEXT = (
    "I turn what you need to do into tasks and a proposed study schedule.\n"
    "- Plan: \"I have a calculus problem set due Friday and a midterm next Wednesday.\"\n"
    "- Study time: \"3 hours on weekdays, I'm busy on Saturday.\"\n"
    "- Update: \"Mark calculus problem set as done.\" or \"Show my plan.\"\n"
    "- Campus offices: \"Where is the library?\"\n"
    "Type \"reset\" to start a new plan. Notes and study practice are planned for a later version."
)
FALLBACK_TEXT = (
    "I can't help with that yet. Tell me about tasks and deadlines, for example "
    "\"I have an essay due Friday\", or ask where a campus office is."
)
EXAMPLES = ["I have an essay due Friday", "Where is the library?", "help"]


@dataclass
class Session:
    tasks: list[Task] = field(default_factory=list)
    availability: dict[int, float] = field(default_factory=dict)
    blocked: set[int] = field(default_factory=set)
    awaiting: str | None = None
    next_id: int = 1

    def add_task(self, task: Task) -> None:
        key = task.title.lower()
        for existing in self.tasks:
            if existing.title.lower() == key:
                for attr in ("deadline", "deadline_time"):
                    if getattr(task, attr):
                        setattr(existing, attr, getattr(task, attr))
                if not task.hours_assumed:
                    existing.hours, existing.hours_assumed = task.hours, False
                return
        task.id = self.next_id
        self.next_id += 1
        self.tasks.append(task)

    def hours_per_weekday(self) -> dict[int, float]:
        hours = dict(self.availability)
        for day in self.blocked:
            hours[day] = 0.0
        return hours


def _response(intent: str, message: str, session: Session, **extra) -> dict:
    response = {
        "intent": intent,
        "message": message,
        "tasks": [t.to_dict() for t in session.tasks],
        "priorities": [
            {"task_id": t.id, "priority": t.priority, "reason": t.priority_reason}
            for t in session.tasks
            if t.status != "done"
        ],
        "schedule": None,
        "warnings": [],
        "assumptions": [],
        "facts": [],
        "highlights": [],
        "suggestions": [],
    }
    response.update(extra)
    return response


def _day_list(days: list[int]) -> str:
    named = {tuple(range(7)): "every day", tuple(range(5)): "weekdays", (5, 6): "weekends"}
    key = tuple(sorted(days))
    return named.get(key) or ", ".join(DAY_NAMES[d][:3].title() for d in key)


def _facts(session: Session) -> list[str]:
    facts = []
    for t in session.tasks:
        if t.deadline is None:
            continue
        when = format_day(t.deadline) + (f" at {t.deadline_time}" if t.deadline_time else "")
        if t.kind in ("exam", "quiz"):
            facts.append(f"{t.title.removeprefix('Prepare for ')} on {when}")
        else:
            facts.append(f"{t.title} due {when}")
    by_hours: dict[float, list[int]] = {}
    for day, hours in session.availability.items():
        if day not in session.blocked:
            by_hours.setdefault(hours, []).append(day)
    for hours, days in sorted(by_hours.items()):
        facts.append(f"{format_hours(hours)} of study time on {_day_list(days)}")
    if session.blocked:
        facts.append(f"Busy on {_day_list(list(session.blocked))}")
    return facts


def _plan_response(session: Session, today: date, assumptions: list[str], highlights: list[dict], note: str = "") -> dict:
    estimates = [f"{t.title} takes about {format_hours(t.hours)}" for t in session.tasks if t.hours_assumed and t.status != "done"]
    common = {"facts": _facts(session), "highlights": highlights}
    pending = [t for t in session.tasks if t.status != "done"]

    if not pending:
        session.awaiting = None
        message = note or "I noted your study time. Now tell me what you need to do and when it is due."
        return _response("planning", message, session, assumptions=assumptions, suggestions=EXAMPLES[:1], **common)

    if not session.availability:
        session.awaiting = "availability"
        count = len(pending)
        message = (
            f"{note}I found {count} task{'s' if count > 1 else ''}. One thing is missing before I can schedule anything: "
            "how many hours can you study each day?"
        ).strip()
        return _response(
            "clarification", message, session, assumptions=assumptions + estimates,
            suggestions=["2 hours", "3 hours", "It changes by day"], **common,
        )

    session.awaiting = None
    hours = session.hours_per_weekday()
    unspecified = [d for d in range(7) if d not in session.availability and d not in session.blocked]
    if unspecified and len(unspecified) < 7:
        assumptions = assumptions + [f"No study time is planned on {_day_list(unspecified)} because none was given."]
    schedule, warnings, schedule_assumptions = build_schedule(session.tasks, hours, today)
    message = note + "Here is a draft schedule. Change anything that looks wrong before you add it to your plan."
    suggestions = ["Show my plan", "reset"]
    if warnings:
        suggestions.insert(0, _more_time_suggestion(session, today))
    return _response(
        "planning", message, session, schedule=schedule, warnings=warnings,
        assumptions=assumptions + estimates + schedule_assumptions, suggestions=suggestions, **common,
    )


def _more_time_suggestion(session: Session, today: date) -> str:
    """Suggest study time on a free day before the latest deadline, or more hours per day."""
    hours = session.hours_per_weekday()
    ends = [t.last_work_day() for t in session.tasks if t.status != "done" and t.last_work_day()]
    for offset in range(((max(ends) - today).days + 1) if ends else 0):
        day = date.fromordinal(today.toordinal() + offset)
        if not hours.get(day.weekday()) and day.weekday() not in session.blocked:
            return f"2 hours on {DAY_NAMES[day.weekday()].title()}"
    return f"{max(hours.values(), default=2) + 1:g} hours per day"


def _match_task(session: Session, words: str) -> Task | None:
    query = set(re.findall(r"[a-z0-9]+", words.lower())) - {"my", "the", "a", "an", "for"}
    best, best_score = None, 0
    for task in session.tasks:
        score = len(query & set(re.findall(r"[a-z0-9]+", task.title.lower())))
        if score > best_score:
            best, best_score = task, score
    return best


def _tasks_from_llm(data: dict, today: date) -> tuple[list[Task], float | None]:
    """Validate model output field by field; anything malformed is dropped."""
    tasks = []
    for item in data.get("tasks") or []:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
            continue
        found = task_kind(item["title"])
        kind = item.get("kind") if item.get("kind") in {"exam", "quiz", "assignment", "project", "presentation", "reading", "review"} else (found[0] if found else "other")
        task = Task(title=item["title"].strip()[:120], kind=kind, hours=found[1] if found else 2.0)
        try:
            task.deadline = date.fromisoformat(item["deadline"]) if item.get("deadline") else None
        except (TypeError, ValueError):
            task.deadline = None
        hours = item.get("hours")
        if isinstance(hours, (int, float)) and 0 < hours <= 40:
            task.hours, task.hours_assumed = float(hours), False
        set_priority(task, today)
        tasks.append(task)
    per_day = data.get("hours_per_day")
    per_day = float(per_day) if isinstance(per_day, (int, float)) and 0 < per_day <= 16 else None
    return tasks, per_day


def process_request(user_input: str, session: Session | None = None, today: date | None = None, provider=None) -> dict:
    """Route one message and return a structured response.

    Raises ValueError for empty or non-string input. ``session`` keeps tasks and study
    time between messages; ``today`` and ``provider`` are injectable for tests.
    """
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("Please type a request.")
    session = session if session is not None else Session()
    today = today or date.today()
    text = user_input.strip()
    lowered = re.sub(r"\s+", " ", text.lower()).strip(" ?!.")

    if lowered in GREETINGS:
        return _response("greeting", "Hello! Tell me what you need to get done, or type \"help\".", session, suggestions=EXAMPLES)
    if HELP_RE.match(lowered):
        return _response("help", HELP_TEXT, session, suggestions=EXAMPLES[:2])
    if RESET_RE.match(lowered):
        session.__init__()
        return _response("reset", "Your plan is cleared. What do you need to do?", session, suggestions=EXAMPLES[:1])
    if SHOW_RE.match(lowered):
        if not session.tasks:
            return _response("planning", "You have no tasks yet. Tell me what you need to do and when it is due.", session, suggestions=EXAMPLES[:1])
        return _plan_response(session, today, [], [])
    done = DONE_RE.match(lowered)
    if done and not session.tasks:
        return _response("planning", "You have no tasks yet, so there is nothing to mark as done.", session, suggestions=EXAMPLES[:1])
    if done:
        task = _match_task(session, done.group("a") or done.group("b"))
        if task is None:
            return _response("planning", "I couldn't find that task in your plan.", session, suggestions=["Show my plan"])
        task.status = "done"
        return _plan_response(session, today, [], [], note=f"Marked \"{task.title}\" as done. ")
    if OFFICE_QUESTION_RE.search(lowered):
        answer = offices.answer(text)
        if answer:
            return _response("office", answer, session)

    parsed = parse(text, today, awaiting_availability=session.awaiting == "availability")
    warnings: list[str] = []
    if not (parsed.tasks or parsed.availability or parsed.blocked) and provider and PLANNING_HINT_RE.search(lowered):
        try:
            tasks, per_day = _tasks_from_llm(llm.extract_plan(provider, text, today), today)
            parsed.tasks = tasks
            if per_day:
                parsed.availability = {d: per_day for d in range(7)}
            if tasks:
                parsed.assumptions.append(f"Tasks were read by the {provider.name} language model. Check them before relying on the plan.")
        except llm.LLMError as exc:
            warnings.append(f"The AI service is unavailable ({exc}). Only rule-based reading was used.")

    if parsed.tasks or parsed.availability or parsed.blocked:
        for task in parsed.tasks:
            session.add_task(task)
        session.availability.update(parsed.availability)
        session.blocked |= parsed.blocked
        response = _plan_response(session, today, parsed.assumptions, parsed.highlights)
        response["warnings"] = warnings + response["warnings"]
        return response

    if session.awaiting == "availability" and VARIES_RE.search(lowered):
        return _response(
            "clarification",
            "Tell me the hours for each day, for example: \"2 hours on weekdays, 4 hours on Sunday\".",
            session,
            suggestions=["2 hours on weekdays, 4 hours on Sunday"],
        )
    return _response("fallback", FALLBACK_TEXT, session, warnings=warnings, suggestions=EXAMPLES)

"""The single entry point used by the CLI, the web server, and the evaluator.

process_request() follows docs/ai-interface.md: it validates the input, routes it to
planning, knowledge (notes), study (quizzes), or office lookup, and returns a dictionary
with at least tasks, priorities, schedule, and message. Replies follow the language of
the message (Vietnamese or English).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from assistant import i18n, knowledge, llm, offices, study
from assistant.i18n import t
from assistant.planning.models import EXAM_KINDS, Note, Study, Task
from assistant.planning.parser import (
    DAY_NAMES,
    DEADLINE_RE,
    DURATION_RE,
    VI_DAYS,
    exam_name,
    format_day,
    format_hours,
    parse,
    set_priority,
    task_kind,
)
from assistant.planning.scheduler import build_schedule

GREETINGS = {"hi", "hello", "hey", "xin chao", "chao", "good morning", "good evening",
             "xin chào", "chào", "chào bạn", "chào bot"}
HELP_RE = re.compile(r"^(?:help|commands|what can you do|how do i use (?:this|you)"
                     r"|giúp|trợ giúp|hướng dẫn|bạn làm được gì|bạn có thể làm gì)$")
RESET_RE = re.compile(r"^(?:reset|start over|clear(?: my)? plan|new plan|làm lại|bắt đầu lại|xóa kế hoạch|kế hoạch mới)$")
SHOW_RE = re.compile(r"^(?:show(?: me)?(?: my)? (?:plan|schedule)|my (?:plan|schedule)|what(?:'s| is) my (?:plan|schedule)"
                     r"|(?:xem|cho xem)(?: lại)? (?:kế hoạch|lịch)(?: học)?(?: của (?:tôi|mình|em))?|(?:kế hoạch|lịch) của (?:tôi|mình|em))$")
DONE_RE = re.compile(
    r"^(?:mark|set)\s+(?P<a>.+?)\s+(?:as\s+)?(?:done|complete|completed|finished)$"
    r"|^(?:i(?:'ve| have)?\s+)?(?:finished|completed|done with)\s+(?P<b>.+)$"
    r"|^đánh dấu\s+(?P<c>.+?)\s+(?:là\s+)?(?:đã\s+)?(?:xong|hoàn thành)$"
    r"|^(?:(?:tôi|mình|em)\s+)?(?:đã\s+)?(?:làm\s+)?xong\s+(?P<d>.+?)(?:\s+rồi)?$"
)
DEPENDS_RE = re.compile(
    r"^(?:do |làm )?(?P<a>.+?)\s+(?:after finishing|after|depends on|sau khi làm xong|sau khi xong|sau khi|phụ thuộc vào)\s+(?P<b>.+)$"
)
OFFICE_QUESTION_RE = re.compile(r"\b(?:where|when|open|opens|opening|room|hours|located|location|find"
                                r"|ở đâu|chỗ nào|mấy giờ|giờ mở cửa|mở cửa|phòng nào|nằm ở)\b")
PLANNING_HINT_RE = re.compile(r"\b(?:plan|schedule|deadline|due|exam|study|homework|assignment|task"
                              r"|kế hoạch|lịch|hạn|thi|kiểm tra|bài tập|ôn|học|nộp|đồ án|báo cáo|môn)\b")
MAX_TITLE_WORDS = 8  # rule-read titles longer than this are probably a whole sentence
VARIES_RE = re.compile(r"\b(?:changes|varies|depends|different|tùy|thay đổi|khác nhau)\b")
EXAMPLES = {
    "en": ["I have an essay due Friday", "save note: Derivatives - the derivative of x^2 is 2x #calculus", "Where is the library?", "help"],
    "vi": ["Tôi có bài tập giải tích hạn thứ 6", "lưu ghi chú: Đạo hàm - đạo hàm của x^2 là 2x #giaitich", "Thư viện ở đâu?", "giúp"],
}


@dataclass
class Session:
    """Everything one student has entered: the AssistantContext and the records it links."""

    tasks: list[Task] = field(default_factory=list)
    availability: dict[int, float] = field(default_factory=dict)
    blocked: set[int] = field(default_factory=set)
    awaiting: str | None = None
    next_id: int = 1
    # Assumptions behind the current plan; replies that don't replan keep showing them.
    assumptions: list[str] = field(default_factory=list)
    lang: str = "en"
    user_goal: str = ""
    next_actions: list[str] = field(default_factory=list)
    dependencies: set[tuple[int, int]] = field(default_factory=set)  # (task_id, depends_on_id)
    schedule: list[dict] = field(default_factory=list)  # the last proposed schedule
    notes: list[Note] = field(default_factory=list)
    next_note_id: int = 1
    links: set[tuple[int, int]] = field(default_factory=set)  # (task_id, note_id)
    studies: list[Study] = field(default_factory=list)
    next_study_id: int = 1

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

    def add_note(self, note: Note) -> None:
        note.id, note.created_at = self.next_note_id, note.created_at or _now()
        self.next_note_id += 1
        self.notes.append(note)

    def add_study(self, item: Study) -> None:
        item.id, item.started_at = self.next_study_id, item.started_at or _now()
        self.next_study_id += 1
        self.studies.append(item)

    def active_study(self) -> Study | None:
        return self.studies[-1] if self.awaiting == "study_answer" and self.studies else None

    def reset_plan(self) -> None:
        """Clear the plan; saved notes and past study sessions stay."""
        keep = {k: getattr(self, k) for k in ("lang", "notes", "next_note_id", "studies", "next_study_id")}
        self.__init__(**keep)

    def hours_per_weekday(self) -> dict[int, float]:
        hours = dict(self.availability)
        for day in self.blocked:
            hours[day] = 0.0
        return hours


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _response(intent: str, message: str, session: Session, **extra) -> dict:
    response = {
        "intent": intent,
        "lang": session.lang,
        "message": message,
        "tasks": [t.to_dict() for t in session.tasks],
        "priorities": [
            {"task_id": t.id, "priority": t.priority, "reason": t.priority_reason}
            for t in session.tasks
            if t.status != "done"
        ],
        "schedule": None,
        "warnings": [],
        "assumptions": list(session.assumptions),
        "facts": _facts(session),
        "highlights": [],
        "suggestions": [],
        "notes": [],
        "citations": [],
        "study": None,
    }
    response.update(extra)
    if "assumptions" in extra:
        session.assumptions = list(extra["assumptions"])
    session.next_actions = list(response["suggestions"])
    return response


def _day_list(days: list[int], lang: str) -> str:
    named = {tuple(range(7)): "every day", tuple(range(5)): "weekdays", (5, 6): "weekends"}
    key = tuple(sorted(days))
    if key in named:
        return t(lang, named[key])
    return ", ".join((VI_DAYS[d] if lang == "vi" else DAY_NAMES[d][:3].title()) for d in key)


def _facts(session: Session) -> list[str]:
    lang = session.lang
    facts = []
    for task in session.tasks:
        if task.deadline is None:
            continue
        when = format_day(task.deadline, lang) + (t(lang, " at {time}", time=task.deadline_time) if task.deadline_time else "")
        if task.kind in EXAM_KINDS:
            facts.append(t(lang, "{title} on {when}", title=exam_name(task.title), when=when))
        else:
            facts.append(t(lang, "{title} due {when}", title=task.title, when=when))
    by_hours: dict[float, list[int]] = {}
    for day, hours in session.availability.items():
        if day not in session.blocked:
            by_hours.setdefault(hours, []).append(day)
    for hours, days in sorted(by_hours.items()):
        facts.append(t(lang, "{hours} of study time on {days}", hours=format_hours(hours), days=_day_list(days, lang)))
    if session.blocked:
        facts.append(t(lang, "Busy on {days}", days=_day_list(list(session.blocked), lang)))
    for task_id, dep in sorted(session.dependencies):
        a, b = _task(session, task_id), _task(session, dep)
        if a and b:
            facts.append(t(lang, "{task} comes after {dep}", task=a.title, dep=b.title))
    return facts


def _task(session: Session, task_id: int) -> Task | None:
    return next((task for task in session.tasks if task.id == task_id), None)


def _plan_response(session: Session, today: date, assumptions: list[str], highlights: list[dict], note: str = "") -> dict:
    lang = session.lang
    estimates = [t(lang, "{title} takes about {hours}", title=task.title, hours=format_hours(task.hours))
                 for task in session.tasks if task.hours_assumed and task.status != "done"]
    common = {"facts": _facts(session), "highlights": highlights}
    pending = [task for task in session.tasks if task.status != "done"]

    if not pending:
        session.awaiting = None
        session.schedule = []
        message = note or t(lang, "I noted your study time. Now tell me what you need to do and when it is due.")
        return _response("planning", message, session, assumptions=assumptions, suggestions=EXAMPLES[lang][:1], **common)

    if not session.availability:
        session.awaiting = "availability"
        count = len(pending)
        template = ("{note}I found {count} task. One thing is missing before I can schedule anything: how many hours can you study each day?"
                    if count == 1 else
                    "{note}I found {count} tasks. One thing is missing before I can schedule anything: how many hours can you study each day?")
        return _response(
            "clarification", t(lang, template, note=note, count=count).strip(), session, assumptions=assumptions + estimates,
            suggestions=[t(lang, "2 hours"), t(lang, "3 hours"), t(lang, "It changes by day")], **common,
        )

    session.awaiting = None
    hours = session.hours_per_weekday()
    unspecified = [d for d in range(7) if d not in session.availability and d not in session.blocked]
    if unspecified and len(unspecified) < 7:
        assumptions = assumptions + [t(lang, "No study time is planned on {days} because none was given.", days=_day_list(unspecified, lang))]
    schedule, warnings, schedule_assumptions = build_schedule(session.tasks, hours, today, lang, session.dependencies)
    session.schedule = schedule
    message = note + t(lang, "Here is a draft schedule. Change anything that looks wrong before you add it to your plan.")
    suggestions = [t(lang, "Show my plan"), t(lang, "reset")]
    if warnings:
        suggestions.insert(0, _more_time_suggestion(session, today))
    return _response(
        "planning", message, session, schedule=schedule, warnings=warnings,
        assumptions=assumptions + estimates + schedule_assumptions, suggestions=suggestions, **common,
    )


def _more_time_suggestion(session: Session, today: date) -> str:
    """Suggest study time on a free day before the latest deadline, or more hours per day."""
    lang = session.lang
    hours = session.hours_per_weekday()
    ends = [task.last_work_day() for task in session.tasks if task.status != "done" and task.last_work_day()]
    for offset in range(((max(ends) - today).days + 1) if ends else 0):
        day = date.fromordinal(today.toordinal() + offset)
        if not hours.get(day.weekday()) and day.weekday() not in session.blocked:
            name = ("thứ " + ["hai", "ba", "tư", "năm", "sáu", "bảy"][day.weekday()]) if lang == "vi" and day.weekday() < 6 else (
                "chủ nhật" if lang == "vi" else DAY_NAMES[day.weekday()].title())
            return t(lang, "2 hours on {day}", day=name)
    return t(lang, "{hours} hours per day", hours=f"{max(hours.values(), default=2) + 1:g}")


def _match_task(session: Session, words: str) -> Task | None:
    """The task whose title shares the most words with the text; '2' or 'task 2' picks by number."""
    number = re.fullmatch(r"(?:task |việc |#)?(\d+)", words.strip())
    if number:
        return _task(session, int(number.group(1)))
    query = knowledge.words(words)
    best, best_score = None, 0
    for task in session.tasks:
        score = len(query & knowledge.words(task.title))
        if score > best_score:
            best, best_score = task, score
    return best


def _tasks_from_llm(data: dict, today: date, lang: str) -> tuple[list[Task], float | None]:
    """Validate model output field by field; anything malformed is dropped."""
    tasks = []
    for item in data.get("tasks") or []:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
            continue
        found = task_kind(item["title"])
        kind = item.get("kind") if item.get("kind") in {"exam", "quiz", "assignment", "project", "presentation", "reading", "review"} else (found[0] if found else "other")
        task = Task(title=item["title"].strip()[:120], kind=kind, hours=found[1] if found else 2.0, source="llm")
        try:
            task.deadline = date.fromisoformat(item["deadline"]) if item.get("deadline") else None
        except (TypeError, ValueError):
            task.deadline = None
        hours = item.get("hours")
        if isinstance(hours, (int, float)) and 0 < hours <= 40:
            task.hours, task.hours_assumed = float(hours), False
        set_priority(task, today, lang)
        tasks.append(task)
    per_day = data.get("hours_per_day")
    per_day = float(per_day) if isinstance(per_day, (int, float)) and 0 < per_day <= 16 else None
    return tasks, per_day


# ---------------------------------------------------------------- knowledge (Feature 2)

def _knowledge(text: str, lowered: str, session: Session) -> dict | None:
    lang = session.lang
    m = knowledge.SAVE_RE.match(text)
    if m:
        note = knowledge.parse_note(m.group("body"), m.group("kind").lower())
        if note is None:
            return _response("knowledge", t(lang, "Tell me what to save, for example: save note: Derivatives - the derivative of x^2 is 2x #calculus. A link needs an address starting with http:// or https://."), session)
        session.add_note(note)
        return _response("knowledge", t(lang, "Saved note #{id}: {title}.", id=note.id, title=note.title), session,
                         notes=[note.to_dict()], citations=knowledge.citations([note]),
                         suggestions=[t(lang, "Show my notes"), t(lang, "quiz me on {topic}", topic=note.title)])
    if knowledge.LIST_RE.match(lowered):
        if not session.notes:
            return _response("knowledge", t(lang, "You have no saved notes yet."), session, suggestions=EXAMPLES[lang][1:2])
        lines = "\n".join(knowledge.describe(n, lang) for n in session.notes)
        return _response("knowledge", t(lang, "Your notes:") + "\n" + lines, session,
                         notes=[n.to_dict() for n in session.notes], citations=knowledge.citations(session.notes))
    m = knowledge.SEARCH_RE.match(lowered)
    if m and not session.notes:
        return _response("knowledge", t(lang, "You have no saved notes yet."), session, suggestions=EXAMPLES[lang][1:2])
    if m:
        query = m.group("q") or m.group("tag")
        found = knowledge.search(session.notes, query)
        if not found:
            return _response("knowledge", t(lang, "No saved note matches \"{query}\". I only search notes you saved, so I have no source for it.", query=query),
                             session, suggestions=[t(lang, "Show my notes")])
        lines = "\n".join(knowledge.describe(n, lang) + ("\n   " + n.content[:200] if n.content else "") for n in found[:5])
        return _response("knowledge", t(lang, "Notes about \"{query}\":", query=query) + "\n" + lines, session,
                         notes=[n.to_dict() for n in found[:5]], citations=knowledge.citations(found[:5]))
    m = knowledge.LINK_RE.match(lowered)
    if m:
        note_id = int(m.group("note") or m.group("note2"))
        note = next((n for n in session.notes if n.id == note_id), None)
        task = _match_task(session, m.group("task") or m.group("task2"))
        if note is None or task is None:
            return _response("knowledge", t(lang, "I couldn't find that note or task. Check the numbers with \"show my notes\" and \"show my plan\"."), session)
        session.links.add((task.id, note.id))
        return _response("knowledge", t(lang, "Linked note #{note} to \"{task}\".", note=note.id, task=task.title), session,
                         notes=[note.to_dict()], citations=knowledge.citations([note]))
    m = knowledge.DELETE_RE.match(lowered)
    if m:
        note_id = int(m.group("id") or m.group("id2"))
        if not any(n.id == note_id for n in session.notes):
            return _response("knowledge", t(lang, "There is no note #{id}.", id=note_id), session, suggestions=[t(lang, "Show my notes")])
        session.notes = [n for n in session.notes if n.id != note_id]
        session.links = {(a, b) for a, b in session.links if b != note_id}
        for item in session.studies:
            item.item_ids = [i for i in item.item_ids if i != note_id]
        return _response("knowledge", t(lang, "Deleted note #{id}.", id=note_id), session)
    return None


# ---------------------------------------------------------------- study (Feature 3)

def _question_response(session: Session, item: Study, prefix: str, **extra) -> dict:
    lang = session.lang
    q = item.questions[item.current]
    message = prefix + t(lang, "Question {n}/{total}: {question}", n=item.current + 1, total=len(item.questions), question=q["question"])
    return _response("study", message.strip(), session, study=item.to_dict(),
                     suggestions=[t(lang, "skip"), t(lang, "stop")], **extra)


def _start_study(topic: str, session: Session, today: date, provider) -> dict:
    lang = session.lang
    by_id = study.NOTE_ID_RE.match(topic)
    if by_id:
        notes = [n for n in session.notes if n.id == int(by_id.group(1))]
        if not notes:
            return _response("study", t(lang, "There is no note #{id}.", id=by_id.group(1)), session, suggestions=[t(lang, "Show my notes")])
        topic = notes[0].title
    else:
        notes = knowledge.search(session.notes, topic)[:2]
    item, text, warnings, assumptions = study.build(topic, notes, lang, provider)
    if item is None:
        if not notes:
            return _response("clarification", t(lang, "I have no material on \"{topic}\" yet. Save a note first, for example: save note: {topic} - what you learned.", topic=topic),
                             session, warnings=warnings, suggestions=EXAMPLES[lang][1:2])
        return _response("study", t(lang, "That note is too short to make questions from. Add a few full sentences to it."), session, warnings=warnings)
    session.add_study(item)
    session.awaiting = "study_answer"
    prefix = (t(lang, "Summary: {text}", text=text) + "\n\n") if text else ""
    return _question_response(session, item, prefix, warnings=warnings, assumptions=session.assumptions + assumptions,
                              citations=knowledge.citations(notes))


def _answer_study(text: str, item: Study, session: Session, today: date, provider) -> dict:
    lang = session.lang
    feedback = study.grade(item, text, lang, provider)
    if not item.finished:
        return _question_response(session, item, feedback + "\n\n")
    session.awaiting = None
    study.finish(item, today)
    message = feedback + "\n\n" + t(lang, "You got {score} right. I suggest reviewing {topic} on {date}. Add that review to your plan?",
                                    score=item.progress(), topic=item.topic, date=format_day(item.review_due, lang))
    return _response("study", message, session, study=item.to_dict(),
                     suggestions=[t(lang, "add review to plan"), t(lang, "Show my plan")])


# ---------------------------------------------------------------- router

def process_request(user_input: str, session: Session | None = None, today: date | None = None, provider=None) -> dict:
    """Route one message and return a structured response.

    Raises ValueError for empty or non-string input. ``session`` keeps tasks, notes and
    study sessions between messages; ``today`` and ``provider`` are injectable for tests.
    """
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError(t(session.lang if session else "en", "Please type a request."))
    session = session if session is not None else Session()
    today = today or date.today()
    text = user_input.strip()
    lowered = re.sub(r"\s+", " ", text.lower()).strip(" ?!.")
    if session.awaiting != "study_answer":  # a quiz answer such as "photosynthesis" keeps the quiz language
        session.lang = i18n.detect(text, session.lang)
    lang = session.lang

    if lowered in GREETINGS:
        return _response("greeting", t(lang, "Hello! Tell me what you need to get done, save a note, or type \"help\"."), session, suggestions=EXAMPLES[lang])
    if HELP_RE.match(lowered):
        return _response("help", t(lang, "help_text"), session, suggestions=EXAMPLES[lang][:3])
    if RESET_RE.match(lowered):
        session.reset_plan()
        return _response("reset", t(lang, "Your plan is cleared. Your saved notes are kept. What do you need to do?"), session, suggestions=EXAMPLES[lang][:1])

    active = session.active_study()
    if active and study.STOP_RE.match(lowered):
        session.awaiting = None
        return _response("study", t(lang, "Quiz stopped. You answered {done} of {total} questions.", done=active.current, total=len(active.questions)),
                         session, study=active.to_dict())
    if active:
        return _answer_study(text, active, session, today, provider)

    if SHOW_RE.match(lowered):
        if not session.tasks:
            return _response("planning", t(lang, "You have no tasks yet. Tell me what you need to do and when it is due."), session, suggestions=EXAMPLES[lang][:1])
        return _plan_response(session, today, [], [])
    if study.ADD_REVIEW_RE.match(lowered):
        last = session.studies[-1] if session.studies else None
        if last is None or last.review_due is None:
            return _response("study", t(lang, "Finish a quiz first, then I can add a review to your plan."), session, suggestions=[t(lang, "Show my notes")])
        task = study.review_task(last, lang)
        session.add_task(task)
        set_priority(task, today, lang)
        for note_id in last.item_ids:
            session.links.add((task.id, note_id))
        return _plan_response(session, today, [], [], note=t(lang, "Added \"{title}\" to your plan. ", title=task.title))

    handled = _knowledge(text, lowered, session)
    if handled:
        return handled

    done = DONE_RE.match(lowered)
    if done and not session.tasks:
        return _response("planning", t(lang, "You have no tasks yet, so there is nothing to mark as done."), session, suggestions=EXAMPLES[lang][:1])
    if done:
        task = _match_task(session, next(g for g in done.groups() if g))
        if task is None:
            return _response("planning", t(lang, "I couldn't find that task in your plan."), session, suggestions=[t(lang, "Show my plan")])
        task.status = "done"
        return _plan_response(session, today, [], [], note=t(lang, "Marked \"{title}\" as done. ", title=task.title))

    depends = DEPENDS_RE.match(lowered) if len(session.tasks) >= 2 else None
    if depends:
        a, b = _match_task(session, depends.group("a")), _match_task(session, depends.group("b"))
        if a and b and a.id != b.id:
            session.dependencies.add((a.id, b.id))
            return _plan_response(session, today, [], [], note=t(lang, "\"{task}\" will start after \"{dep}\" is finished. ", task=a.title, dep=b.title))

    start = study.START_RE.match(lowered)
    topic = start and (start.group("topic") or start.group("topic2"))
    if topic and not (DEADLINE_RE.search(topic) or DURATION_RE.search(topic)):
        return _start_study(topic, session, today, provider)

    if OFFICE_QUESTION_RE.search(lowered):
        answer = offices.answer(text, lang=lang)
        if answer:
            return _response("office", answer, session)

    parsed = parse(text, today, awaiting_availability=session.awaiting == "availability", lang=lang)
    warnings: list[str] = []
    nothing = not (parsed.tasks or parsed.availability or parsed.blocked)
    # A long title means the rules swallowed a casual sentence ("lo vụ lab hóa với cái slide..."): ask the model.
    misread = any(len(task.title.split()) > MAX_TITLE_WORDS for task in parsed.tasks)
    if (nothing or misread) and provider and PLANNING_HINT_RE.search(lowered):
        try:
            tasks, per_day = _tasks_from_llm(llm.extract_plan(provider, text, today), today, lang)
            if tasks or nothing:
                parsed.tasks = tasks
                parsed.highlights = [h for h in parsed.highlights if h["kind"] != "task"]
            if per_day and not parsed.availability:
                parsed.availability = {d: per_day for d in range(7)}
            if tasks:
                parsed.assumptions.append(t(lang, "Tasks were read by the {name} language model. Check them before relying on the plan.", name=provider.name))
        except llm.LLMError as exc:
            warnings.append(t(lang, "The AI service is unavailable ({error}). Only rule-based reading was used.", error=exc))

    if parsed.tasks or parsed.availability or parsed.blocked:
        if parsed.tasks and not session.user_goal:
            session.user_goal = text[:500]
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
            t(lang, "Tell me the hours for each day, for example: \"2 hours on weekdays, 4 hours on Sunday\"."),
            session,
            suggestions=[t(lang, "2 hours on weekdays, 4 hours on Sunday")],
        )
    return _response("fallback", t(lang, "fallback_text"), session, warnings=warnings, suggestions=EXAMPLES[lang])

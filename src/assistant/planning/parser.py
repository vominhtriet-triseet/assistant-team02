"""Rule-based extraction of tasks, deadlines, durations, and study availability.

The parser only reads what the student wrote. Anything it has to guess, such as a
task duration or which week "next Wednesday" means, is returned as an assumption.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from assistant.i18n import t
from assistant.planning.models import ParseResult, Task

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ALIASES = {
    "mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3, "thurs": 3, "fri": 4, "sat": 5, "sun": 6,
    **{name: i for i, name in enumerate(DAY_NAMES)},
    "thứ hai": 0, "thứ 2": 0, "thứ ba": 1, "thứ 3": 1, "thứ tư": 2, "thứ 4": 2, "thứ năm": 3, "thứ 5": 3,
    "thứ sáu": 4, "thứ 6": 4, "thứ bảy": 5, "thứ 7": 5, "chủ nhật": 6, "cn": 6,
}
VI_DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
EXAM_PREFIX = {"en": "Prepare for ", "vi": "Ôn tập: "}
DAY_PATTERN = "|".join(sorted(DAY_ALIASES, key=len, reverse=True))
WEEKDAYS, WEEKEND, ALL_DAYS = set(range(5)), {5, 6}, set(range(7))

# (kind, pattern, default hours). The first match wins, so exams come before reviews.
KINDS = [
    ("quiz", r"\b(?:quiz(?:zes)?|kiểm tra ngắn)\b", 2.0),
    ("exam", r"\b(?:(?:exam|midterm|final|test)s?|thi|kiểm tra|giữa kỳ|cuối kỳ)\b", 8.0),
    ("project", r"\b(?:projects?|đồ án|dự án)\b", 6.0),
    ("presentation", r"\b(?:presentation|slides?|talk|thuyết trình)\b", 3.0),
    ("assignment", r"\b(?:(?:assignment|homework|problem set|exercises?|lab|report|essay)s?|bài tập|báo cáo|tiểu luận|bài luận|bài thực hành)\b", 4.0),
    ("reading", r"\b(?:read|reading|chapter|đọc|chương)\b", 2.0),
    ("review", r"\b(?:review|revise|study|practi[cs]e|learn|ôn tập|ôn|luyện|học bài)\b", 2.0),
]

PREP = r"(?:(?:due|by|before|on|until|hạn chót|hạn nộp|hạn|nộp vào|nộp|trước|vào)\s+)?"
DEADLINE_RE = re.compile(
    PREP + rf"(?:\b(?P<rel>next|this)\s+)?\b(?P<day>{DAY_PATTERN})\b(?:\s+(?P<relvi>tuần sau|tuần tới|tuần này))?"
    r"|" + PREP + r"\b(?P<word>today|tonight|tomorrow|hôm nay|tối nay|ngày mai|sáng mai|tối mai|mai|cuối tuần(?: này)?)\b"
    r"|" + PREP + r"\b(?:in\s+(?P<n>\d+)\s+days?|(?:trong\s+)?(?P<n2>\d+)\s+ngày\s+nữa)\b"
    r"|" + PREP + r"\b(?P<iso>\d{4}-\d{2}-\d{2})\b"
    r"|" + PREP + r"\b(?P<dd>\d{1,2})/(?P<mm>\d{1,2})\b",
    re.I,
)
TIME_RE = re.compile(
    r"(?:(?:by|before|at|until)\s+)?\b(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm)\b"
    r"|(?:(?:by|before|at|until|lúc|trước)\s+)?\b(?P<h24>\d{1,2}):(?P<m24>\d{2})\b"
    # Vietnamese: "5 giờ chiều", "lúc 17h", "17h30". A bare "3h" stays a duration.
    r"|(?:(?:lúc|trước)\s+)?\b(?P<hv>\d{1,2})\s*(?:giờ|h)\s*(?P<mv>\d{2})?\s*(?P<pv>sáng|trưa|chiều|tối)\b"
    r"|\blúc\s+(?P<hl>\d{1,2})\s*(?:giờ|h)(?P<ml>\d{2})?\b"
    r"|(?:(?:lúc|trước)\s+)?\b(?P<hh>\d{1,2})h(?P<mh>\d{2})\b",
    re.I,
)
DURATION_RE = re.compile(
    r"(?:\b(?:for|about|around|khoảng|tầm|mất)\s+|~)?\b(?P<n>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>hours?|hrs?|h|minutes?|mins?|tiếng|giờ|phút)\b", re.I
)
VI_STUDY_TIME = r"có thể học|học được|mỗi ngày|một ngày|1 ngày|hằng ngày|hàng ngày|mỗi tối"
AVAILABILITY_HINT = re.compile(
    rf"\b(?:per day|a day|each day|every day|daily|a night|weekdays?|weekends?|can study|can work|free"
    rf"|{VI_STUDY_TIME}|ngày thường|cuối tuần|trong tuần|rảnh)\b"
    rf"|\b(?:(?:on|vào)\s+)?(?:{DAY_PATTERN})\b",  # "4 tiếng chủ nhật": a duration next to a day, no task named
    re.I,
)
# "I can study 2 hours a day" is about study time even though it contains "study".
STUDY_TIME_RE = re.compile(rf"\b(?:can study|can work|per day|a day|each day|every day|daily|{VI_STUDY_TIME})\b", re.I)
BLOCKED_RE = re.compile(
    r"\b(?:busy|not free|not available|unavailable|no time|can't study|cannot study|none|no study|day off|off"
    r"|bận|không rảnh|không học|kín lịch|nghỉ)\b", re.I
)
PRIORITY_HIGH = re.compile(r"\b(?:urgent|asap|important|high priority|gấp|quan trọng|khẩn cấp|ưu tiên cao)\b", re.I)
PRIORITY_LOW = re.compile(r"\b(?:low priority|không gấp|không quan trọng|ưu tiên thấp)\b", re.I)
SPLIT_RE = re.compile(r",|;|\band\b|\bthen\b|\bbut\b|\bvà\b|\brồi\b|\bnhưng\b|\bcòn\b|\bvới cả\b|\bvới\b", re.I)
LEADING_WORDS = [
    r"(?:so|also|then|and|but|plus|please)\b",
    r"(?:can|could|would|will) you(?: please)?(?: help me)?(?: to)?\b",
    r"help me(?: to)?\b",
    r"(?:i|we)(?:'ve|'ll|'m)?\b",
    r"(?:have got|have to|need to|must|should|want to|got to|am going to|going to|will|have|has|got)\b",
    r"(?:get ready for|be ready for|prepare for)\b",
    r"to\b",
    r"(?:a|an|my|the|our|some)\b",
    r"(?:there is|there's)\b",
    r"(?:tuần này|tôi|mình|em|tui|chúng tôi|bọn mình)\b",
    r"(?:cần|phải|sẽ|có|muốn|đang|còn|thì|là|với|hãy|giúp(?: tôi| mình| em)?|làm|hoàn thành|nộp|chuẩn bị|lo|vụ)\b",
    r"(?:một|cái|các|những)\b",
]
# Also drops what is left of "it takes 3 hours" once the duration has been read.
TRAILING_WORDS = re.compile(
    r"\s*\b(?:due|by|before|on|until|for|at|is|which|that|in|next|this|it|takes?|needs?|lasts?|will|should"
    r"|both|was|were|hạn chót|hạn nộp|hạn|vào|trước|lúc|mất|khoảng|tầm|cần|trong|nộp|là|thì|kéo dài|sẽ|nhé|nha|ạ|cả hai)\s*$", re.I
)


def format_day(day: date, lang: str = "en") -> str:
    if lang == "vi":
        return f"{VI_DAYS[day.weekday()]} {day.day}/{day.month}"
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"


def exam_name(title: str) -> str:
    """"Prepare for X" / "Ôn tập: X" -> "X"."""
    for prefix in EXAM_PREFIX.values():
        title = title.removeprefix(prefix)
    return title


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
    if re.search(r"\b(?:weekdays?|ngày thường|trong tuần)\b", lowered):
        days |= WEEKDAYS
    if re.search(r"\b(?:weekends?|cuối tuần)\b", lowered):
        days |= WEEKEND
    days |= {DAY_ALIASES[m] for m in re.findall(rf"\b({DAY_PATTERN})\b", lowered)}
    return days


def _hours(match: re.Match) -> float:
    value = float(match.group("n"))
    unit = match.group("unit").lower()
    return value / 60 if unit.startswith("m") or unit == "phút" else value


def _resolve_date(m: re.Match, today: date, assumptions: list[str], lang: str = "en") -> date | None:
    if m.group("day"):
        target = DAY_ALIASES[m.group("day").lower()]
        relvi = (m.group("relvi") or "").lower()
        if relvi:  # "thứ 4 tuần sau" means that weekday in the next calendar week
            monday = today - timedelta(days=today.weekday()) + timedelta(days=0 if relvi == "tuần này" else 7)
            return monday + timedelta(days=target)
        delta = (target - today.weekday()) % 7
        if m.group("rel") and m.group("rel").lower() == "next":
            delta = delta or 7
            day = today + timedelta(days=delta)
            assumptions.append(t(lang, "Read 'next {day}' as {date}.", day=DAY_NAMES[target].title(), date=format_day(day, lang)))
            return day
        return today + timedelta(days=delta)
    if m.group("word") and m.group("word").lower().startswith("cuối tuần"):
        day = today + timedelta(days=6 - today.weekday())  # this week's Sunday
        assumptions.append(t(lang, "Read '{phrase}' as {date}.", phrase=m.group("word"), date=format_day(day, lang)))
        return day
    if m.group("word"):
        return today + timedelta(days=0 if m.group("word").lower() in ("today", "tonight", "hôm nay", "tối nay") else 1)
    if m.group("n") or m.group("n2"):
        return today + timedelta(days=int(m.group("n") or m.group("n2")))
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
    assumptions.append(t(lang, "Read {dm} as {date} (day/month).", dm=f"{m.group('dd')}/{m.group('mm')}", date=format_day(day, lang)))
    return day


def _clean_title(text: str) -> str:
    text = re.sub(r"\(\s*\)|\[\s*\]", " ", text)  # brackets emptied by removing "(3 hours)"
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
    text = re.sub(r"\b(?:my|our)\s+|\s+của (?:tôi|mình|em)\b", "", text, flags=re.I).strip(" .,!?;:-")
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


def _time_of(m: re.Match) -> tuple[int, int]:
    hour = int(m.group("h") or m.group("h24") or m.group("hv") or m.group("hl") or m.group("hh"))
    minute = int(m.group("m") or m.group("m24") or m.group("mv") or m.group("ml") or m.group("mh") or 0)
    if m.group("ap"):
        hour = hour % 12 + (12 if m.group("ap").lower() == "pm" else 0)
    period = (m.group("pv") or "").lower()
    if (period in ("chiều", "tối") and hour < 12) or (period == "trưa" and hour < 11):
        hour += 12
    return hour, minute


def _parse_task(clause: str, today: date, result: ParseResult, lang: str = "en") -> Task | None:
    found = task_kind(clause)
    if not found:
        return None
    kind, default_hours = found
    work = clause
    task = Task(title="", kind=kind, hours=default_hours)

    m = DEADLINE_RE.search(work)
    if m:
        task.deadline = _resolve_date(m, today, result.assumptions, lang)
        result.highlights.append({"text": m.group(0).strip(), "kind": "date"})
        work = work[: m.start()] + " " + work[m.end():]
    tm = TIME_RE.search(work)
    if tm:
        hour, minute = _time_of(tm)
        task.deadline_time = f"{hour:02d}:{minute:02d}"
        result.highlights.append({"text": tm.group(0).strip(), "kind": "date"})
        work = work[: tm.start()] + " " + work[tm.end():]
        if task.deadline is None:
            task.deadline = today
            result.assumptions.append(t(lang, "No date was given for the {time} deadline, so it is read as today.", time=task.deadline_time))
    d = DURATION_RE.search(work)
    if d:
        task.hours, task.hours_assumed = _hours(d), False
        result.highlights.append({"text": d.group(0).strip(), "kind": "time"})
        work = work[: d.start()] + " " + work[d.end():]
    # Low first: "không gấp" (not urgent) contains "gấp" (urgent).
    if PRIORITY_LOW.search(work):
        task.priority, task.priority_reason = "low", t(lang, "marked as low priority")
        work = PRIORITY_LOW.sub(" ", work)
    elif PRIORITY_HIGH.search(work):
        task.priority, task.priority_reason = "high", t(lang, "marked as important")
        work = PRIORITY_HIGH.sub(" ", work)

    name = _clean_title(work)
    if len(name.split()) < 2 and task.deadline is None and task.hours_assumed:
        return None  # e.g. "Can you help me study?" carries no task details
    if name.lower() in clause.lower():
        result.highlights.append({"text": clause[clause.lower().index(name.lower()):][: len(name)], "kind": "task"})
    if kind in ("exam", "quiz") and not re.match(r"(?:prepare|review|study|revise|ôn)\b", name, re.I):
        name = EXAM_PREFIX[lang] + name
    task.title = name
    if not task.priority_reason:
        set_priority(task, today, lang)
    return task


MARKED = {t(lang, s) for lang in ("en", "vi") for s in ("marked as important", "marked as low priority")}


def set_priority(task: Task, today: date, lang: str = "en") -> None:
    if task.priority_reason in MARKED:
        return
    if task.deadline is None:
        task.priority, task.priority_reason = "low", t(lang, "no deadline given")
        return
    days = (task.deadline - today).days
    if days <= 2:
        task.priority, task.priority_reason = "high", t(lang, "due within 2 days")
    elif days <= 5:
        task.priority, task.priority_reason = "medium", t(lang, "due within 5 days")
    else:
        task.priority, task.priority_reason = "low", t(lang, "due in {days} days", days=days)


def _parse_availability(segment: str, result: ParseResult, bare_ok: bool) -> tuple | None:
    """Read study time or busy days from one segment.

    Returns the rule it applied, ("hours", h) or ("busy", None), so a following list of
    bare day names can continue it; None when the segment is not about availability.
    """
    if task_kind(segment) and not STUDY_TIME_RE.search(segment):
        return None
    m = DURATION_RE.search(segment)
    if m and (AVAILABILITY_HINT.search(segment) or bare_ok):
        for day in _day_scope(segment) or ALL_DAYS:
            result.availability[day] = _hours(m)
        result.highlights.append({"text": m.group(0).strip(), "kind": "time"})
        return ("hours", _hours(m))
    if BLOCKED_RE.search(segment):
        days = _day_scope(segment)
        if days:
            result.blocked |= days
            return ("busy", None)
    return None


# What is left of a segment such as " Tuesday" or " and on Wednesday" once day names are removed.
DAYS_ONLY_RE = re.compile(rf"\b(?:{DAY_PATTERN}|weekdays?|weekends?|ngày thường|cuối tuần|on|vào|only|also|too|cũng)\b|\W", re.I)


def parse(text: str, today: date, awaiting_availability: bool = False, lang: str = "en") -> ParseResult:
    result = ParseResult()
    for sentence in (s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text)):
        if not sentence:
            continue
        # A bare "3 hours" answers the study-time question, unless the sentence also names a task.
        bare_ok = awaiting_availability and not task_kind(sentence)
        remaining = [seg for seg in SPLIT_RE.split(sentence) if seg and seg.strip()]
        kept, rule = [], None
        for seg in remaining:
            days = _day_scope(seg)
            if rule and days and not DAYS_ONLY_RE.sub("", seg).strip():
                # "busy on Monday, Tuesday and Wednesday": the rule carries over a list of day names
                if rule[0] == "busy":
                    result.blocked |= days
                else:
                    result.availability.update({day: rule[1] for day in days})
                continue
            rule = _parse_availability(seg, result, bare_ok)
            if not rule:
                kept.append(seg)
        if len(kept) != len(remaining):
            sentence = " and ".join(seg.strip() for seg in kept)
        found = [task for task in (_parse_task(c, today, result, lang) for c in _clauses(sentence)) if task]
        # "lab and slides, due on the weekend": a deadline closing the sentence covers every task in it.
        tail = SPLIT_RE.split(sentence)[-1]
        if len(found) > 1 and found[-1].deadline and DEADLINE_RE.search(tail) and not task_kind(tail):
            for task in found[:-1]:
                if task.deadline is None:
                    task.deadline, task.deadline_time = found[-1].deadline, found[-1].deadline_time
                    set_priority(task, today, lang)
        result.tasks.extend(found)
    return result

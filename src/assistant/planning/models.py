"""Data types shared by the parser, scheduler, and service."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
EXAM_KINDS = {"exam", "quiz"}


@dataclass
class Task:
    title: str
    kind: str = "other"
    deadline: date | None = None
    deadline_time: str | None = None
    hours: float = 2.0
    hours_assumed: bool = True
    priority: str = "low"
    priority_reason: str = ""
    status: str = "pending"
    id: int = 0
    source: str = "user"  # user, llm (read by the model), or system (suggested by the assistant)

    def last_work_day(self) -> date | None:
        """The last day work can be scheduled: the day before an exam, otherwise the due date."""
        if self.deadline is None:
            return None
        if self.kind in EXAM_KINDS:
            return date.fromordinal(self.deadline.toordinal() - 1)
        return self.deadline

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "deadline_time": self.deadline_time,
            "hours": self.hours,
            "hours_assumed": self.hours_assumed,
            "priority": self.priority,
            "status": self.status,
            "source": self.source,
        }


@dataclass
class ParseResult:
    tasks: list[Task] = field(default_factory=list)
    availability: dict[int, float] = field(default_factory=dict)
    blocked: set[int] = field(default_factory=set)
    assumptions: list[str] = field(default_factory=list)
    highlights: list[dict] = field(default_factory=list)


@dataclass
class Note:
    """A knowledge item the student saved: a note, a link, or pasted text."""

    title: str
    content: str = ""
    source_url: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    id: int = 0

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "content": self.content,
                "source_url": self.source_url, "tags": self.tags, "created_at": self.created_at}


@dataclass
class Study:
    """One study session: material, practice questions, and the result."""

    topic: str
    item_ids: list[int] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)  # {"question", "answer", "correct": bool | None}
    current: int = 0
    review_notes: str = ""
    review_due: date | None = None
    started_at: str = ""
    id: int = 0

    @property
    def correct(self) -> int:
        return sum(1 for q in self.questions if q.get("correct"))

    @property
    def finished(self) -> bool:
        return self.current >= len(self.questions)

    def progress(self) -> str:
        return f"{self.correct}/{len(self.questions)}"

    def to_dict(self) -> dict:
        return {"id": self.id, "topic": self.topic, "item_ids": self.item_ids, "progress": self.progress(),
                "question_count": len(self.questions), "current": self.current, "finished": self.finished,
                "review_notes": self.review_notes,
                "review_due": self.review_due.isoformat() if self.review_due else None}

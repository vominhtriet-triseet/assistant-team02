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
        }


@dataclass
class Availability:
    """Study hours for each weekday (0 = Monday)."""

    hours: dict[int, float] = field(default_factory=dict)

    def known(self) -> bool:
        return bool(self.hours)

    def for_day(self, day: date) -> float:
        return self.hours.get(day.weekday(), 0.0)


@dataclass
class ParseResult:
    tasks: list[Task] = field(default_factory=list)
    availability: dict[int, float] = field(default_factory=dict)
    blocked: set[int] = field(default_factory=set)
    assumptions: list[str] = field(default_factory=list)
    highlights: list[dict] = field(default_factory=list)

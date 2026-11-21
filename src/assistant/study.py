"""Feature 3, study support: a short quiz from the student's notes, feedback, and a review task.

Without a language model the questions are fill-in-the-blank sentences taken from the
note (retrieval practice). With a model, it writes a summary and questions from the same
material and grades free-text answers; its output is validated like the planning output.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from assistant import llm
from assistant.i18n import t
from assistant.knowledge import STOP, fold
from assistant.planning.models import Note, Study, Task

START_RE = re.compile(
    r"^(?:quiz me|test me|kiểm tra tôi|hỏi tôi|đố tôi)(?: on| about| về)?\s+(?P<topic>.+)$"
    r"|^(?:study|practice|học|ôn tập|ôn|luyện)\s+(?P<topic2>.+)$"
)
NOTE_ID_RE = re.compile(r"^(?:note|ghi chú)\s+#?(\d+)$")
STOP_RE = re.compile(r"^(?:stop|stop quiz|end quiz|quit quiz|dừng|dừng lại|thôi|kết thúc)$")
SKIP_RE = re.compile(r"^(?:skip|pass|i don't know|idk|bỏ qua|không biết|chịu)$")
ADD_REVIEW_RE = re.compile(
    r"^(?:add (?:the |this )?review(?: task)? to (?:my )?plan|yes,? add (?:it|the review)"
    r"|thêm (?:bài |việc )?ôn tập vào kế hoạch|thêm vào kế hoạch)$"
)
QUESTION_COUNT = 3


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def summary(material: str) -> str:
    text = " ".join(_sentences(material)[:2])
    return text if len(text) <= 300 else text[:297].rsplit(" ", 1)[0] + "..."


def cloze_questions(material: str, title_words: set[str], lang: str) -> list[dict]:
    """Hide the last key term of each sentence, usually its object ("...into chemical energy").

    Words from the note title are never hidden: the quiz topic already gives them away.
    Vietnamese words are two syllables more often than not, so two tokens are hidden there.
    ponytail: positional heuristic, no part-of-speech tagging; the language model writes better questions.
    """
    questions = []
    for sentence in _sentences(material):
        tokens = re.findall(r"\w+", sentence)
        if len(tokens) < 5:
            continue
        keep = [i for i, w in enumerate(tokens) if fold(w) not in STOP and fold(w) not in title_words and len(w) >= 2]
        if not keep:
            continue
        last = keep[-1]
        start = last - 1 if lang == "vi" and last - 1 in keep and not tokens[last].isdigit() else last
        answer = " ".join(tokens[start:last + 1])
        pattern = r"\b" + r"\W+".join(re.escape(w) for w in tokens[start:last + 1]) + r"\b"
        blank = re.sub(pattern, "_____", sentence, count=1)
        questions.append({"question": blank, "answer": answer, "correct": None})
        if len(questions) == QUESTION_COUNT:
            break
    return questions


def _clean_questions(items) -> list[dict]:
    """Validate model questions: text only, short, at most QUESTION_COUNT."""
    questions = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and isinstance(item.get("question"), str) and isinstance(item.get("answer"), str):
            q, a = item["question"].strip()[:300], item["answer"].strip()[:300]
            if q and a:
                questions.append({"question": q, "answer": a, "correct": None})
    return questions[:QUESTION_COUNT]


def build(topic: str, notes: list[Note], lang: str, provider=None) -> tuple[Study | None, str, list[str], list[str]]:
    """Return (study, summary text, warnings, assumptions). study is None when there is nothing to practise."""
    warnings: list[str] = []
    assumptions: list[str] = []
    material = "\n".join(f"{n.title}. {n.content}" for n in notes)
    study = Study(topic=notes[0].title if notes else topic, item_ids=[n.id for n in notes])
    text = summary("\n".join(n.content or n.title for n in notes))
    if provider is not None:
        try:
            data = llm.study_pack(provider, topic, material, lang)
            questions = _clean_questions(data.get("questions"))
            if questions:
                study.questions = questions
                if isinstance(data.get("summary"), str) and data["summary"].strip():
                    text = data["summary"].strip()[:800]
                note = ("Questions were written by the {name} model from your notes." if notes else
                        "You have no notes on this topic, so the {name} model wrote these questions from general knowledge. Check them against your course material.")
                assumptions.append(t(lang, note, name=provider.name))
        except llm.LLMError as exc:
            warnings.append(t(lang, "The AI service is unavailable ({error}). Only rule-based reading was used.", error=exc))
    if not study.questions and notes:
        study.questions = cloze_questions(material, {fold(w) for n in notes for w in re.findall(r"\w+", n.title)}, lang)
    return (study if study.questions else None), text, warnings, assumptions


def grade(study: Study, reply: str, lang: str, provider=None) -> str:
    """Grade the current question, move to the next one, and return feedback."""
    q = study.questions[study.current]
    expected = q["answer"]
    feedback = ""
    if SKIP_RE.match(reply.lower().strip(" .!?")):
        q["correct"] = False
    elif provider is not None:
        try:
            data = llm.grade(provider, q["question"], expected, reply, lang)
            q["correct"] = data.get("correct") is True
            if isinstance(data.get("feedback"), str):
                feedback = data["feedback"].strip()[:300]
        except llm.LLMError:
            q["correct"] = None
    if q.get("correct") is None:
        got, want = fold(reply).strip(" .!?"), fold(expected)
        got_words = " ".join(re.findall(r"\w+", got))  # backslashes in f-strings need Python 3.12
        q["correct"] = got == want or f" {want} " in f" {got_words} "
    study.current += 1
    if q["correct"]:
        return feedback or t(lang, "Correct!")
    return t(lang, "Not quite. The answer is: {answer}.", answer=expected) + (f" {feedback}" if feedback else "")


def finish(study: Study, today: date) -> None:
    ratio = study.correct / len(study.questions)
    study.review_due = today + timedelta(days=1 if ratio < 0.6 else 3)
    study.review_notes = "; ".join(q["question"] for q in study.questions if not q["correct"])[:500]


def review_task(study: Study, lang: str) -> Task:
    return Task(title=t(lang, "Review {topic}", topic=study.topic)[:120], kind="review",
                deadline=study.review_due, hours=1.0, source="system")


if __name__ == "__main__":
    note = Note(title="Photosynthesis", content="Photosynthesis turns light energy into chemical energy in chloroplasts.", id=1)
    s, text, _, _ = build("photosynthesis", [note], "en")
    assert s and s.questions[0]["answer"] == "chloroplasts" and text.startswith("Photosynthesis turns")
    assert grade(s, "Chloroplasts.", "en") == "Correct!" and s.finished
    vi = Note(title="Quang hợp", content="Quang hợp diễn ra trong lục lạp của tế bào thực vật.", id=2)
    s, _, _, _ = build("quang hợp", [vi], "vi")
    assert s.topic == "Quang hợp" and s.questions[0]["answer"] == "thực vật", s.questions
    assert grade(s, "thuc vat", "vi") == "Chính xác!"
    finish(s, date(2026, 10, 26))
    assert s.review_due == date(2026, 10, 29)
    print("ok")

# Student Learning Assistant

CSC10014 Computational Thinking, Team 02. Topic: Virtual Assistant.

The assistant turns a student's message into tasks, asks for missing details, and
proposes a study schedule that respects deadlines and available time. When the work
does not fit, it says so instead of hiding the problem. It also answers questions
about campus offices from `data/offices.csv`.

All three features from the project report work: planning and task execution,
knowledge management (the student's own notes), and study support (quizzes from those
notes). Messages can be in Vietnamese or English; the reply follows the language of the
message. Plans and notes are stored in SQLite, so they survive a server restart.

## What works

| Feature | Example message |
|---|---|
| Extract tasks, deadlines, and durations | `I have a calculus problem set due Friday and a Data Structures midterm next Wednesday` |
| Ask for missing study time | the assistant asks "how many hours can you study each day?" |
| Read study time and busy days | `About 3 hours on weekdays. I'm busy all Saturday.` |
| Build a schedule and report conflicts | earliest deadline first, exam preparation ends the day before the exam |
| Update the plan | `mark calculus problem set as done`, `show my plan`, `reset` |
| Task dependencies | `do the slides after the essay` |
| Save and organize notes and links | `save note: Derivatives - the derivative of x^2 is 2x #calculus`, `save link https://... #tag` |
| Search notes (accent-insensitive), link to tasks, delete | `find notes about derivatives`, `find #calculus`, `link note 1 to essay`, `delete note 1` |
| Study session: summary, questions, feedback | `quiz me on derivatives`, `study note 1` |
| Review suggestion added to the plan | `add review to plan` |
| Vietnamese | `Tôi có bài tập giải tích hạn thứ 6`, `Mỗi ngày tôi học được 3 tiếng, thứ 7 bận`, `kiểm tra tôi về đạo hàm` |
| Campus offices, including partial names | `Where is the library?`, `Thư viện ở đâu?` |
| Optional local AI for unusual requests and better quizzes | Ollama with `qwen3:14b`, see [docs/ai-setup.md](docs/ai-setup.md) |

Every guess (a task duration, which week "next Wednesday" means) is listed as an
assumption so the student can correct it. Searches and quizzes use only notes the
student saved; a source is the student's own link or "your note #3", never an invented one.

## Setup

Requirements: Python 3.10 or newer and Git. The assistant itself uses only the
Python standard library; `pytest` is needed to run the tests.

```bash
git clone https://github.com/vominhtriet-triseet/assistant-team02.git
cd assistant-team02
python -m venv .venv
```

Activate the virtual environment:

- Git Bash on Windows: `source .venv/Scripts/activate`
- PowerShell: `.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Install the project in editable mode and the test dependency:

```bash
python -m pip install -e .
python -m pip install -r requirements.txt
```

Check the setup:

```bash
python scripts/check_env.py
```

## Run

Web chat page:

```bash
python -m assistant serve
```

Then open http://127.0.0.1:8000. Use `--port 8080` to change the port. Data is stored in
`data/assistant.db` (ignored by Git); set `ASSISTANT_DB` to use another file.

To publish it at https://assistant.triseet.site from the GPU PC, follow
[docs/deploy.md](docs/deploy.md).

Command line, one message:

```bash
python -m assistant "where is the library?"
```

Command line, a conversation that keeps your plan between messages:

```bash
python -m assistant
```

## Test and evaluate

```bash
python -m pytest -q
python eval/run.py
```

`eval/run.py` runs the 23 benchmark cases in `eval/cases.csv` with a fixed date, so
the results are the same on every machine.

## Project layout

```text
src/assistant/
  service.py          process_request(): the single entry point for every interface
  planning/parser.py  rule-based reading of tasks, dates, durations, study time (English and Vietnamese)
  planning/scheduler.py  earliest-deadline-first schedule with daily capacity and dependencies
  knowledge.py        Feature 2: save, search, link, and delete notes
  study.py            Feature 3: quiz questions, grading, review task
  i18n.py             language detection and Vietnamese replies
  storage.py          SQLite, the 8 tables of the report's data model
  offices.py          office lookup with partial names
  llm.py              optional Ollama or OpenAI-compatible provider
  server.py           HTTP server for the chat page (standard library only)
  __main__.py         command line
ui/index.html         chat page
data/                 synthetic data used by the assistant
eval/                 benchmark cases and runner
tests/                unit, service, and server tests
docs/                 design documents
report/               project report, kept locally (ignored by Git)
```

The response format of `process_request()` is described in
[docs/ai-interface.md](docs/ai-interface.md).

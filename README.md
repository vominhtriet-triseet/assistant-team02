# Student Learning Assistant

CSC10014 Computational Thinking, Team 02. Topic: Virtual Assistant.

The assistant turns a student's message into tasks, asks for missing details, and
proposes a study schedule that respects deadlines and available time. When the work
does not fit, it says so instead of hiding the problem. It also answers questions
about campus offices from `data/offices.csv`.

This is the MVP of Feature 1 (planning and task execution) from the project report.
Knowledge management and study support are planned for later versions.

## What works

| Feature | Example message |
|---|---|
| Extract tasks, deadlines, and durations | `I have a calculus problem set due Friday and a Data Structures midterm next Wednesday` |
| Ask for missing study time | the assistant asks "how many hours can you study each day?" |
| Read study time and busy days | `About 3 hours on weekdays. I'm busy all Saturday.` |
| Build a schedule and report conflicts | earliest deadline first, exam preparation ends the day before the exam |
| Update the plan | `mark calculus problem set as done`, `show my plan`, `reset` |
| Campus offices, including partial names | `Where is the library?`, `faculty office hours` |
| Optional AI reading of unusual requests | local model (Ollama) or an API key, see [docs/ai-setup.md](docs/ai-setup.md) |

Every guess (a task duration, which week "next Wednesday" means) is listed as an
assumption so the student can correct it.

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

Then open http://127.0.0.1:8000. Use `--port 8080` to change the port.

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

`eval/run.py` runs the 15 benchmark cases in `eval/cases.csv` with a fixed date, so
the results are the same on every machine.

## Project layout

```text
src/assistant/
  service.py          process_request(): the single entry point for every interface
  planning/parser.py  rule-based reading of tasks, dates, durations, study time
  planning/scheduler.py  earliest-deadline-first schedule with daily capacity
  offices.py          office lookup with partial names
  llm.py              optional Ollama or OpenAI-compatible provider
  server.py           HTTP server for the chat page (standard library only)
  __main__.py         command line
ui/index.html         chat page
data/                 synthetic data used by the assistant
eval/                 benchmark cases and runner
tests/                unit, service, and server tests
docs/                 design documents
report/               project report (LaTeX source and figures)
```

The response format of `process_request()` is described in
[docs/ai-interface.md](docs/ai-interface.md).

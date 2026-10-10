# assistant-team02
CSC10014 Personal Productivity Assistant — Team 02

A small rule-based assistant for the CSC10014 Smart Virtual Assistant project.
It answers greetings and looks up office locations and opening hours from
`data/offices.csv`.

## Setup

Requirements: Python 3.10+ and Git.

Clone the repository and enter it:

```bash
git clone https://github.com/vominhtriet-triseet/lab01-Triseet.git
cd lab01-Triseet
```

Create and activate a virtual environment.

Git Bash on Windows:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

PowerShell on Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and its test dependency:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run

With the virtual environment active:

```bash
python -m assistant "where is the library?"
```

Expected output:

```text
Library: room B.201, open Mon-Sat 07:00-20:00.
```

For interactive mode, run `python -m assistant` and type questions. Enter
`quit` or `exit` to stop.

## Test

```bash
python -m pytest -q
```

Expected result: `4 passed`.

To check the complete developer setup:

```bash
python scripts/check_env.py
```

Every check should show `[ OK ]`.

## Project structure

- `src/assistant/`: application code and response rules.
- `tests/`: automated tests.
- `data/`: small sample data used by the assistant.
- `scripts/check_env.py`: environment verification script.
- `docs/`: project documentation.
- `ui/`: future user-interface plan.
- `requirements.txt`: pinned direct dependencies.
- `pyproject.toml`: package and test configuration.

## Troubleshooting

- `No module named assistant`: activate `.venv` and run `python -m pip install -e .`.
- `pytest` is not found: activate `.venv` and run `python -m pip install -r requirements.txt`.
- PowerShell blocks activation: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.
- The app does not know an office: check that its name exists in `data/offices.csv`.
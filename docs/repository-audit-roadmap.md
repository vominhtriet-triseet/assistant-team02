# Repository audit and improvement roadmap

## Audit summary

The repository is currently a prototype assembled from several disconnected lab components. It does not yet implement the three features described in the feature-analysis document as one coherent assistant.

The three main features should be:

1. **Planning and task execution**: combine Scheduling & Planning with Task & Project Management.
2. **Knowledge management**: manage notes, documents, sources, and reusable information.
3. **Study support**: support learning, practice, feedback, and review planning.

The current code includes greetings and office lookup, a separate help-command prototype, a static placeholder UI, and sample task data that no code consumes. Planning, knowledge management, and study support are mostly described in documentation rather than implemented.

| Area | Current state |
|---|---|
| `assistant/` | Greeting and office lookup using rules |
| `backend/` | Separate help/capability prototype, not connected to `assistant/` |
| `ui/` | Static HTML placeholder; it does not send requests to a backend |
| `data/sample_tasks.csv` | Sample tasks exist but are not used by application code |
| `eval/` | Evaluation runner is not functional |
| `tests/` | Includes placeholder tests using `assert True` |
| Planning | Documentation exists; task lifecycle and scheduler are not implemented |
| Knowledge management | Office lookup exists; notes, search, and citations are not implemented |
| Study support | Appears in branding and examples; no study workflow exists |

---

## P0: Fix the foundation and make the repository truthful

### 1. Choose one main branch

The checked-out branch is `16-backend-office-lookup-handles-partial-names`, while `origin/main` has newer material that is missing from this branch. Before further development:

1. Update local information from `origin/main`.
2. Reconcile documents that only exist on other branches.
3. Make `main` the single source of truth.
4. Require issues to include implementation, tests, documentation, and acceptance evidence before closure.

### 2. Standardize the Python package layout

[pyproject.toml](../pyproject.toml) and [README.md](../README.md) assume that the package is at `src/assistant`, but the current code is under the repository root in `assistant/`.

Use a standard `src` layout:

```text
src/
└── assistant/
    ├── __init__.py
    ├── __main__.py
    ├── application/
    ├── domain/
    ├── features/
    ├── infrastructure/
    └── interfaces/
```

Update these together:

- [pyproject.toml](../pyproject.toml)
- [README.md](../README.md)
- [scripts/check_env.py](../scripts/check_env.py)
- imports in tests
- data loading in the current assistant rules

The data path in [assistant/rules.py](../assistant/rules.py) does not match the current package location. After moving to `src`, define a reliable data-loading strategy that does not depend on the user's current working directory.

Verify from a fresh virtual environment:

```bash
python -m pip install -e .
python -m assistant "where is the library?"
python -m pytest -q
```

Also run the installed package from a directory outside the repository.

### 3. Keep one application service

The repository currently has two unrelated implementations:

- [assistant/rules.py](../assistant/rules.py)
- [backend/main.py](../backend/main.py)

Create one canonical entry point, for example:

```text
src/assistant/application/service.py
```

All interfaces should call the same service:

```text
CLI  ─────┐
UI   ─────┼──> process_request()
Eval ─────┘
```

Replace `backend/main.py` with a real adapter or remove it. Avoid keeping a backend that only searches strings in a list of capability descriptions.

Use a structured response shared by the CLI, UI, and evaluator:

```text
AssistantResponse
├── message
├── intent
├── tasks
├── schedule
├── knowledge_answer
├── study_result
├── warnings
├── assumptions
├── citations
└── errors
```

### 4. Replace placeholder tests

[tests/test_smoke.py](../tests/test_smoke.py) contains tests that always pass with `assert True`. Replace them with behavior tests.

A starting test structure:

```text
tests/
├── unit/
│   ├── test_input_validation.py
│   ├── test_office_lookup.py
│   ├── test_task_model.py
│   ├── test_scheduler.py
│   ├── test_knowledge.py
│   └── test_study.py
├── integration/
│   ├── test_process_request.py
│   ├── test_cli.py
│   └── test_api.py
├── contract/
│   └── test_response_schema.py
└── fixtures/
```

Cover at least:

- empty input;
- non-string input;
- greeting;
- exact office lookup;
- partial office lookup;
- a more specific office name;
- unknown office;
- ambiguous query;
- task creation and editing;
- missing deadline or duration;
- schedule conflicts;
- unscheduled tasks;
- knowledge retrieval and citations;
- study questions and feedback.

Move or remove [backend/test_help.py](../backend/test_help.py). It is not collected by the documented pytest command and its assertions do not match the current backend implementation.

---

## P1: Build Planning and task execution first

This should be the first vertical slice because [docs/problem-boundary.md](problem-boundary.md) and [ui/README.md](../ui/README.md) already describe it in some detail.

### Domain model

Define:

```text
Task
TaskStatus
Priority
TimeWindow
Dependency
ScheduleItem
ScheduleProposal
Conflict
```

A task should have at least:

```text
id
title
description
duration_minutes
deadline
priority
status
dependencies
created_at
updated_at
```

### Decomposition

```text
User request
→ extract goal
→ create tasks
→ assign priority
→ check constraints
→ create proposed schedule
→ track progress
```

### MVP functions

- Create, update, complete, defer, and reschedule tasks.
- List and filter tasks.
- Store deadlines, durations, and priorities.
- Check dependencies and availability.
- Detect conflicts.
- Show tasks that could not be scheduled.
- Ask for missing information instead of guessing.

Start with a deterministic, explainable scheduler. Call its output a `ScheduleProposal`, not an optimal or guaranteed schedule. Return separate fields for scheduled tasks, unscheduled tasks, warnings, and assumptions.

---

## P2: Build Knowledge management

Office lookup can be the first knowledge use case, but it should return structured results instead of a formatted string.

### Domain model

```text
KnowledgeItem
Source
Tag
KnowledgeLink
Citation
KnowledgeAnswer
```

A knowledge item may include:

```text
id
title
content
tags
subject
source
created_at
updated_at
status
```

### Decomposition

```text
Capture
→ classify
→ tag
→ store
→ search
→ connect
→ cite
```

### MVP functions

- Save and search notes.
- Search by tag or subject.
- Link related notes.
- Use the office directory as an initial knowledge catalog.
- Return source metadata.
- Handle ambiguous and multiple results.

[docs/ui-sources.md](ui-sources.md) correctly warns against fabricated citations. Responses should include verified source data, for example:

```json
{
  "answer": "The library is in room B.201.",
  "citations": [
    {
      "title": "University office directory",
      "publisher": "Synthetic project data",
      "record_id": "office-library",
      "url": null
    }
  ]
}
```

URLs such as `example.edu` and `example.org` should remain clearly illustrative and must not be presented as real sources.

### Improve office matching

The current lookup returns the first row whose name is a substring of the query. A generic name may be chosen before a more specific office. Improve the lookup by:

- normalizing with `casefold()`;
- preferring longer, more specific matches;
- supporting aliases;
- detecting ambiguous matches;
- validating the CSV schema;
- defining behavior for `None`, empty, and invalid inputs;
- adding source metadata when the data is shown to users.

---

## P3: Build Study support

Study support currently appears in the UI tagline and examples, but has no domain logic.

### Domain model

```text
StudyGoal
StudyTopic
StudySession
PracticeQuestion
StudyAttempt
StudyProgress
```

### Decomposition

```text
Learning goal
→ identify topic
→ explain concept
→ generate practice
→ check answer
→ give feedback
→ schedule review
```

### MVP functions

- Create a study goal and select topics.
- Create study sessions and store progress.
- Provide flashcards or practice questions.
- Check answers and return feedback.
- Identify topics that need review.
- Add review tasks to the scheduler.

Study support should reuse planning and knowledge:

```text
Knowledge item
→ study topic
→ practice session
→ feedback
→ review task
```

Start with deterministic behavior. Add an AI provider only after the domain model, tests, and evaluation are stable.

---

## Abstraction across features

The feature analysis uses an `AssistantContext` idea:

```python
AssistantContext(
    user_goal,
    tasks,
    schedule,
    knowledge_items,
    study_state,
    next_actions,
)
```

This is useful as a conceptual model, but it should not become a large class that owns every feature. Keep separate domain contexts:

```text
PlanningContext
KnowledgeContext
StudyContext
```

Connect them through a shared response contract. They may share the user's goal, next actions, warnings, and citations, while each feature keeps its own responsibilities.

---

## P4: Correct the data assets and their documentation

### Fix `data/README.md`

The current data documentation lists files that are not present, including `user_profiles.json`, `calendar_events.csv`, `task_backlog.csv`, `intent_training.json`, and `travel_time_matrix.json`. It omits the actual `offices.csv` and `sample_tasks.csv` files.

Rewrite the catalog to describe only existing files. If future assets are mentioned, label them as planned and not included.

### Fix `data/sample_tasks.csv`

Add:

- a data dictionary;
- allowed status values;
- priority range;
- timezone policy;
- dependency fields where needed;
- validation;
- a controlled clock for tests.

The current sample deadlines are old fixture dates. Either keep them as explicitly historical examples or generate relative dates for demonstrations. Do not require UTC `Z` in documentation while the CSV omits timezone information.

---

## P5: Repair the evaluation system

[eval/run.py](../eval/run.py) is not a usable evaluation runner, and [eval/cases.csv](../eval/cases.csv) has no stable schema.

Use a structure such as:

```text
eval/
├── cases.csv
├── run.py
├── README.md
└── results/
```

Example schema:

```csv
case_id,category,input,expected_intent,expected_behavior
E001,greeting,Hello,greeting,returns greeting
E002,knowledge,Where is the library?,knowledge,returns office location
E003,validation,,validation,returns input error
E004,planning,Review calculus tomorrow,planning,creates task
E005,clarification,Plan my assignment,clarification,asks for missing duration
E006,conflict,Schedule two tasks in one hour,planning,shows conflict
```

The runner should report pass/fail and pass rate, exit nonzero on regression, cover all three features, and run in CI.

---

## P6: Connect the UI

[ui/index.html](../ui/index.html) is a placeholder. Its form currently changes a status message without sending a request.

After the service contract is stable, implement these UI states:

```text
empty
loading
clarification
success
conflict
partial success
error
citation result
study feedback
```

Display task lists, proposed schedules, warnings, unscheduled tasks, knowledge answers and citations, study questions, and feedback. The UI should render structured responses rather than parse free-form text.

---

## Target repository structure

```text
assistant-team02/
├── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
├── CHANGELOG.md
├── src/
│   └── assistant/
│       ├── __init__.py
│       ├── __main__.py
│       ├── application/
│       │   ├── service.py
│       │   └── router.py
│       ├── domain/
│       │   ├── task.py
│       │   ├── schedule.py
│       │   ├── knowledge.py
│       │   ├── study.py
│       │   └── response.py
│       ├── features/
│       │   ├── planning/
│       │   ├── knowledge/
│       │   └── study/
│       ├── infrastructure/
│       │   ├── repositories/
│       │   └── providers/
│       └── interfaces/
│           ├── cli.py
│           └── http.py
├── data/
│   └── synthetic/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── fixtures/
├── eval/
├── docs/
├── ui/
├── scripts/
└── .github/
    └── workflows/
        └── ci.yml
```

Do not build every directory at once. Implement one vertical slice at a time:

```text
service contract
→ planning model
→ planning tests
→ CLI
→ UI
```

Then extend the same structure for knowledge and study support.

---

## Documentation to add or revise

Recommended documentation set:

```text
docs/
├── product-brief.md
├── architecture.md
├── api-contract.md
├── planning-spec.md
├── knowledge-spec.md
├── study-spec.md
├── data-catalog.md
├── evaluation-plan.md
├── privacy-and-security.md
├── roadmap.md
└── definition-of-done.md
```

### Main README

Make [README.md](../README.md) the authoritative project guide. It should include:

1. Project overview.
2. The three features.
3. Current implementation status.
4. Setup and run instructions.
5. Tests and evaluation.
6. A short architecture overview.
7. Known limitations.
8. Roadmap.

Include a capability-status table and label every feature accurately. For example:

| Capability | Status |
|---|---|
| Greeting | Implemented |
| Office lookup | Implemented, matching needs improvement |
| Task CRUD | Planned |
| Scheduling | Planned |
| Knowledge retrieval | Prototype |
| Study support | Planned |
| Web UI integration | Planned |

### Other documents

- Rewrite `backend/README.md`; it currently gives incorrect commands such as `requirements.get` and `test_backend.py`, and claims scheduling that is not implemented.
- Rewrite `docs/ai-or-not.md` as a table with the question, whether AI is needed, the reason, expected behavior, and feature category.

---

## CI and project governance

Add:

```text
.github/
├── workflows/ci.yml
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   └── feature_request.md
├── pull_request_template.md
└── CODEOWNERS
```

Minimum CI steps:

```text
install
→ run tests
→ validate data
→ run evaluator
→ run lint/format checks
```

Also add `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `definition-of-done.md` as appropriate for the course project.

An issue should only close when the behavior works, tests cover it, documentation is updated, edge cases are considered, and acceptance evidence is available.

---

## Suggested milestones

### Milestone 1: Make the repository truthful

- Synchronize the project baseline.
- Standardize the package layout.
- Fix data loading.
- Consolidate the backend.
- Replace placeholder tests.
- Correct the README and data catalog.
- Verify a clean install and a working office lookup.

### Milestone 2: Planning MVP

- Task model and repository.
- CRUD operations.
- Priority, deadline, and status.
- Scheduler and conflict detection.
- Clarification for missing information.
- Behavior tests.

### Milestone 3: Knowledge MVP

- Knowledge item model.
- Search and tags.
- Source metadata and citation contract.
- Move office lookup into the knowledge feature.

### Milestone 4: Study MVP

- Study goals, topics, and sessions.
- Practice questions and feedback.
- Progress tracking.
- Review scheduling.

### Milestone 5: UI, evaluation, and CI

- Connect the UI to the service.
- Render structured responses.
- Finish the evaluator.
- Add CI.
- Complete documentation and release notes.

---

## Final priority order

1. Fix package layout and data path.
2. Replace placeholder tests with behavior tests.
3. Consolidate `assistant/` and `backend/`.
4. Build the Planning MVP.
5. Connect the UI to the application service.
6. Build the Knowledge MVP.
7. Build the Study MVP.
8. Repair evaluation.
9. Add CI and project governance.
10. Complete documentation, license, and release notes.

The first goal is not to create many modules. It is to make one complete flow work:

```text
User request
→ canonical service
→ task, knowledge, or study response
→ CLI or UI
→ behavior test
→ evaluation result
```

Once that flow is reliable, extend it to the other features using the same architecture.

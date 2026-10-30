# Project progress presentation: questions, answers, and evidence

This document prepares the team for progress questions from the lecturer. Each answer separates what is currently present in the repository from what the team plans to implement. The linked files are evidence that can be opened during the presentation.

## Presentation rule

Use the following wording when showing evidence:

> This file documents the intended behavior, while this code file shows the current implementation. We are careful not to describe a planned feature as completed until it has code, tests, and a working demonstration.

The project repository is:

- [GitHub repository](https://github.com/vominhtriet-triseet/assistant-team02)
- [Project README](../README.md)
- [Repository audit and roadmap](repository-audit-roadmap.md)

---

## 1. What problem does the project solve?

### Suggested answer

The project is intended to help students organize work and study. The assistant receives an unstructured request and helps turn it into tasks, priorities, constraints, schedules, knowledge items, or study actions. The current product direction has three features: Planning and task execution, Knowledge management, and Study support.

### Evidence to show

- [Problem boundary](problem-boundary.md): target users, pain points, use cases, constraints, and the central transformation.
- [UI flow](../ui/README.md): natural-language input, routing, clarification, fallback, and result display.
- [Repository README](../README.md): current project description and setup instructions.

### GitHub links

- [Problem boundary on GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/docs/problem-boundary.md)
- [UI flow on GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/ui/README.md)

---

## 2. What has the team completed?

### Suggested answer

The repository currently contains a rule-based greeting and office-lookup prototype, synthetic office and task data, a static UI prototype, and initial product documentation. We have also reviewed the repository and recorded the remaining work in the audit roadmap. The three main product features are not yet complete.

### Evidence to show

- [Rule-based assistant](../assistant/rules.py): greeting and office lookup logic.
- [CLI entry point](../assistant/__main__.py): how the current assistant is launched.
- [Office data](../data/offices.csv): current lookup dataset.
- [Sample tasks](../data/sample_tasks.csv): synthetic task fixture.
- [UI prototype](../ui/index.html): current static interface.
- [Repository roadmap](repository-audit-roadmap.md): current status and remaining work.

### Important wording

Say **prototype** or **initial implementation**, not “the full assistant is complete.”

---

## 3. Are the three features already working?

### Suggested answer

Not yet. Planning does not yet have a complete task lifecycle or scheduler. Knowledge management does not yet provide a complete notes and retrieval workflow. Study support does not yet have a complete practice and progress workflow. The UI is also not connected to a backend service. The team is treating these as planned MVP work and will mark each feature complete only after implementation, tests, and a working demonstration are available.

### Evidence to show

- [Repository audit summary](repository-audit-roadmap.md): current implementation table.
- [UI placeholder](../ui/index.html): explicitly shows that backend integration is not implemented.
- [Planning requirements](problem-boundary.md): intended behavior that still needs implementation.
- [Initial UI scope](../ui/README.md): intended task and schedule interactions.

### GitHub links

- [UI placeholder on GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/ui/index.html)
- [Audit roadmap on GitHub](https://github.com/vominhtriet-triseet/assistant-team02/blob/main/docs/repository-audit-roadmap.md)

---

## 4. Which part is currently executable?

### Suggested answer

The current executable surface is the rule-based assistant for greetings and office lookup. The backend capability class is a separate prototype and is not yet the canonical application service. The team is now consolidating these surfaces so that the CLI, UI, evaluator, and future API use one service contract.

### Evidence to show

- [Current rules](../assistant/rules.py).
- [Current CLI](../assistant/__main__.py).
- [Backend prototype](../backend/main.py).
- [Backend README](../backend/README.md): shows the current documentation mismatch that must be corrected.
- [Packaging configuration](../pyproject.toml): currently assumes a `src` layout.

---

## 5. Why did the team combine Scheduling & Planning with Task & Project Management?

### Suggested answer

Both areas operate on the same core object: a task. A task has a title, duration, deadline, priority, status, and possibly dependencies. Task management creates and tracks the work, while scheduling assigns that work to available time. Combining them creates one coherent Planning and task execution feature instead of separating two parts of the same lifecycle.

### Evidence to show

- [Problem boundary](problem-boundary.md): task extraction, priorities, constraints, schedule generation, and revision.
- [Sample task data](../data/sample_tasks.csv): current fields include duration, deadline, importance, and status.
- [UI flow](../ui/README.md): task creation, schedule planning, task updates, and rescheduling.

---

## 6. How do the three features connect?

### Suggested answer

Planning turns a broad goal into tasks and schedules. Knowledge management stores notes, documents, and sources related to those tasks. Study support uses that information to create explanations, practice activities, feedback, and review actions. For example, a student can save material about a topic, create a study session from it, complete a practice activity, and schedule the next review.

### Evidence to show

- [Problem boundary](problem-boundary.md): the planning transformation and revision flow.
- [UI flow](../ui/README.md): task and schedule flow.
- [Source display design](ui-sources.md): how retrieved information should be presented with sources.
- [Sample tasks](../data/sample_tasks.csv): synthetic tasks that can support a future study-planning demo.
- [Audit roadmap, abstraction section](repository-audit-roadmap.md): shared context and response contract.

---

## 7. How does the team apply decomposition, pattern recognition, and abstraction?

### Suggested answer

Decomposition breaks each feature into smaller operations. For Planning, the sequence is request, task extraction, prioritization, constraint checking, scheduling, and progress tracking. Pattern recognition identifies repeated flows such as goal to task to scheduled time, capture to organize to search, and explanation to attempt to feedback to review. Abstraction gives the system stable entities such as Task, KnowledgeItem, StudySession, and a shared response contract, so the code does not depend on the exact wording of each request.

### Evidence to show

- [Repository audit roadmap](repository-audit-roadmap.md): decomposition, domain models, and shared response contract.
- [Problem boundary](problem-boundary.md): intended task and scheduling pipeline.
- [UI flow](../ui/README.md): input, routing, clarification, fallback, and result pattern.
- [Source rules](ui-sources.md): repeated source-display pattern.

### Note

The computational-thinking analysis was first prepared in the team's presentation document. The repository roadmap is the current written version that connects those ideas to implementation tasks.

---

## 8. How will the team implement Planning and task execution?

### Suggested answer

We will first define a Task model with an identifier, title, duration, deadline, priority, status, and dependencies. The MVP will support creating, updating, completing, postponing, and rescheduling tasks. A deterministic scheduler will produce a proposed schedule, detect conflicts, and list tasks that could not be scheduled. If duration, deadline, or availability is missing, the assistant will ask for clarification instead of silently guessing.

### Evidence to show

- [Planning requirements](problem-boundary.md): core use cases and constraints.
- [UI result requirements](../ui/README.md): proposed schedule, warnings, unscheduled tasks, and rescheduling.
- [Sample task CSV](../data/sample_tasks.csv): initial synthetic task fields.
- [Planning implementation plan](repository-audit-roadmap.md): Planning MVP section.

---

## 9. Why is the output called a “schedule proposal” instead of a guaranteed schedule?

### Suggested answer

The result depends on the information supplied by the user. If availability, duration, dependencies, or deadlines are missing or conflicting, the system cannot honestly claim that the plan is guaranteed or optimal. Therefore, it will show a proposed schedule together with assumptions, warnings, conflicts, and unscheduled tasks.

### Evidence to show

- [Problem boundary constraints](problem-boundary.md): incomplete input, infeasibility, and uncertainty.
- [UI result behavior](../ui/README.md): distinction between a proposed schedule and a guaranteed feasible plan.
- [Audit roadmap](repository-audit-roadmap.md): `ScheduleProposal`, warnings, assumptions, and unscheduled tasks.

---

## 10. How will Knowledge management work?

### Suggested answer

The team will represent information as KnowledgeItems with content, tags, subjects, and source metadata. The MVP will support saving and searching notes, retrieving related information, and returning citations when a verified source exists. Office lookup can be the first knowledge source, but it will be moved behind the same structured knowledge interface instead of remaining an isolated string-matching rule.

### Evidence to show

- [Office data](../data/offices.csv): initial knowledge-like dataset.
- [Source display design](ui-sources.md): citation placement and anti-fabrication rules.
- [Data README](../data/README.md): current data documentation that needs correction.
- [Knowledge MVP plan](repository-audit-roadmap.md): knowledge model and search flow.

### Important wording

Say “office lookup is the first knowledge-source prototype,” not “the knowledge-management feature is complete.”

---

## 11. How will the team avoid fabricated citations?

### Suggested answer

The response will contain structured citation objects only when the source is actually available. The UI will render citations from the response contract rather than extracting or inventing URLs from arbitrary text. If no verified source exists, the response will say that no source is available. The example URLs in the source-design document are illustrative only.

### Evidence to show

- [Source rules](ui-sources.md): explicitly prohibits fabricated citations.
- [Office data](../data/offices.csv): currently has limited source metadata, which is part of the planned improvement.
- [Knowledge roadmap](repository-audit-roadmap.md): structured `Source` and `Citation` models.

---

## 12. How will Study support work?

### Suggested answer

Study support will start with a study goal, topic, and study session. The assistant can explain a concept, provide a practice question, check the answer, give feedback, and suggest what to review next. The next review can be represented as a task in the Planning feature. The initial version will use synthetic content and deterministic rules before considering an AI provider.

### Evidence to show

- [UI examples](../ui/index.html): current study-related examples and the current placeholder status.
- [Sample tasks](../data/sample_tasks.csv): synthetic study-related task examples.
- [Study roadmap](repository-audit-roadmap.md): Study support model and MVP flow.
- [Problem boundary](problem-boundary.md): uncertainty and synthetic-data boundaries.

---

## 13. Is the UI connected to the backend?

### Suggested answer

Not yet. The current HTML page is a UI prototype. Its form prevents a real submission and changes a local status message instead. After the response contract and application service are ready, the team will connect the UI to the service and add loading, clarification, success, conflict, error, citation, and study-feedback states.

### Evidence to show

- [UI HTML](../ui/index.html): current placeholder behavior.
- [UI README](../ui/README.md): intended routing and result flow.
- [Application integration plan](repository-audit-roadmap.md): canonical service and UI connection.

---

## 14. How is the team testing the project?

### Suggested answer

The current test suite needs improvement. Some smoke tests are placeholders and always pass, while the backend test is not included in the normal pytest discovery and does not match the current backend response. The team will replace those tests with behavior-based unit, integration, contract, and evaluation tests. A regression should make the test suite fail.

### Evidence to show

- [Placeholder smoke tests](../tests/test_smoke.py): current false-green tests that must be replaced.
- [Backend tests](../backend/test_help.py): current stale and excluded tests.
- [Pytest configuration](../pyproject.toml): current test discovery configuration.
- [Testing roadmap](repository-audit-roadmap.md): proposed test structure and required cases.

### Strong answer if asked about “how many tests pass?”

> The current pass count is not a reliable progress metric because some tests are placeholders. We are replacing them with behavior tests first, then we will report coverage by feature and by acceptance case.

---

## 15. Does the project use AI now?

### Suggested answer

The current executable assistant is rule-based. The code itself states that AI has not been added yet. The team will first stabilize the domain models, validation, response contract, and evaluation cases with deterministic behavior. If an AI provider is added later, it will be placed behind a replaceable provider interface, while validation, warnings, citations, and privacy rules remain controlled by the application.

### Evidence to show

- [Rule-based assistant](../assistant/rules.py): current implementation.
- [AI analysis document](ai-or-not.md): current AI-related planning document, which still needs completion.
- [Architecture roadmap](repository-audit-roadmap.md): provider separation and staged implementation.

---

## 16. How does the team protect data privacy?

### Suggested answer

The MVP uses synthetic data. The team will not commit real calendars, personal task lists, credentials, or private student information. The system should avoid unnecessary logging and should make assumptions visible instead of silently collecting or inventing personal details.

### Evidence to show

- [Problem boundary](problem-boundary.md): non-goals, privacy boundary, synthetic-data rule, and constraints.
- [UI privacy and error rules](../ui/README.md): validation, credentials, logging, and synthetic data.
- [Data documentation](../data/README.md): current privacy and governance statements that need to match the actual files.

---

## 17. What are the biggest risks at the moment?

### Suggested answer

The main risks are disconnected application surfaces, an inconsistent package layout, false-green tests, an unusable evaluator, and documentation that describes more functionality than the code currently provides. The team is addressing these risks by defining one application service, separating modules by feature, adding behavior tests, and maintaining a capability-status table.

### Evidence to show

- [Repository audit](repository-audit-roadmap.md): complete risk assessment and priority order.
- [Packaging configuration](../pyproject.toml): current `src` layout mismatch.
- [UI placeholder](../ui/index.html): current lack of backend integration.
- [Evaluation runner](../eval/run.py): current evaluation gap.
- [Smoke tests](../tests/test_smoke.py): current placeholder tests.

---

## 18. What will the team do next?

### Suggested answer

The next work is divided into five milestones:

1. Make the repository truthful and installable.
2. Implement the Planning MVP.
3. Implement the Knowledge MVP.
4. Implement the Study MVP.
5. Connect the UI, evaluator, and CI.

The first measurable end-to-end flow will be:

```text
User request
→ canonical service
→ task, knowledge, or study response
→ CLI or UI
→ behavior test
→ evaluation result
```

### Evidence to show

- [Milestones in the audit roadmap](repository-audit-roadmap.md#suggested-milestones).
- [Final priority order](repository-audit-roadmap.md#final-priority-order).
- [Project README](../README.md): current setup and project entry point.

---

## 19. How is the work divided among the six members?

### Suggested answer

The proposed ownership is module-based so that members can work independently:

| Username | Proposed ownership |
|---|---|
| `vominhtriet-triseet` | Product scope, acceptance criteria, progress tracking, and integration |
| `NPTho510` | Package structure, application service, and response contract |
| `NiceBruhh` | Planning and task execution |
| `NguyenDuongAn` | Knowledge management and data catalog |
| `HaiTanh` | Study support, UI/UX, and acceptance testing |
| `reiryuka` | CI, data validation, and evaluator |

Each member works in a separate branch and owns a separate module. Shared decisions are limited to the response contract, data/timezone rules, test command, and branch workflow.

### Evidence to show

- [Team roles](team.md): current role list.
- [Repository roadmap](repository-audit-roadmap.md): target modules and milestones.
- [Team work plan](team-work-plan.md): detailed task ownership and handoff rules, if this plan has been added to the repository.

### Important correction

[docs/team.md](team.md) currently repeats `HaiTanh` for QA and UI/UX, so the repository lists five distinct usernames in its role table. `NiceBruhh` appears in the contributor history and is used here as the provisional sixth member. Confirm this username with the team before presenting the assignment as official.

---

## 20. What does “done” mean for a task?

### Suggested answer

A task is done only when its code is in the assigned module, behavior tests cover normal and edge cases, documentation is updated, the relevant command passes, and the acceptance criteria are verified in a reviewed pull request. Creating a file or writing a design paragraph alone is not considered completion.

### Evidence to show

- [Repository roadmap](repository-audit-roadmap.md): CI, governance, and final priority order.
- [Team work plan](team-work-plan.md): Definition of Done and independent work rules, if this plan has been added to the repository.

---

## Short closing statement

> The team has completed the initial prototype and requirements analysis, but the full three-feature assistant is still under development. Our immediate goal is to make the repository consistent and testable, then deliver one complete Planning MVP. After that, we will implement Knowledge management and Study support using the same application service and response contract. We will report each feature as complete only when the code, tests, UI behavior, and documentation agree.

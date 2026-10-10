# Problem Boundary: Personal Productivity Assistant

## Target users

- People who need help organizing or researching.

## Pain points

- Requests often arrive as unstructured natural language.
- Important tasks can be hard to identify and prioritize when several requests compete for limited time.
- Plans may be unrealistic when deadlines, task durations, availability, dependencies, or other constraints are overlooked.
- Users need a clear way to review assumptions and adjust a proposed plan when information is missing or circumstances change.

## Core use cases

1. **Parse a request:** Convert an unstructured request into identifiable tasks and extract relevant details such as deadlines, estimated durations, dependencies, and preferences.
2. **Set priorities:** Assign or recommend priorities based on urgency, importance, deadlines, and user-provided preferences.
3. **Identify constraints:** Represent availability, time limits, dependencies, and other stated restrictions; flag missing or conflicting information instead of silently inventing it.
4. **Build a feasible schedule:** Arrange tasks into a proposed schedule that respects known constraints and available time.
5. **Explain and revise a plan:** Show the reasoning behind prioritization or scheduling decisions, surface conflicts, and revise the proposal when the user changes requirements.
6. **Handle uncertainty:** Ask for clarification or state assumptions when a request does not provide enough information for a reliable plan.

The central transformation is **unstructured requests → tasks, priorities, constraints, and feasible schedules**. The assistant supports planning and decision-making; a proposed schedule is only as reliable as the information supplied.

## Non-goals

- Guaranteeing an optimal schedule or inferring unstated personal preferences as facts.
- Providing medical, legal, financial, or other professional advice.
- Collecting or maintaining a real personal profile for the purpose of planning.
- Connecting to real personal calendars or storing users' private task lists as part of this repository.

## Constraints

- Input may be incomplete, ambiguous, inconsistent.
- Task duration, deadline, availability, priority, and dependency information may be unknown.
- A schedule must respect explicitly stated constraints and should surface infeasibility when all requirements cannot be satisfied.
- Planning output should be understandable and easy for users to inspect, correct, and revise.
- The implementation should separate extracted facts from assumptions or recommendations where practical.
- The project must remain within the data boundary described above and must not require real personal data to develop or test core behavior.
- Results depend on the quality of the input.

## Success criteria

- Given a representative unstructured request, the system produces a structured set of tasks with relevant deadlines, durations, and dependencies when those details are present.
- Priorities are explicit and can be traced to supplied urgency, importance, deadlines, or preferences.
- Stated constraints are captured and reflected in the proposed schedule.
- The system identifies missing information, conflicting constraints, or infeasible requests instead of silently ignoring them.
- The resulting schedule is actionable, readable, and can be revised when the user changes a task or constraint.
- Tests cover typical requests, incomplete inputs, conflicting deadlines, and cases where no feasible schedule can be produced.
- Repository examples and tests use synthetic data; no real personal calendars, private tasks, credentials, or sensitive data are stored in the repository.

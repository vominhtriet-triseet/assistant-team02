# Student-Facing UI Flow

## 1. Purpose

This document describes the planned user interface flow for the Smart AI Assistant. The interface helps students convert natural-language requests into structured tasks and actionable schedules.

The chat page in `ui/index.html` implements this flow for the planning feature. Start it with `python -m assistant serve` and open http://127.0.0.1:8000. External calendar sync and voice input are still out of scope.

## 2. User Flow

The main interaction follows this sequence:

1. **Input** — The student enters a request in natural language.
2. **Routing** — The system identifies the request type and directs it to the appropriate handler.
3. **Clarification or fallback** — The system asks for missing information or provides a safe fallback when processing fails.
4. **Result** — The system presents the extracted tasks, a proposed schedule, or an actionable error message.

## 3. Input

The interface provides a text input where students can describe their tasks, deadlines, estimated durations, and available time.

Example:

> I need to review calculus tomorrow and finish my programming assignment before 5 PM.

The system should accept incomplete requests and avoid assuming that unspecified details are known.

## 4. Routing

After receiving a request, the system classifies it into a supported request type, such as:

- **Task creation:** Extract one or more tasks from the request.
- **Schedule planning:** Generate a schedule based on tasks, deadlines, and availability.
- **Task updates:** Change task details or completion status.
- **Unsupported request:** Explain that the request is outside the currently supported scope.

Routing decisions should be validated by the application rather than relying solely on unrestricted model-generated output.

## 5. Clarification and Fallback

### Clarification

If required information is missing or ambiguous, the interface asks a focused follow-up question.

Examples:

- A task has no identifiable deadline, but a deadline is required for the requested schedule.
- The duration of a task is unknown.
- The available time conflicts with the requested workload.

The system should ask only for information needed to proceed and preserve the details already provided.

### Fallback

If the AI service is unavailable, the response cannot be parsed, or the request cannot be handled safely, the interface should:

- Display a clear explanation of the issue.
- Preserve the original request where appropriate.
- Allow the student to retry or enter task details manually.
- Avoid presenting an unverified schedule as valid.

## 6. Result

Depending on the request, the interface may display:

- Extracted tasks and their attributes.
- Task priorities and scheduling explanations.
- A proposed schedule with start times, end times, and deadlines.
- Warnings for conflicts, insufficient availability, or tasks that cannot be scheduled.
- Actions to edit tasks, mark them complete, or generate an updated schedule.

The system must distinguish between a proposed schedule and a guaranteed feasible plan. It should clearly identify tasks that remain unscheduled.

## 7. Error Handling and Privacy

- Validate task fields before saving or scheduling.
- Handle invalid input and service failures without crashing the interface.
- Do not expose API keys, credentials, or internal error details to the user.
- Do not use real student task lists, calendars, emails, or contact details as sample data.
- Use synthetic data for demonstrations and tests.
- Do not log sensitive user content unnecessarily.

## 8. Initial Implementation Scope

The initial UI should support:

1. Entering a natural-language request.
2. Reviewing extracted task details.
3. Answering clarification questions.
4. Viewing a proposed schedule and any warnings.
5. Updating task status and requesting rescheduling.

Advanced integrations, such as external calendar synchronization and voice input, are outside the initial scope.


Routing and Evaluation Outline

1. Purpose

This document defines the initial routing policy, safety safeguards, and evaluation approach for the Smart AI Assistant.

The initial scope focuses on extracting structured tasks, handling multi-task planning requests, asking clarification questions, and reporting scheduling limitations honestly.

This document specifies intended behavior. It does not imply that the routing or scheduling components have already been implemented.

2. Initial Routing Policy

2.1. Clear Single-Task Requests

Route clear requests describing a single task to deterministic extraction.

Extract only information supported by the user's input, such as the task title, duration, and deadline.

Validate extracted fields before saving the task.

If a required field is missing, ask a clarification question instead of inventing a value.


2.2. Multi-Task Requests

Route requests containing multiple tasks to the priority and planning logic.

Extract and validate each task before attempting to schedule it.

Use documented priority rules to determine task order.

Check deadlines, task durations, and user-provided availability before generating a schedule.

Report tasks that cannot be scheduled instead of silently dropping them.


2.3. Incomplete or Ambiguous Requests

Ask a focused clarification question when the deadline, duration, or availability required for planning is missing.

Preserve information the user has already provided.

Do not infer deadlines, durations, or availability without a reliable basis.

If possible, retain the extracted task as a draft until the missing information is supplied.


2.4. Conflicting Constraints

Validate whether the requested tasks can fit within the available time.

Detect conflicts such as overlapping tasks, insufficient available time, or deadlines that cannot be met.

Explain the conflict clearly and identify affected tasks.

Ask the user which constraint they want to change when a resolution requires changing their original requirements.

Never claim that a schedule is feasible unless its constraints have been validated.


2.5. Unsupported or Unclear Requests

Use a safe fallback when a request is outside the supported scope or cannot be interpreted reliably.

Explain what the system can and cannot do.

Ask the user to rephrase the request or enter task details manually.

If the AI service fails or returns invalid output, handle the error without crashing or exposing internal details.


3. Deterministic Task Extraction

Clear task requests should be converted into structured task records using explicit parsing and validation rules wherever possible.

Example input:

Add a task called "Review calculus notes" that takes 60 minutes and is due on October 12, 2026, at 9:00 AM.

Expected extracted fields:

Title: Review calculus notes

Duration: 60 minutes

Deadline: 2026-10-12 09:00

Status: pending, if this is the application's documented default

The system should validate field types, date formats, and permitted values before accepting a task.

Natural-language parsing may use an AI model when needed, but the resulting fields must be validated by application logic. The system must not silently invent missing deadlines, durations, or availability.

Relative dates, such as "tomorrow," should only be resolved when the relevant current date and time zone are known. Otherwise, the system should ask for clarification.

4. Multi-Task Routing and Planning

Requests containing multiple tasks or asking for a schedule should be routed to the priority and planning component.

The initial planning pipeline is:

Extract individual tasks.

Validate task fields and identify missing information.

Check the user's explicitly provided availability.

Rank tasks using documented priority rules.

Attempt to allocate tasks to available time slots.

Validate the proposed schedule against all hard constraints.

Return the schedule, unscheduled tasks, and relevant warnings.

Priority ranking is a heuristic for deciding which tasks to consider first. It must not override hard constraints such as fixed commitments or deadlines.

The planner should preserve existing task completion status and any fixed schedule entries that the user has requested to keep unchanged.

5. Clarification Policy

The system should ask clarification questions when essential information is missing or ambiguous. It must preserve the information already provided by the user and avoid inventing constraints.


5.1. Missing Deadline

If the user requests a schedule but a task's deadline is missing, ask for the deadline when it is necessary to produce the requested plan.

Do not invent a deadline or assume that a task is due today.

If the task can be created without a deadline, save it as a draft or leave the deadline unspecified.

Explain when a missing deadline prevents the system from verifying whether the task can be completed on time.


5.2. Missing Duration

If the task duration is required for scheduling but has not been provided, ask the user for an estimate.

Do not assign an arbitrary duration without explicitly identifying it as a proposed estimate and obtaining the user's confirmation.

If the duration remains unknown, keep the task unscheduled when its feasibility cannot be verified.


5.3. Missing Availability

If the system needs the user's available time to construct a schedule, ask which time periods are available.

Do not assume that the user is free outside explicitly provided commitments.

If availability is unknown, the system may organize tasks by priority but must not claim that the resulting plan is a feasible schedule.


5.4. Ambiguous Date or Time

Ask the user to clarify dates or times when multiple interpretations are possible.

Resolve relative expressions such as "tomorrow" only when the current date and relevant time zone are known.

Do not silently convert ambiguous expressions into specific deadlines.

Preserve the original expression until it can be resolved reliably.


5.5. Clarification Principles

Ask focused questions that address the information currently needed.

Avoid asking the user to repeat details already provided.

Ask only the necessary questions before proceeding.

Preserve valid task information while waiting for clarification.

Clearly distinguish confirmed user-provided values from estimates or suggestions.

Do not generate a schedule that depends on unresolved assumptions without disclosing those assumptions.


6. Conflicting Constraints

The system must distinguish between a proposed schedule and a verified feasible schedule.

Potential conflicts include:

The total required duration exceeds the available time.

A task cannot fit before its deadline.

Two tasks require the same time slot.

A fixed commitment overlaps a proposed task.

A task's earliest permitted start time is after its deadline.

When a conflict is detected, the system should:

Identify the affected task or constraint.

Explain why the requested schedule cannot satisfy the known constraints.

Mark affected tasks as unscheduled or at risk.

Ask whether the user wants to change a deadline, duration, or availability.

Recalculate the schedule only after the relevant information or constraints change.

The system must not claim that a schedule is feasible if any hard constraint remains violated. If feasibility cannot be verified, the result must be labelled as unverified.

The system must not change user-provided deadlines or availability silently.

7. Safe Fallback

For unsupported, unclear, or unsuccessfully processed requests, the system should:

Explain what could not be understood or completed.

Ask the user to rephrase the request or provide the missing fields.

Offer structured manual task entry when available.

Preserve valid input where appropriate.

Handle AI service failures, malformed model output, and validation errors without crashing.

Avoid fabricating tasks, deadlines, or scheduling results.

The system should not expose credentials, API keys, internal stack traces, or private application data in user-facing error messages.

8. Initial Evaluation Cases

Initial evaluation should use synthetic test cases only. No private calendars, real user conversations, credentials, or personal task lists should be used.

ID

Test case

Expected behavior

E01

One task with an explicit title, duration, and deadline

Extract and validate all supplied fields

E02

Multiple tasks with different deadlines and importance levels

Extract every task and route to planning logic

E03

Task with no deadline when a deadline is required

Ask a clarification question

E04

Task with no duration when scheduling requires it

Ask for an estimated duration

E05

Scheduling request with no availability information

Ask for availability when needed

E06

Required work exceeds the available time

Report infeasibility or unscheduled tasks

E07

Two tasks overlap with a fixed commitment

Detect the conflict and avoid claiming feasibility

E08

Ambiguous relative date without a known reference date

Ask for clarification rather than inventing a date

E09

Unsupported request unrelated to task planning

Use the safe fallback

E10

AI returns malformed or incomplete structured output

Reject or repair only through validated logic; otherwise ask for input or fall back

E11

User changes a task duration after planning

Revalidate and recalculate affected schedule entries

E12

User marks a task complete

Preserve completion status during subsequent replanning

Each test case should record the input, expected behavior, actual result, pass/fail status, and any observed failure.

9. Initial Evaluation Metrics

Task extraction

Field accuracy: Correctly extracted fields divided by evaluated fields.

Task completeness: Correctly extracted tasks divided by expected tasks.

Clarification correctness: Whether the system asks when required information is missing and avoids unnecessary questions when it is present.

Routing

Routing accuracy: Correctly routed requests divided by all evaluated requests.

Fallback correctness: Unsupported or unclear requests handled according to the fallback policy.

Planning

Hard-constraint violation rate: Number of proposed schedules violating hard constraints divided by the number of schedules evaluated.

Task scheduling rate: Number of tasks successfully scheduled divided by the number of schedulable tasks.

Conflict detection rate: Proportion of deliberately introduced conflicts correctly identified.

Rescheduling correctness: Whether task completion, fixed commitments, and unchanged constraints are preserved after updates.

Reliability

Structured-output validation rate: Proportion of model outputs that pass schema and semantic validation.

Failure recovery rate: Proportion of simulated processing failures handled without crashing or presenting invalid output.

Results should be reported with the number of test cases and their outcomes. Small synthetic test sets are useful for initial validation but are not sufficient to establish general real-world performance.

10. Evaluation Principles

Use deterministic expected results for rule-based extraction and constraint validation tests.

Use synthetic inputs with explicit expected outputs.

Include normal cases, missing-field cases, ambiguous requests, and conflicting constraints.

Separate model extraction errors from planner errors.

Never reward a planner for producing a complete-looking schedule that violates hard constraints.

Document limitations and failed test cases instead of hiding them.
# AI Service Interface

Implemented in `src/assistant/service.py`. The CLI, the web server, and the evaluator
all call this function.

## Function Signature

```python
def process_request(user_input: str, session: Session | None = None,
                    today: date | None = None, provider=None) -> dict:
    ...
```

## Inputs

- `user_input`: non-empty natural-language request from the user.
- `session`: keeps tasks, study time, dependencies, notes, study sessions, and the pending
  question between messages. A new empty session is used when it is omitted. The web server
  loads it from SQLite before the call and saves it after (`assistant.storage`).
- `today`: the date relative dates are resolved against. Tests and the evaluator pass a
  fixed date.
- `provider`: optional language-model provider from `assistant.llm.get_provider()`.

## Outputs

A dictionary that always contains:

- `intent`: `greeting`, `help`, `office`, `clarification`, `planning`, `knowledge`, `study`,
  `reset`, or `fallback`.
- `lang`: `vi` or `en`, the language of the reply (it follows the student's message).
- `message`: a short explanation, answer, or clarification question.
- `tasks`: all tasks in the session, each with `id`, `title`, `kind`, `deadline`,
  `deadline_time`, `hours`, `hours_assumed`, `priority`, `status`, and `source`
  (`user`, `llm`, or `system` for a suggested review task).
- `priorities`: `{task_id, priority, reason}` for every open task.
- `schedule`: a list of days, each `{date, day, blocks}`, or `None` when the schedule
  cannot be built yet. A block is `{task_id, title, hours, event}`; `event` marks a
  deadline or exam rather than study time.
- `warnings`: work that does not fit before its deadline, or an unavailable AI service.
- `assumptions`: every guess the assistant made, such as an estimated duration.
- `facts`: what the student stated, such as deadlines and study time.
- `highlights`: `{text, kind}` spans of the student's message that were read as a
  `task`, `date`, or `time`.
- `suggestions`: short replies the interface can offer as buttons.
- `notes`: notes shown by a knowledge reply, each `{id, title, content, source_url, tags, created_at}`.
- `citations`: `{note_id, title, source_url}` for every note a reply used. `source_url` is
  `null` for the student's own note; the assistant never invents a source.
- `study`: the current study session, `{id, topic, item_ids, progress, question_count,
  current, finished, review_notes, review_due}`, or `None`.

## Errors

- `ValueError`: input is empty or not a string.
- Other exceptions are not expected. The web server turns them into a generic error
  message without internal details.

## Fallback

Rules run first. A language model is only asked when the rules find nothing in a
planning-like message and a provider is configured (see [ai-setup.md](ai-setup.md)).
Its output is validated field by field. If the model is unavailable or the request
cannot be interpreted, the response has `intent: fallback`, `schedule: None`, a
warning when the model failed, and a message that tells the student what the assistant
can do.

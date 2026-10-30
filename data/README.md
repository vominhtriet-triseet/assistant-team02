# Data

All data in this folder is synthetic or taken from public campus information. Do not
add real student calendars, task lists, emails, or contact details.

| File | Used by | Contents |
|---|---|---|
| `offices.csv` | `src/assistant/offices.py` | Office name, room, and opening hours. Columns: `name,room,hours`. Use `Not listed publicly` when the room or hours are not published. |
| `sample_tasks.csv` | Reference data for demos and future import | Example tasks with `task_id,title,duration_minutes,deadline,importance,status`. Deadlines use ISO 8601 local time. |

Tasks and study time that students type into the assistant are kept in memory for the
current session only and are not written to this folder.

To read data from another folder, set `ASSISTANT_DATA_DIR` to that path.

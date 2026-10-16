# Data Directory - Personal Schedule Assistant

This directory contains all the data assets (raw datasets, configurations, and training templates) used to train, configure, and operate the Personal Schedule Assistant.

## Data Inventory

The table below outlines the source, ownership, and update frequency for each data file utilized in this repository:

| File Name | Source | Owner | Update Frequency | Description |
| :--- | :--- | :--- | :--- | :--- |
| `user_profiles.json` | User registration & application settings | **Product Team / Backend** | Upon user profile modification | Stores user preferences, time zones, standard working hours, and buffer time configurations. |
| `calendar_events.csv` | Google Calendar & Outlook Calendar APIs | **Integration Team** | Real-time synchronization | Holds active events, meetings, and blocked slots to prevent scheduling conflicts. |
| `task_backlog.csv` | User input & to-do list applications | **Product Lead** | Dynamic / Weekly | A list of tasks, deadlines, and priority levels that need to be scheduled into the calendar. |
| `intent_training.json` | Synthesized dataset & historical chat logs | **AI / NLP Team** | Monthly (Upon model retraining) | Training data for natural language understanding (NLU) to identify scheduling intents (e.g., set, reschedule, cancel). |
| `travel_time_matrix.json`| Google Maps Distance Matrix API | **Data Engineer** | Weekly | Cached travel time data between frequent user locations to calculate commute buffers. |
| `system_prompts.md` | Internal AI behavioral engineering | **Product Lead** | As required by system updates | Defines the persona, tone of voice, and boundary constraints for the assistant (e.g., no meetings after 8 PM). |

---

## Data Governance & Standards

* **Privacy & Security:** Files containing Personally Identifiable Information (PII), such as `user_profiles.json` and `calendar_events.csv`, must be anonymized. Never commit production or real user data to public branches.
* **Time Standardization:** All timestamps across these files must strictly follow the **ISO 8601** format (`YYYY-MM-DDTHH:mm:ssZ`) to ensure accurate scheduling logic and timezone conversions.


# Quality evaluation — version `e18a55b`

Run 2026-11-21 09:12:15 on one Windows 11 laptop, Python 3.15.0. Server under test in its own process, temporary SQLite file, rules path unless stated.

## 1. Test levels (pytest)

| Level / component | Tests | Passed | Failed |
|---|---|---|---|
| Parser (planning/parser.py) | 12 | 12 | 0 |
| Scheduler (planning/scheduler.py) | 11 | 11 | 0 |
| Service / router (service.py) | 18 | 18 | 0 |
| Knowledge (knowledge.py) | 6 | 6 | 0 |
| Study (study.py) | 7 | 7 | 0 |
| Storage (storage.py) | 6 | 6 | 0 |
| Office lookup (offices.py) | 8 | 8 | 0 |
| Language / i18n (i18n.py + Vietnamese rules) | 9 | 9 | 0 |
| HTTP server (server.py) | 7 | 7 | 0 |
| Security regressions (BUG-04..07) | 5 | 5 | 0 |
| INTEGRATION (IT-01..07) | 7 | 7 | 0 |
| SYSTEM (ST-01..07) | 7 | 7 | 0 |
| **Total** | **103** | **103** | **0** |

**INTEGRATION (IT-01..07)**

| Test | Result | Time s |
|---|---|---|
| test_IT01_api_passes_the_message_to_the_service | Pass | 0.61 |
| test_IT02_service_result_is_saved_in_storage | Pass | 0.61 |
| test_IT03_storage_carries_the_conversation_between_requests | Pass | 0.62 |
| test_IT04_task_update_reaches_scheduler_and_stored_blocks | Pass | 0.63 |
| test_IT05_a_failing_request_does_not_change_stored_data | Pass | 0.59 |
| test_IT06_model_failure_falls_back_to_rules_without_losing_data | Pass | 0.00 |
| test_IT07_note_quiz_and_review_task_are_linked_in_storage | Pass | 0.01 |

**SYSTEM (ST-01..07)**

| Test | Result | Time s |
|---|---|---|
| test_ST01_new_task_appears_in_the_plan | Pass | 0.60 |
| test_ST02_earlier_deadline_reschedules_the_task | Pass | 0.59 |
| test_ST03_finished_task_is_no_longer_scheduled | Pass | 0.64 |
| test_ST04_missing_information_gets_a_question_not_a_plan | Pass | 0.66 |
| test_ST05_infeasible_plan_is_warned_not_forced | Pass | 0.57 |
| test_ST06_data_survives_a_server_restart | Pass | 1.14 |
| test_ST07_vietnamese_conversation_end_to_end | Pass | 0.62 |

## 2. Simulation: 5 concurrent users (CCU)

Five simulated students start at the same moment and keep chatting for 60 s. Each picks scenarios from the 33-case test set at random, waits 0.3–1.5 s between messages (think time), and after each conversation the stored record is compared with the reply. Baseline: 1 user for 30 s.

| Metric | 1 user | 5 users |
|---|---|---|
| Requests | 31 | 298 |
| Conversations completed | 24 | 231 |
| Throughput (req/s) | 0.98 | 4.74 |
| Failed requests | 0 | 0 |
| Success rate | 100.00% | 100.00% |
| Stored record ≠ reply (integrity) | 0 | 0 |
| Wrong task count (isolation) | 0 | 0 |
| Server memory after run (MB) | 30.8203125 | 31.08984375 |

| Run | Requests | Mean ms | Min | P50 | P90 | P95 | P99 | Max |
|---|---|---|---|---|---|---|---|---|
| 1 user | 31 | 71.6 | 17.4 | 75.2 | 104.0 | 112.6 | 139.1 | 139.1 |
| 5 users | 298 | 70.5 | 16.0 | 75.7 | 102.5 | 114.3 | 179.7 | 238.2 |

| User | Requests | P50 ms | P95 ms |
|---|---|---|---|
| U1 | 61 | 74.2 | 105.6 |
| U2 | 58 | 74.7 | 112.0 |
| U3 | 55 | 79.0 | 117.2 |
| U4 | 58 | 78.0 | 120.4 |
| U5 | 66 | 72.0 | 107.8 |

**Model path with 5 CCU** (assistant.triseet.site, Qwen3 14B on one RTX 5070, one model call at a time):

| Arrival order | HTTP | Seconds | Task source |
|---|---|---|---|
| 1 | 200 | 3.25 | llm |
| 2 | 200 | 6.17 | llm |
| 3 | 200 | 9.12 | llm |
| 4 | 200 | 11.97 | llm |
| 5 | 200 | 14.84 | llm |

## 3. Stress test

**Concurrency ramp** (closed loop, no think time, each client sends 10 requests: every third adds a task, the rest replan; server and clients on one laptop):

| Concurrent clients | Requests | Errors | Throughput req/s | P50 ms | P95 ms | P99 ms | Max ms |
|---|---|---|---|---|---|---|---|
| 1 | 20 | 0 | 29.9 | 22.0 | 82.5 | 106.1 | 106.1 |
| 5 | 50 | 0 | 75.0 | 53.3 | 113.3 | 124.0 | 124.0 |
| 10 | 100 | 0 | 101.7 | 77.6 | 163.6 | 180.5 | 197.1 |
| 25 | 250 | 0 | 127.2 | 174.2 | 451.5 | 536.0 | 562.4 |
| 50 | 500 | 0 | 175.4 | 219.0 | 751.7 | 941.1 | 1029.2 |
| 100 | 1000 | 0 | 178.1 | 426.1 | 1489.5 | 1828.0 | 1970.1 |
| 200 | 2000 | 0 | 175.4 | 876.7 | 2871.6 | 3541.5 | 3785.5 |

Breaking point (first level with > 1% errors or P95 > 5 s): none up to 200 clients.
Recovery after the 200-client peak: P50 26.9 ms vs 22.0 ms before, 0 errors.

**Task volume** (one student with many tasks, 6 h/day, deadlines over 4 weeks; replan 3×):

| Tasks | Stored | Median replan ms | Max ms | Hard violations | Warnings |
|---|---|---|---|---|---|
| 100 | 100 | 111 | 156 | 0 | 0 |
| 200 | 200 | 142 | 151 | 0 | 32 |
| 500 | 500 | 207 | 253 | 0 | 332 |
| 1000 | 1000 | 356 | 366 | 0 | 832 |

Integrity after all stress runs: 396 contexts stored, 0 duplicated task rows.
Server memory: 29.46875 MB at start, 36.796875 MB after the ramp, 36.30859375 MB after volume.
Restart time (process start → first answered request): 1.13 s (HTTP 200).

## 4. Profiling

126 requests (all 33 scenarios × 3) through the same steps as the HTTP handler, in one process.

| Stage | Mean ms / request | Share of handler time |
|---|---|---|
| DB save session | 10.56 | 45.0% |
| DB load session | 5.00 | 21.3% |
| Parse + plan (process_request) | 3.99 | 17.0% |
| DB connect + schema check | 3.64 | 15.5% |
| JSON encode reply | 0.29 | 1.3% |

CPU time 2.44 s over 2.97 s wall time (82% of one core busy). Peak Python memory during the run: 0.2 MB. One student with 1000 tasks: replan 201 ms, peak 1.9 MB.

**Hottest functions (cumulative time):**

```
   List reduced from 231 to 68 due to restriction <'assistant|sqlite3|re\\.py'>
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      126    0.018    0.000    0.947    0.008 \src\assistant\storage.py:173(save)
     1071    0.832    0.001    0.832    0.001 {method 'execute' of 'sqlite3.Connection' objects}
      252    0.578    0.002    0.578    0.002 {method 'close' of 'sqlite3.Connection' objects}
      126    0.025    0.000    0.498    0.004 \src\assistant\service.py:384(process_request)
      252    0.002    0.000    0.456    0.002 \src\assistant\storage.py:115(connect)
      252    0.422    0.002    0.444    0.002 {built-in method _sqlite3.connect}
      126    0.432    0.003    0.432    0.003 {method '__exit__' of 'sqlite3.Connection' objects}
      126    0.007    0.000    0.424    0.003 \src\assistant\storage.py:132(load)
      114    0.011    0.000    0.232    0.002 \src\assistant\planning\parser.py:310(parse)
      123    0.012    0.000    0.160    0.001 \src\assistant\service.py:190(_plan_response)
      348    0.001    0.000    0.117    0.000 \src\assistant\planning\parser.py:333(<genexpr>)
      141    0.014    0.000    0.116    0.001 \src\assistant\planning\parser.py:218(_parse_task)
      111    0.046    0.000    0.085    0.001 \src\assistant\planning\scheduler.py:39(build_schedule)
      141    0.010    0.000    0.060    0.000 \src\assistant\planning\parser.py:174(_clean_title)
```

## 5. Security / penetration test

Run against a local copy of the server (and three safe checks on the team's own public site). No authentication exists by design: a random session id is the only key to a student's data.

| ID | Test | Expected | Actual | Result |
|---|---|---|---|---|
| PT-01 | SQL injection in message and note text | stored as plain text, all 8 tables intact | HTTP 200/200, tables 8/8, note title "x'); DELETE FROM knowledge_items;--" | Pass |
| PT-02 | Injection or traversal in session_id | ignored: a fresh random session, HTTP 200 | 200, 200, 200, 200, 200 | Pass |
| PT-03 | Guessing session ids (authorization) | no guessed id sees another student's tasks | 0/20 guesses saw tasks | Pass |
| PT-04 | Session fixation: client picks an unused id | server issues its own id | server used a new id | Pass |
| PT-05 | Malformed Content-Length header | HTTP 400 | HTTP/1.0 400 Bad Request | Pass |
| PT-06 | Slow or incomplete body | connection closed within 20 s | closed after 15.0 s | Pass |
| PT-07 | Oversized body (2 MB declared) | HTTP 400 without reading it | HTTP/1.0 400 Bad Request | Pass |
| PT-08 | Malformed JSON and wrong field types | HTTP 400 for each, never 500 | 400, 400, 400, 400, 400 | Pass |
| PT-09 | Path traversal / reading files over GET | 404 for every path | 404, 404, 404, 404, 404 | Pass |
| PT-10 | Stored XSS through a note | returned as data; page never uses innerHTML | innerHTML uses in ui/index.html: 0 | Pass |
| PT-11 | Version disclosure in the Server header | no Python/library version | assistant  | Pass |
| PT-12 | Browser security headers on the page | all present: x-content-type-options, x-frame-options, content-security-policy, referrer-policy | all present | Pass |
| PT-13 | Regex denial of service (15 KB crafted input) | every reply in < 2 s | slowest 0.15 s | Pass |
| PT-14 | Unknown endpoint and errors | short JSON error, no stack trace | HTTP/1.0 404 Not Found | Pass |
| PT-15 | Rate limit on assistant.triseet.site | requests beyond 8 in 10 s are blocked | 200, 200, 200, 200, 200, 200, 200, 200, 200, 429 | Pass |
| PT-16 | Ollama port 11434 from the internet | not reachable | not reachable | Pass |
| PT-17 | Plain HTTP on the public site | 301 redirect to https | 301 → https://assistant.triseet.site/ | Pass |

17/17 passed.

## 6. Bug report (confirmed, reproduced on the old and the new version)

| ID | Bug | Severity | Found by | Old version → actual | Fixed version → actual |
|---|---|---|---|---|---|
| BUG-01 | Busy days after the first one in a list are ignored | High | Evaluation scenario C04 | `9ad5025` → blocked days [0] | `e18a55b` → blocked days [0, 1, 2] |
| BUG-02 | Casual Vietnamese sentence read as one task; model never asked | Medium | Manual check of the public site | `4c77594` → 1 task(s): ['Tuần này mình phải lo vụ lab hóa với cái slide nhóm môn kinh tế'] | `e18a55b` → 2 task(s): ['Lab hóa', 'Slide nhóm môn kinh tế'] |
| BUG-03 | Every request fails when the server runs without a console (pythonw) | Critical | Deployment on the RTX PC (auto-start task) | `4c77594` → no response (connection closed) | `e18a55b` → HTTP 200 |
| BUG-04 | Malformed Content-Length closes the connection without an answer | Medium | Penetration test PT-05 | `c2a1ef5` → no response (connection closed) | `e18a55b` → HTTP/1.0 400 |
| BUG-05 | Incomplete request body holds a server thread forever (slowloris) | High | Penetration test PT-06 | `c2a1ef5` → still open after 25 s | `e18a55b` → closed after 15 s |
| BUG-06 | Server adopts a session id chosen by the client (session fixation) | Medium | Penetration test PT-04 | `c2a1ef5` → client id accepted | `e18a55b` → new id issued |
| BUG-07 | No browser security headers; Server header shows the Python version | Low | Penetration test PT-11, PT-12 | `c2a1ef5` → no security headers; Server: BaseHTTP Python/3.15.0 | `e18a55b` → nosniff/CSP present |
| BUG-08 | HTTP 500 "database is locked" under 200 concurrent clients | Medium | Stress test (concurrency ramp) | `3af6f1d` → 27 of 2000 requests failed [500] | `e18a55b` → 0 of 2000 requests failed |

**BUG-01 Busy days after the first one in a list are ignored** (High)

- Steps: Send: "Essay due Wednesday, 2 hours. 2 hours on weekdays. Busy on Monday, Tuesday and Wednesday."
- Expected: Mon, Tue and Wed blocked; warning that the essay does not fit
- Root cause: Busy days were read one comma-separated piece at a time; "Tuesday" alone had no "busy" word.
- Fix: 918eafb: a busy/hours rule carries over a following list of day names
- Regression test: `tests/test_parser.py::test_busy_and_study_time_carry_over_a_list_of_days`

**BUG-02 Casual Vietnamese sentence read as one task; model never asked** (Medium)

- Steps: Send: "Tuần này mình phải lo vụ lab hóa với cái slide nhóm môn kinh tế, cuối tuần nộp"
- Expected: Two tasks (Lab hóa, Slide nhóm môn kinh tế) due this Sunday
- Root cause: "với" did not split tasks, "cuối tuần" was not a deadline, and any rule match skipped the model.
- Fix: 9ad5025: Vietnamese splitting and deadline words; long titles go to the model
- Regression test: `tests/test_vietnamese.py::test_casual_vietnamese_shares_the_closing_deadline`

**BUG-03 Every request fails when the server runs without a console (pythonw)** (Critical)

- Steps: Start the server with pythonw.exe (sys.stdout/sys.stderr are None) and send any message
- Expected: HTTP 200
- Root cause: http.server writes each request log line to sys.stderr, which is None under pythonw, so every handler crashed.
- Fix: e1c7996: send output to data/server.log when there is no console
- Regression test: `eval/quality_eval.py bugs (BUG-03 probe)`

**BUG-04 Malformed Content-Length closes the connection without an answer** (Medium)

- Steps: POST /api/chat with header "Content-Length: abc"
- Expected: HTTP 400
- Root cause: int() on the header raised ValueError outside any error handling.
- Fix: server.py: invalid Content-Length is treated as a bad request
- Regression test: `tests/test_security.py::test_malformed_content_length_gets_400`

**BUG-05 Incomplete request body holds a server thread forever (slowloris)** (High)

- Steps: Declare Content-Length: 100, send 1 byte, keep the connection open
- Expected: Server gives up and closes the connection
- Root cause: No socket timeout on the request handler, so the read blocks with no limit; many such connections exhaust threads.
- Fix: server.py: 15 s socket timeout on every connection
- Regression test: `tests/test_security.py::test_slow_body_is_dropped`

**BUG-06 Server adopts a session id chosen by the client (session fixation)** (Medium)

- Steps: POST a message with a made-up 32-hex session_id that does not exist
- Expected: Server ignores it and issues its own random id
- Root cause: Any well-formed id was used to create a new session.
- Fix: server.py: only ids that already exist are accepted
- Regression test: `tests/test_security.py::test_unknown_session_id_is_replaced`

**BUG-07 No browser security headers; Server header shows the Python version** (Low)

- Steps: GET / and read the response headers
- Expected: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy; no version
- Root cause: BaseHTTPRequestHandler defaults; no headers were added.
- Fix: server.py: security headers on every response, neutral Server header
- Regression test: `tests/test_security.py::test_security_headers`

**BUG-08 HTTP 500 "database is locked" under 200 concurrent clients** (Medium)

- Steps: 200 clients send 10 requests each at the same moment
- Expected: Every request answered; slower is acceptable, failing is not
- Root cause: Each SQLite writer waited up to 10 s for the write lock, then raised OperationalError, reported as HTTP 500.
- Fix: server.py: writes queue on one in-process lock; if SQLite is still busy the reply is 503 with Retry-After
- Regression test: `tests/test_security.py::test_concurrent_writes_do_not_fail`


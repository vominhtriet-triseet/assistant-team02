# Quality evaluation — version `3af6f1d`

Run 2026-11-21 09:03:56 on one Windows 11 laptop, Python 3.15.0. Server under test in its own process, temporary SQLite file, rules path unless stated.

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
| Security regressions (BUG-04..07) | 4 | 4 | 0 |
| INTEGRATION (IT-01..07) | 7 | 7 | 0 |
| SYSTEM (ST-01..07) | 7 | 7 | 0 |
| **Total** | **102** | **102** | **0** |

**INTEGRATION (IT-01..07)**

| Test | Result | Time s |
|---|---|---|
| test_IT01_api_passes_the_message_to_the_service | Pass | 0.61 |
| test_IT02_service_result_is_saved_in_storage | Pass | 0.57 |
| test_IT03_storage_carries_the_conversation_between_requests | Pass | 0.56 |
| test_IT04_task_update_reaches_scheduler_and_stored_blocks | Pass | 0.64 |
| test_IT05_a_failing_request_does_not_change_stored_data | Pass | 0.61 |
| test_IT06_model_failure_falls_back_to_rules_without_losing_data | Pass | 0.00 |
| test_IT07_note_quiz_and_review_task_are_linked_in_storage | Pass | 0.01 |

**SYSTEM (ST-01..07)**

| Test | Result | Time s |
|---|---|---|
| test_ST01_new_task_appears_in_the_plan | Pass | 0.56 |
| test_ST02_earlier_deadline_reschedules_the_task | Pass | 0.61 |
| test_ST03_finished_task_is_no_longer_scheduled | Pass | 0.64 |
| test_ST04_missing_information_gets_a_question_not_a_plan | Pass | 0.57 |
| test_ST05_infeasible_plan_is_warned_not_forced | Pass | 0.58 |
| test_ST06_data_survives_a_server_restart | Pass | 1.11 |
| test_ST07_vietnamese_conversation_end_to_end | Pass | 0.56 |

## 2. Simulation: 5 concurrent users (CCU)

Five simulated students start at the same moment and keep chatting for 60 s. Each picks scenarios from the 33-case test set at random, waits 0.3–1.5 s between messages (think time), and after each conversation the stored record is compared with the reply. Baseline: 1 user for 30 s.

| Metric | 1 user | 5 users |
|---|---|---|
| Requests | 31 | 301 |
| Conversations completed | 24 | 234 |
| Throughput (req/s) | 0.97 | 4.82 |
| Failed requests | 0 | 0 |
| Success rate | 100.00% | 100.00% |
| Stored record ≠ reply (integrity) | 0 | 0 |
| Wrong task count (isolation) | 0 | 0 |
| Server memory after run (MB) | 30.9296875 | 30.86328125 |

| Run | Requests | Mean ms | Min | P50 | P90 | P95 | P99 | Max |
|---|---|---|---|---|---|---|---|---|
| 1 user | 31 | 76.1 | 19.2 | 75.3 | 92.8 | 103.5 | 169.0 | 169.0 |
| 5 users | 301 | 63.7 | 13.0 | 67.1 | 88.9 | 98.8 | 191.4 | 259.0 |

| User | Requests | P50 ms | P95 ms |
|---|---|---|---|
| U1 | 61 | 67.7 | 102.3 |
| U2 | 58 | 64.7 | 105.6 |
| U3 | 56 | 63.1 | 95.3 |
| U4 | 60 | 62.7 | 84.5 |
| U5 | 66 | 72.0 | 99.3 |

**Model path with 5 CCU** (assistant.triseet.site, Qwen3 14B on one RTX 5070, one model call at a time):

| Arrival order | HTTP | Seconds | Task source |
|---|---|---|---|
| 1 | 200 | 3.36 | llm |
| 2 | 200 | 6.22 | llm |
| 3 | 200 | 9.14 | llm |
| 4 | 200 | 12.05 | llm |
| 5 | 200 | 14.9 | llm |

## 3. Stress test

**Concurrency ramp** (closed loop, no think time, each client sends 10 requests: every third adds a task, the rest replan; server and clients on one laptop):

| Concurrent clients | Requests | Errors | Throughput req/s | P50 ms | P95 ms | P99 ms | Max ms |
|---|---|---|---|---|---|---|---|
| 1 | 20 | 0 | 21.5 | 30.0 | 109.0 | 139.0 | 139.0 |
| 5 | 50 | 0 | 76.3 | 49.6 | 128.7 | 160.3 | 160.3 |
| 10 | 100 | 0 | 95.6 | 69.5 | 167.1 | 247.7 | 484.9 |
| 25 | 250 | 0 | 97.5 | 78.6 | 443.2 | 2041.6 | 2264.8 |
| 50 | 500 | 0 | 106.4 | 96.4 | 1703.1 | 3638.8 | 4078.8 |
| 100 | 1000 | 0 | 104.7 | 108.2 | 3809.1 | 7576.6 | 9194.5 |
| 200 | 2000 | 14 [500] | 114.5 | 110.9 | 6925.1 | 11067.0 | 11432.8 |

Breaking point (first level with > 1% errors or P95 > 5 s): 200 clients.
Recovery after the 200-client peak: P50 23.2 ms vs 30.0 ms before, 0 errors.

**Task volume** (one student with many tasks, 6 h/day, deadlines over 4 weeks; replan 3×):

| Tasks | Stored | Median replan ms | Max ms | Hard violations | Warnings |
|---|---|---|---|---|---|
| 100 | 100 | 93 | 95 | 0 | 0 |
| 200 | 200 | 122 | 143 | 0 | 32 |
| 500 | 500 | 192 | 239 | 0 | 332 |
| 1000 | 1000 | 412 | 485 | 0 | 832 |

Integrity after all stress runs: 396 contexts stored, 0 duplicated task rows.
Server memory: 29.3984375 MB at start, 36.203125 MB after the ramp, 35.53515625 MB after volume.
Restart time (process start → first answered request): 1.06 s (HTTP 200).

## 4. Profiling

126 requests (all 33 scenarios × 3) through the same steps as the HTTP handler, in one process.

| Stage | Mean ms / request | Share of handler time |
|---|---|---|
| DB save session | 10.62 | 44.4% |
| DB load session | 5.04 | 21.1% |
| Parse + plan (process_request) | 4.08 | 17.0% |
| DB connect + schema check | 3.84 | 16.1% |
| JSON encode reply | 0.34 | 1.4% |

CPU time 2.39 s over 3.03 s wall time (79% of one core busy). Peak Python memory during the run: 0.2 MB. One student with 1000 tasks: replan 243 ms, peak 1.9 MB.

**Hottest functions (cumulative time):**

```
   List reduced from 231 to 68 due to restriction <'assistant|sqlite3|re\\.py'>
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      126    0.020    0.000    0.941    0.007 \src\assistant\storage.py:172(save)
     1071    0.844    0.001    0.844    0.001 {method 'execute' of 'sqlite3.Connection' objects}
      252    0.591    0.002    0.591    0.002 {method 'close' of 'sqlite3.Connection' objects}
      126    0.026    0.000    0.508    0.004 \src\assistant\service.py:384(process_request)
      252    0.003    0.000    0.482    0.002 \src\assistant\storage.py:114(connect)
      252    0.443    0.002    0.468    0.002 {built-in method _sqlite3.connect}
      126    0.007    0.000    0.428    0.003 \src\assistant\storage.py:131(load)
      126    0.418    0.003    0.418    0.003 {method '__exit__' of 'sqlite3.Connection' objects}
      114    0.013    0.000    0.237    0.002 \src\assistant\planning\parser.py:310(parse)
      123    0.012    0.000    0.163    0.001 \src\assistant\service.py:190(_plan_response)
      348    0.001    0.000    0.117    0.000 \src\assistant\planning\parser.py:333(<genexpr>)
      141    0.016    0.000    0.116    0.001 \src\assistant\planning\parser.py:218(_parse_task)
      111    0.045    0.000    0.086    0.001 \src\assistant\planning\scheduler.py:39(build_schedule)
      141    0.010    0.000    0.056    0.000 \src\assistant\planning\parser.py:174(_clean_title)
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
| PT-13 | Regex denial of service (15 KB crafted input) | every reply in < 2 s | slowest 0.16 s | Pass |
| PT-14 | Unknown endpoint and errors | short JSON error, no stack trace | HTTP/1.0 404 Not Found | Pass |
| PT-15 | Rate limit on assistant.triseet.site | requests beyond 8 in 10 s are blocked | 200, 200, 200, 200, 200, 200, 200, 200, 200, 429 | Pass |
| PT-16 | Ollama port 11434 from the internet | not reachable | not reachable | Pass |
| PT-17 | Plain HTTP on the public site | 301 redirect to https | 301 → https://assistant.triseet.site/ | Pass |

17/17 passed.

## 6. Bug report (confirmed, reproduced on the old and the new version)

| ID | Bug | Severity | Found by | Old version → actual | Fixed version → actual |
|---|---|---|---|---|---|
| BUG-01 | Busy days after the first one in a list are ignored | High | Evaluation scenario C04 | `9ad5025` → blocked days [0] | `3af6f1d` → blocked days [0, 1, 2] |
| BUG-02 | Casual Vietnamese sentence read as one task; model never asked | Medium | Manual check of the public site | `4c77594` → 1 task(s): ['Tuần này mình phải lo vụ lab hóa với cái slide nhóm môn kinh tế'] | `3af6f1d` → 2 task(s): ['Lab hóa', 'Slide nhóm môn kinh tế'] |
| BUG-03 | Every request fails when the server runs without a console (pythonw) | Critical | Deployment on the RTX PC (auto-start task) | `4c77594` → no response (connection closed) | `3af6f1d` → HTTP 200 |
| BUG-04 | Malformed Content-Length closes the connection without an answer | Medium | Penetration test PT-05 | `c2a1ef5` → no response (connection closed) | `3af6f1d` → HTTP/1.0 400 |
| BUG-05 | Incomplete request body holds a server thread forever (slowloris) | High | Penetration test PT-06 | `c2a1ef5` → still open after 25 s | `3af6f1d` → closed after 15 s |
| BUG-06 | Server adopts a session id chosen by the client (session fixation) | Medium | Penetration test PT-04 | `c2a1ef5` → client id accepted | `3af6f1d` → new id issued |
| BUG-07 | No browser security headers; Server header shows the Python version | Low | Penetration test PT-11, PT-12 | `c2a1ef5` → no security headers; Server: BaseHTTP Python/3.15.0 | `3af6f1d` → nosniff/CSP present |

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


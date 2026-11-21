# Quality evaluation — version `c2a1ef5`

Run 2026-11-21 08:57:02 on one Windows 11 laptop, Python 3.15.0. Server under test in its own process, temporary SQLite file, rules path unless stated.

## 5. Security / penetration test

Run against a local copy of the server (and three safe checks on the team's own public site). No authentication exists by design: a random session id is the only key to a student's data.

| ID | Test | Expected | Actual | Result |
|---|---|---|---|---|
| PT-01 | SQL injection in message and note text | stored as plain text, all 8 tables intact | HTTP 200/200, tables 8/8, note title "x'); DELETE FROM knowledge_items;--" | Pass |
| PT-02 | Injection or traversal in session_id | ignored: a fresh random session, HTTP 200 | 200, 200, 200, 200, 200 | Pass |
| PT-03 | Guessing session ids (authorization) | no guessed id sees another student's tasks | 0/20 guesses saw tasks | Pass |
| PT-04 | Session fixation: client picks an unused id | server issues its own id | server used the client id | **Fail** |
| PT-05 | Malformed Content-Length header | HTTP 400 | no response | **Fail** |
| PT-06 | Slow or incomplete body | connection closed within 20 s | still open after 25.0 s | **Fail** |
| PT-07 | Oversized body (2 MB declared) | HTTP 400 without reading it | HTTP/1.0 400 Bad Request
Serv | Pass |
| PT-08 | Malformed JSON and wrong field types | HTTP 400 for each, never 500 | 400, 400, 400, 400, 400 | Pass |
| PT-09 | Path traversal / reading files over GET | 404 for every path | 404, 404, 404, 404, 404 | Pass |
| PT-10 | Stored XSS through a note | returned as data; page never uses innerHTML | innerHTML uses in ui/index.html: 0 | Pass |
| PT-11 | Version disclosure in the Server header | no Python/library version | BaseHTTP Python/3.15.0 | **Fail** |
| PT-12 | Browser security headers on the page | all present: x-content-type-options, x-frame-options, content-security-policy, referrer-policy | missing: x-content-type-options, x-frame-options, content-security-policy, referrer-policy | **Fail** |
| PT-13 | Regex denial of service (15 KB crafted input) | every reply in < 2 s | slowest 0.17 s | Pass |
| PT-14 | Unknown endpoint and errors | short JSON error, no stack trace | HTTP/1.0 404 Not Found
Server: BaseHTTP | Pass |

9/14 passed.


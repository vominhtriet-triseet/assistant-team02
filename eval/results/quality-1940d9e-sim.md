# Quality evaluation — version `1940d9e`

Run 2026-11-21 09:00:02 on one Windows 11 laptop, Python 3.15.0. Server under test in its own process, temporary SQLite file, rules path unless stated.

## 2. Simulation: 5 concurrent users (CCU)

Five simulated students start at the same moment and keep chatting for 60 s. Each picks scenarios from the 33-case test set at random, waits 0.3–1.5 s between messages (think time), and after each conversation the stored record is compared with the reply. Baseline: 1 user for 30 s.

| Metric | 1 user | 5 users |
|---|---|---|
| Requests | 30 | 292 |
| Conversations completed | 23 | 227 |
| Throughput (req/s) | 0.98 | 4.74 |
| Failed requests | 0 | 0 |
| Success rate | 100.00% | 100.00% |
| Stored record ≠ reply (integrity) | 0 | 0 |
| Wrong task count (isolation) | 0 | 0 |
| Server memory after run (MB) | 31.16015625 | 30.7265625 |

| Run | Requests | Mean ms | Min | P50 | P90 | P95 | P99 | Max |
|---|---|---|---|---|---|---|---|---|
| 1 user | 30 | 84.1 | 32.2 | 84.8 | 106.7 | 116.7 | 163.3 | 163.3 |
| 5 users | 292 | 83.4 | 19.4 | 84.5 | 120.6 | 138.2 | 200.3 | 220.8 |

| User | Requests | P50 ms | P95 ms |
|---|---|---|---|
| U1 | 59 | 82.1 | 145.4 |
| U2 | 55 | 80.7 | 151.2 |
| U3 | 55 | 88.5 | 196.4 |
| U4 | 58 | 92.7 | 150.5 |
| U5 | 65 | 83.3 | 124.2 |

**Model path with 5 CCU** (assistant.triseet.site, Qwen3 14B on one RTX 5070, one model call at a time):

| Arrival order | HTTP | Seconds | Task source |
|---|---|---|---|
| 1 | 200 | 3.93 | llm |
| 2 | 200 | 6.81 | llm |
| 3 | 200 | 9.68 | llm |
| 4 | 200 | 12.58 | llm |
| 5 | 200 | 15.45 | llm |


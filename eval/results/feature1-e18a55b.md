# Feature 1 evaluation results — version `e18a55b`

Run 2026-11-21T09:18:42 on Windows 11, Python 3.15.0. Scenario dates are resolved against 2026-10-26 (Monday). Rules-only mode (no language model) unless stated.

## Summary

| Criterion | Metric | Target | Evidence | Status |
|---|---|---|---|---|
| Correctness | Schedule validity rate (30 core scenarios) | >= 90% | 30/30 = 100.0% | Met |
| Correctness | All scenarios incl. FR checks | (info) | 32/33 = 97.0% | info |
| Efficiency | Median / P90 response time, rules path (HTTP + SQLite) | <= 5 s / <= 10 s | 16.7 ms / 30.0 ms | Met |
| Reliability | Successful-run rate (99 conversations) | >= 98%, 0 lost/duplicated | 99/99 = 100.0% | Met |
| Usability | Unaided task completion (5 users) | >= 80% | not run yet | Not measurable yet |
| Scalability | 50-task median vs 10-task baseline; success | <= 2x; >= 95% | 1.11x; 5/5 = 100.0% | Met |
| Constraint handling | Undisclosed hard-constraint violations | 0 | 0 | Met |
| Constraint handling | Infeasible cases disclosed | >= 90% | 9/9 = 100.0% | Met |
| Constraint handling | Missing-information cases clarified (FR-03) | 100% | 3/3 = 100.0% | Met |

## Functional requirements

| FR | Scenarios passed | Failed scenarios |
|---|---|---|
| FR-01 | 12/12 = 100.0% | - |
| FR-02 | 1/2 = 50.0% | F03 |
| FR-03 | 6/6 = 100.0% | - |
| FR-04 | 10/10 = 100.0% | - |
| FR-05 | 11/11 = 100.0% | - |
| FR-06 | 4/4 = 100.0% | - |

## Scalability

| Tasks | Median | P90 | Successful runs | Violations |
|---|---|---|---|---|
| 10 | 18.1 ms | 32.4 ms | 5/5 | 0 |
| 30 | 20.2 ms | 38.8 ms | 5/5 | 0 |
| 50 | 20.1 ms | 77.1 ms | 5/5 | 0 |

## Scenario results

| ID | Category | FR | Result | Problems / undisclosed violations |
|---|---|---|---|---|
| N01 | normal | FR-01, FR-04 | Pass | - |
| N02 | normal | FR-01, FR-04 | Pass | - |
| N03 | normal | FR-01 | Pass | - |
| N04 | normal | FR-01, FR-04 | Pass | - |
| N05 | normal | FR-01 | Pass | - |
| N06 | normal | FR-01 | Pass | - |
| N07 | normal | FR-01 | Pass | - |
| N08 | normal | FR-01 | Pass | - |
| B01 | busy calendar | FR-01, FR-04 | Pass | - |
| B02 | busy calendar | FR-01, FR-04 | Pass | - |
| B03 | busy calendar | FR-01, FR-04 | Pass | - |
| B04 | busy calendar | FR-05 | Pass | - |
| B05 | busy calendar | FR-04 | Pass | - |
| D01 | deadline pressure | FR-05 | Pass | - |
| D02 | deadline pressure | FR-05 | Pass | - |
| D03 | deadline pressure | FR-01, FR-04 | Pass | - |
| D04 | deadline pressure | FR-05 | Pass | - |
| D05 | deadline pressure | FR-04 | Pass | - |
| A01 | ambiguous input | FR-03 | Pass | - |
| A02 | ambiguous input | FR-03 | Pass | - |
| A03 | ambiguous input | FR-03 | Pass | - |
| A04 | ambiguous input | FR-03 | Pass | - |
| C01 | conflict | FR-03, FR-05 | Pass | - |
| C02 | conflict | FR-03, FR-05 | Pass | - |
| C03 | conflict | FR-05 | Pass | - |
| C04 | conflict | FR-05 | Pass | - |
| R01 | rescheduling | FR-06 | Pass | - |
| R02 | rescheduling | FR-05, FR-06 | Pass | - |
| R03 | rescheduling | FR-05, FR-06 | Pass | - |
| R04 | rescheduling | FR-05, FR-06 | Pass | - |
| F01 | FR check | FR-04 | Pass | - |
| F02 | FR check | FR-02 | Pass | - |
| F03 | FR check | FR-02 | Fail | expected at least 2 tasks from the goal, got 1: ['Prepare for Data Structures final'] |

Failed HTTP runs: none.

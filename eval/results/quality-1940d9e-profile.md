# Quality evaluation — version `1940d9e`

Run 2026-11-21 09:02:18 on one Windows 11 laptop, Python 3.15.0. Server under test in its own process, temporary SQLite file, rules path unless stated.

## 4. Profiling

126 requests (all 33 scenarios × 3) through the same steps as the HTTP handler, in one process.

| Stage | Mean ms / request | Share of handler time |
|---|---|---|
| DB connect + schema check | 11.23 | 40.0% |
| DB save session | 8.61 | 30.6% |
| Parse + plan (process_request) | 5.69 | 20.2% |
| DB load session | 2.22 | 7.9% |
| JSON encode reply | 0.35 | 1.3% |

CPU time 2.97 s over 3.56 s wall time (83% of one core busy). Peak Python memory during the run: 0.3 MB. One student with 1000 tasks: replan 269 ms, peak 1.9 MB.

**Hottest functions (cumulative time):**

```
   List reduced from 232 to 69 due to restriction <'assistant|sqlite3|re\\.py'>
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      252    0.005    0.000    1.412    0.006 \src\assistant\storage.py:111(connect)
     1323    0.931    0.001    0.931    0.001 {method 'execute' of 'sqlite3.Connection' objects}
      126    0.029    0.000    0.710    0.006 \src\assistant\service.py:384(process_request)
      126    0.023    0.000    0.657    0.005 \src\assistant\storage.py:166(save)
      252    0.645    0.003    0.645    0.003 {method 'close' of 'sqlite3.Connection' objects}
      252    0.486    0.002    0.513    0.002 {built-in method _sqlite3.connect}
      126    0.483    0.004    0.483    0.004 {method '__exit__' of 'sqlite3.Connection' objects}
      114    0.013    0.000    0.287    0.003 \src\assistant\planning\parser.py:310(parse)
      123    0.013    0.000    0.193    0.002 \src\assistant\service.py:190(_plan_response)
       84    0.005    0.000    0.148    0.002 \src\assistant\offices.py:59(answer)
      348    0.001    0.000    0.139    0.000 \src\assistant\planning\parser.py:333(<genexpr>)
      141    0.017    0.000    0.139    0.001 \src\assistant\planning\parser.py:218(_parse_task)
       84    0.006    0.000    0.107    0.001 \src\assistant\offices.py:30(load_offices)
      111    0.055    0.000    0.105    0.001 \src\assistant\planning\scheduler.py:39(build_schedule)
```


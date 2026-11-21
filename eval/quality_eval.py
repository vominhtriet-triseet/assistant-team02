"""Software-quality evaluation beyond correctness: test levels, 5-CCU simulation, stress,
profiling, security checks, and bug reproduction across versions.

    python eval/quality_eval.py unit          # unit/component table from pytest
    python eval/quality_eval.py sim [--public] # 5 concurrent users for 60 s (+ 5-user burst on the model path)
    python eval/quality_eval.py stress        # task volume, concurrency ramp, breaking point, recovery
    python eval/quality_eval.py profile       # time per stage, CPU, memory, hottest functions
    python eval/quality_eval.py security [--public]
    python eval/quality_eval.py bugs          # reproduce each confirmed bug on the old and the new version
    python eval/quality_eval.py all [--public]

The server under test runs as a separate process with a temporary SQLite file and no
language model (rules path), so numbers are repeatable. Results: eval/results/quality-<commit>.{md,json}.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import math
import os
import pstats
import random
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import tracemalloc
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))
from assistant import storage  # noqa: E402
from assistant.service import Session, process_request  # noqa: E402
from feature1_eval import oracle  # noqa: E402

SCENARIOS = json.loads((ROOT / "eval" / "feature1_scenarios.json").read_text(encoding="utf-8"))["scenarios"]
PUBLIC = "https://assistant.triseet.site"
UA = {"User-Agent": "quality-eval"}
LLM_MESSAGE = "hôm nay phải hoàn thành bài tập mà thầy giao từ buổi trước liên quan tới đồ thị và cây nhị phân"


# ---------------------------------------------------------------- helpers

def pctl(values: list[float], p: float) -> float:
    """Nearest-rank percentile."""
    s = sorted(values)
    return s[max(0, math.ceil(p / 100 * len(s)) - 1)]


def latency(values: list[float]) -> dict:
    ms = [v * 1000 for v in values]
    return {"n": len(ms), "mean": statistics.fmean(ms), "min": min(ms), "p50": pctl(ms, 50), "p90": pctl(ms, 90),
            "p95": pctl(ms, 95), "p99": pctl(ms, 99), "max": max(ms)}


def lat_row(name: str, s: dict) -> str:
    return (f"| {name} | {s['n']} | {s['mean']:.1f} | {s['min']:.1f} | {s['p50']:.1f} | {s['p90']:.1f} | "
            f"{s['p95']:.1f} | {s['p99']:.1f} | {s['max']:.1f} |")


LAT_HEAD = ["| Run | Requests | Mean ms | Min | P50 | P90 | P95 | P99 | Max |", "|---|---|---|---|---|---|---|---|---|"]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    """Run `assistant serve` from a source tree in its own process with a temporary database."""

    def __init__(self, root: Path = ROOT, stdio_none: bool = False, db: str | None = None):
        self.port = free_port()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = db or str(Path(self.tmp.name) / "q.db")
        code = (f"import sys; sys.path.insert(0, {str(root / 'src')!r}); "
                + ("sys.stdout = None; sys.stderr = None; " if stdio_none else "")
                + f"from assistant.server import main; main(['--port', '{self.port}'])")
        env = {**os.environ, "ASSISTANT_DB": self.db, "ASSISTANT_LLM": "none", "PYTHONIOENCODING": "utf-8"}
        self.proc = subprocess.Popen([sys.executable, "-c", code], env=env, cwd=root,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.base = f"http://127.0.0.1:{self.port}"
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("server did not start")

    def rss_mb(self) -> float | None:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {self.proc.pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
        try:
            return int(out.strip().split('","')[-1].strip('" K\n').replace(",", "").replace(".", "")) / 1024
        except (ValueError, IndexError):
            return None

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.tmp.cleanup()


def post(base: str, payload: dict, path: str = "/api/chat", timeout: float = 60) -> tuple[int, dict, float]:
    req = urllib.request.Request(base + path, json.dumps(payload).encode(), {"Content-Type": "application/json", **UA})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), time.perf_counter() - start
    except urllib.error.HTTPError as err:
        body = err.read()
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"raw": body[:200].decode("utf-8", "replace")}
        return err.code, data, time.perf_counter() - start
    except (urllib.error.URLError, OSError) as err:
        return 0, {"error": str(err)}, time.perf_counter() - start


def stored_tasks(db: str, sid: str) -> list[dict]:
    with closing(storage.connect(db)) as conn:
        s = storage.load(conn, sid)
    return [t.to_dict() for t in s.tasks] if s else []


def version() -> str:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "src"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return commit + ("-dirty" if dirty else "")


# ---------------------------------------------------------------- 1. unit / component

COMPONENTS = {
    "test_parser.py": "Parser (planning/parser.py)", "test_scheduler.py": "Scheduler (planning/scheduler.py)",
    "test_service.py": "Service / router (service.py)", "test_knowledge.py": "Knowledge (knowledge.py)",
    "test_study.py": "Study (study.py)", "test_storage.py": "Storage (storage.py)", "test_offices.py": "Office lookup (offices.py)",
    "test_vietnamese.py": "Language / i18n (i18n.py + Vietnamese rules)", "test_server.py": "HTTP server (server.py)",
    "test_security.py": "Security regressions (BUG-04..07)",
    "test_integration.py": "INTEGRATION (IT-01..07)", "test_system.py": "SYSTEM (ST-01..07)",
}


def unit_section() -> tuple[list[str], dict]:
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "junit.xml"
        subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={xml}"], cwd=ROOT, capture_output=True)
        suite = ET.parse(xml).getroot()
    by_file: dict[str, dict] = defaultdict(lambda: {"pass": 0, "fail": 0, "tests": []})
    for case in suite.iter("testcase"):
        name = case.get("classname", "").split(".")[-1] + ".py"
        ok = not any(c.tag in ("failure", "error") for c in case)
        by_file[name]["pass" if ok else "fail"] += 1
        by_file[name]["tests"].append((case.get("name"), ok, float(case.get("time", 0))))
    md = ["## 1. Test levels (pytest)", "", "| Level / component | Tests | Passed | Failed |", "|---|---|---|---|"]
    total_p = total_f = 0
    for file, label in COMPONENTS.items():
        d = by_file.get(file, {"pass": 0, "fail": 0})
        total_p, total_f = total_p + d["pass"], total_f + d["fail"]
        md.append(f"| {label} | {d['pass'] + d['fail']} | {d['pass']} | {d['fail']} |")
    md.append(f"| **Total** | **{total_p + total_f}** | **{total_p}** | **{total_f}** |")
    for level in ("test_integration.py", "test_system.py"):
        md += ["", f"**{COMPONENTS[level]}**", "", "| Test | Result | Time s |", "|---|---|---|"]
        md += [f"| {n} | {'Pass' if ok else 'Fail'} | {t:.2f} |" for n, ok, t in by_file[level]["tests"]]
    return md, {"by_file": by_file, "passed": total_p, "failed": total_f}


# ---------------------------------------------------------------- 2. simulation: 5 concurrent users

def user_loop(base: str, db: str, uid: int, stop_at: float, barrier: threading.Barrier, out: dict):
    rng = random.Random(uid)
    barrier.wait()
    while time.time() < stop_at:
        sc = rng.choice(SCENARIOS)
        sid, body, ok = None, {}, True
        for message in sc["turns"]:
            status, body, seconds = post(base, {"message": message, "session_id": sid})
            out["lat"].append(seconds)
            out["per_user"][uid].append(seconds)
            if status != 200:
                out["errors"].append(f"user {uid} {sc['id']}: HTTP {status}")
                ok = False
                break
            sid = body["session_id"]
            time.sleep(rng.uniform(0.3, 1.5))  # think time between messages
        if not ok:
            continue
        out["conversations"] += 1
        if stored_tasks(db, sid) != body["tasks"]:
            out["integrity"].append(f"user {uid} {sc['id']}: stored tasks differ from the reply")
        if "tasks" in sc and len(body["tasks"]) != sc["tasks"]:
            out["isolation"].append(f"user {uid} {sc['id']}: {len(body['tasks'])} tasks, expected {sc['tasks']}")


def simulate(users: int, seconds: int) -> dict:
    srv = Server()
    out = {"lat": [], "per_user": defaultdict(list), "errors": [], "integrity": [], "isolation": [], "conversations": 0}
    barrier = threading.Barrier(users)
    stop_at = time.time() + seconds + 0.5
    threads = [threading.Thread(target=user_loop, args=(srv.base, srv.db, u, stop_at, barrier, out)) for u in range(users)]
    start = time.time()
    [t.start() for t in threads]
    [t.join() for t in threads]
    out["wall"] = time.time() - start
    out["rss_mb"] = srv.rss_mb()
    srv.stop()
    return out


def public_burst(users: int = 5) -> list[dict]:
    """5 users send a model-path message at the same moment (5 requests: under the 8-per-10-s rate limit)."""
    results, barrier = [None] * users, threading.Barrier(users)

    def one(i):
        barrier.wait()
        status, body, seconds = post(PUBLIC, {"message": LLM_MESSAGE}, timeout=120)
        results[i] = {"status": status, "seconds": round(seconds, 2), "source": [t.get("source") for t in body.get("tasks", [])]}
        if body.get("session_id"):
            post(PUBLIC, {"session_id": body["session_id"]}, path="/api/reset")

    threads = [threading.Thread(target=one, args=(i,)) for i in range(users)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return sorted(results, key=lambda r: r["seconds"])


def sim_section(public: bool) -> tuple[list[str], dict]:
    one = simulate(1, 30)
    five = simulate(5, 60)
    s1, s5 = latency(one["lat"]), latency(five["lat"])
    total = len(five["lat"])
    md = ["## 2. Simulation: 5 concurrent users (CCU)", "",
          "Five simulated students start at the same moment and keep chatting for 60 s. Each picks scenarios from the "
          "33-case test set at random, waits 0.3–1.5 s between messages (think time), and after each conversation the "
          "stored record is compared with the reply. Baseline: 1 user for 30 s.", "",
          "| Metric | 1 user | 5 users |", "|---|---|---|",
          f"| Requests | {len(one['lat'])} | {total} |",
          f"| Conversations completed | {one['conversations']} | {five['conversations']} |",
          f"| Throughput (req/s) | {len(one['lat']) / one['wall']:.2f} | {total / five['wall']:.2f} |",
          f"| Failed requests | {len(one['errors'])} | {len(five['errors'])} |",
          f"| Success rate | {100 * (1 - len(one['errors']) / max(1, len(one['lat']))):.2f}% | {100 * (1 - len(five['errors']) / max(1, total)):.2f}% |",
          f"| Stored record ≠ reply (integrity) | {len(one['integrity'])} | {len(five['integrity'])} |",
          f"| Wrong task count (isolation) | {len(one['isolation'])} | {len(five['isolation'])} |",
          f"| Server memory after run (MB) | {one['rss_mb'] or 'n/a'} | {five['rss_mb'] or 'n/a'} |",
          "", *LAT_HEAD, lat_row("1 user", s1), lat_row("5 users", s5)]
    md += ["", "| User | Requests | P50 ms | P95 ms |", "|---|---|---|---|"]
    md += [f"| U{u + 1} | {len(v)} | {pctl(v, 50) * 1000:.1f} | {pctl(v, 95) * 1000:.1f} |" for u, v in sorted(five["per_user"].items())]
    if five["isolation"] or five["integrity"] or five["errors"]:
        md += ["", "Problems: " + "; ".join(five["errors"] + five["integrity"] + five["isolation"])[:1500]]
    data = {"one": {k: v for k, v in one.items() if k != "per_user"}, "five": {k: v for k, v in five.items() if k != "per_user"},
            "lat1": s1, "lat5": s5}
    if public:
        burst = public_burst()
        md += ["", "**Model path with 5 CCU** (assistant.triseet.site, Qwen3 14B on one RTX 5070, one model call at a time):", "",
               "| Arrival order | HTTP | Seconds | Task source |", "|---|---|---|---|"]
        md += [f"| {i + 1} | {r['status']} | {r['seconds']} | {', '.join(s or '-' for s in r['source'])} |" for i, r in enumerate(burst)]
        data["burst"] = burst
    return md, data


# ---------------------------------------------------------------- 3. stress

def ramp_level(base: str, clients: int, per_client: int) -> dict:
    lat, errors, barrier = [], [], threading.Barrier(clients)
    lock = threading.Lock()

    def client(i):
        barrier.wait()
        sid = None
        for k in range(per_client):
            msg = f"report {i}-{k} due in {1 + k % 6} days for 1 hour. 3 hours a day." if k % 3 == 0 else "show my plan"
            status, body, seconds = post(base, {"message": msg, "session_id": sid}, timeout=60)
            with lock:
                lat.append(seconds)
                if status != 200:
                    errors.append(status)
            sid = body.get("session_id", sid)

    start = time.time()
    threads = [threading.Thread(target=client, args=(i,)) for i in range(clients)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    wall = time.time() - start
    return {"clients": clients, "requests": len(lat), "errors": len(errors), "codes": sorted(set(errors)),
            "rps": len(lat) / wall, **latency(lat)}


def volume_level(base: str, db: str, n: int) -> dict:
    today = date.today()
    sid, lat = None, []
    for start in range(0, n, 40):  # 40 tasks per message keeps the body under the 16 KB limit
        chunk = "; ".join(f"report {k + 1} due {(today + timedelta(days=1 + (27 * k) // n)).isoformat()} for 1 hour"
                          for k in range(start, min(n, start + 40)))
        status, body, _ = post(base, {"message": chunk + ". 6 hours a day.", "session_id": sid}, timeout=300)
        if status != 200:
            return {"tasks": n, "error": f"HTTP {status} while adding tasks"}
        sid = body["session_id"]
    bad = 0
    for _ in range(3):
        status, body, seconds = post(base, {"message": "show my plan", "session_id": sid}, timeout=300)
        lat.append(seconds)
        bad += len(oracle(body.get("schedule") or [], body.get("tasks", []), body.get("warnings", []), [6] * 7, set(), today))
    stored = len(stored_tasks(db, sid))
    return {"tasks": n, "stored": stored, "median_ms": statistics.median(lat) * 1000, "max_ms": max(lat) * 1000,
            "violations": bad, "warnings": len(body.get("warnings", []))}


def stress_section() -> tuple[list[str], dict]:
    srv = Server()
    rss = {"start": srv.rss_mb()}
    baseline = ramp_level(srv.base, 1, 20)
    ramp = [ramp_level(srv.base, c, 10) for c in (5, 10, 25, 50, 100, 200)]
    rss["after_ramp"] = srv.rss_mb()
    recovery = ramp_level(srv.base, 1, 20)
    volume = [volume_level(srv.base, srv.db, n) for n in (100, 200, 500, 1000)]
    rss["after_volume"] = srv.rss_mb()
    with closing(storage.connect(srv.db)) as conn:  # integrity after everything
        dup = conn.execute("SELECT COUNT(*) FROM (SELECT context_id, task_id FROM tasks GROUP BY 1, 2 HAVING COUNT(*) > 1)").fetchone()[0]
        contexts = conn.execute("SELECT COUNT(*) FROM contexts").fetchone()[0]
    srv.stop()
    # restart time: how long until a fresh process answers (RTO evidence for a crash)
    t0 = time.time()
    srv2 = Server()
    status, _, _ = post(srv2.base, {"message": "hello"})
    restart_s = time.time() - t0
    srv2.stop()

    breaking = next((r for r in ramp if r["errors"] / r["requests"] > 0.01 or r["p95"] > 5000), None)
    md = ["## 3. Stress test", "", "**Concurrency ramp** (closed loop, no think time, each client sends 10 requests: "
          "every third adds a task, the rest replan; server and clients on one laptop):", "",
          "| Concurrent clients | Requests | Errors | Throughput req/s | P50 ms | P95 ms | P99 ms | Max ms |", "|---|---|---|---|---|---|---|---|"]
    for r in [baseline] + ramp:
        md.append(f"| {r['clients']} | {r['requests']} | {r['errors']}{' ' + str(r['codes']) if r['codes'] else ''} | "
                  f"{r['rps']:.1f} | {r['p50']:.1f} | {r['p95']:.1f} | {r['p99']:.1f} | {r['max']:.1f} |")
    md += ["", f"Breaking point (first level with > 1% errors or P95 > 5 s): "
           f"{'none up to 200 clients' if breaking is None else str(breaking['clients']) + ' clients'}.",
           f"Recovery after the 200-client peak: P50 {recovery['p50']:.1f} ms vs {baseline['p50']:.1f} ms before, "
           f"{recovery['errors']} errors.",
           "", "**Task volume** (one student with many tasks, 6 h/day, deadlines over 4 weeks; replan 3×):", "",
           "| Tasks | Stored | Median replan ms | Max ms | Hard violations | Warnings |", "|---|---|---|---|---|---|"]
    for v in volume:
        md.append(f"| {v['tasks']} | {v.get('stored', '-')} | {v.get('median_ms', 0):.0f} | {v.get('max_ms', 0):.0f} | "
                  f"{v.get('violations', v.get('error', '-'))} | {v.get('warnings', '-')} |")
    md += ["", f"Integrity after all stress runs: {contexts} contexts stored, {dup} duplicated task rows.",
           f"Server memory: {rss['start']} MB at start, {rss['after_ramp']} MB after the ramp, {rss['after_volume']} MB after volume.",
           f"Restart time (process start → first answered request): {restart_s:.2f} s (HTTP {status})."]
    return md, {"baseline": baseline, "ramp": ramp, "recovery": recovery, "volume": volume, "rss": rss,
                "restart_s": restart_s, "dup": dup, "contexts": contexts}


# ---------------------------------------------------------------- 4. profiling

def profile_section() -> tuple[list[str], dict]:
    tmp = tempfile.TemporaryDirectory()
    db = str(Path(tmp.name) / "p.db")
    storage.connect(db).close()
    stages: dict[str, list[float]] = defaultdict(list)
    prof = cProfile.Profile()
    tracemalloc.start()
    wall0, cpu0 = time.perf_counter(), time.process_time()
    prof.enable()
    for _ in range(3):
        for sc in SCENARIOS:
            sid = uuid.uuid4().hex
            for message in sc["turns"]:
                t0 = time.perf_counter()
                conn = storage.connect(db)
                t1 = time.perf_counter()
                session = storage.load(conn, sid) or Session()
                conn.close()
                t2 = time.perf_counter()
                response = process_request(message, session)
                t3 = time.perf_counter()
                conn = storage.connect(db)
                t4 = time.perf_counter()
                storage.save(conn, sid, session)
                conn.close()
                t5 = time.perf_counter()
                json.dumps(response, ensure_ascii=False).encode()
                t6 = time.perf_counter()
                stages["DB connect + schema check"].append((t1 - t0) + (t4 - t3))
                stages["DB load session"].append(t2 - t1)
                stages["Parse + plan (process_request)"].append(t3 - t2)
                stages["DB save session"].append(t5 - t4)
                stages["JSON encode reply"].append(t6 - t5)
    prof.disable()
    wall, cpu = time.perf_counter() - wall0, time.process_time() - cpu0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    big = Session()  # memory and time for one student with 1000 tasks
    today = date.today()
    for start in range(0, 1000, 40):
        process_request("; ".join(f"report {k + 1} due {(today + timedelta(days=1 + (27 * k) // 1000)).isoformat()} for 1 hour"
                                  for k in range(start, start + 40)) + ". 6 hours a day.", big)
    tracemalloc.start()
    t0 = time.perf_counter()
    process_request("show my plan", big)
    big_ms = (time.perf_counter() - t0) * 1000
    _, big_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    tmp.cleanup()

    n = len(stages["DB load session"])
    total = sum(sum(v) for v in stages.values())
    md = ["## 4. Profiling", "", f"{n} requests (all 33 scenarios × 3) through the same steps as the HTTP handler, in one process.", "",
          "| Stage | Mean ms / request | Share of handler time |", "|---|---|---|"]
    for name, values in sorted(stages.items(), key=lambda kv: -sum(kv[1])):
        md.append(f"| {name} | {statistics.fmean(values) * 1000:.2f} | {100 * sum(values) / total:.1f}% |")
    md += ["", f"CPU time {cpu:.2f} s over {wall:.2f} s wall time ({100 * cpu / wall:.0f}% of one core busy). "
           f"Peak Python memory during the run: {peak / 1024 / 1024:.1f} MB. "
           f"One student with 1000 tasks: replan {big_ms:.0f} ms, peak {big_peak / 1024 / 1024:.1f} MB.", "",
           "**Hottest functions (cumulative time):**", "", "```"]
    buf = io.StringIO()
    pstats.Stats(prof, stream=buf).sort_stats("cumulative").print_stats(r"assistant|sqlite3|re\.py", 14)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip() and ("assistant" in ln or "sqlite3" in ln or "ncalls" in ln or "re.py" in ln)]
    md += [ln.replace(str(ROOT), "") for ln in lines[:16]] + ["```"]
    return md, {"stages_ms": {k: statistics.fmean(v) * 1000 for k, v in stages.items()}, "cpu_s": cpu, "wall_s": wall,
                "peak_mb": peak / 1048576, "big_ms": big_ms, "big_peak_mb": big_peak / 1048576, "requests": n}


# ---------------------------------------------------------------- 5. security

def raw_http(port: int, data: bytes, wait: float = 5) -> tuple[bytes, float]:
    """Send raw bytes and return what comes back before the server closes (or `wait` passes)."""
    s = socket.create_connection(("127.0.0.1", port), timeout=wait)
    start = time.time()
    s.sendall(data)
    chunks = []
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    except (TimeoutError, socket.timeout):
        chunks.append(b"<<still open>>")
    except ConnectionResetError:
        chunks.append(b"<<reset>>")
    s.close()
    return b"".join(chunks), time.time() - start


def security_section(public: bool) -> tuple[list[str], dict]:
    srv = Server()
    rows = []

    def check(tid, name, expected, ok, actual):
        rows.append({"id": tid, "test": name, "expected": expected, "pass": bool(ok), "actual": actual.splitlines()[0] if actual else ""})

    # PT-01 SQL injection through the message and a note
    payload = "Robert'); DROP TABLE tasks;-- essay due Friday"
    st, body, _ = post(srv.base, {"message": payload})
    st2, _, _ = post(srv.base, {"message": "save note: x'); DELETE FROM knowledge_items;-- - y", "session_id": body.get("session_id")})
    with closing(storage.connect(srv.db)) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        notes = conn.execute("SELECT title FROM knowledge_items").fetchall()
    check("PT-01", "SQL injection in message and note text", "stored as plain text, all 8 tables intact",
          st == 200 and st2 == 200 and set(storage.TABLES) <= tables and notes, f"HTTP {st}/{st2}, tables {len(tables & set(storage.TABLES))}/8, note title {notes[0][0] if notes else '-'!r}")
    # PT-02 SQL injection / traversal through session_id
    weird = ["1' OR '1'='1", "../../etc/passwd", "a" * 5000, 123, None]
    got = [post(srv.base, {"message": "hello", "session_id": w}) for w in weird]
    check("PT-02", "Injection or traversal in session_id", "ignored: a fresh random session, HTTP 200",
          all(s == 200 and len(b.get("session_id", "")) == 32 and b["session_id"] != w for (s, b, _), w in zip(got, weird)),
          ", ".join(str(s) for s, _, _ in got))
    # PT-03 another valid-looking id cannot read someone else's data
    _, owner, _ = post(srv.base, {"message": "secret essay due Friday"})
    guesses = [post(srv.base, {"message": "show my plan", "session_id": uuid.uuid4().hex})[1] for _ in range(20)]
    check("PT-03", "Guessing session ids (authorization)", "no guessed id sees another student's tasks",
          all(not g.get("tasks") for g in guesses), f"{sum(bool(g.get('tasks')) for g in guesses)}/20 guesses saw tasks")
    # PT-04 session fixation: client-chosen unused id
    chosen = "ab" * 16
    _, fx, _ = post(srv.base, {"message": "hello", "session_id": chosen})
    check("PT-04", "Session fixation: client picks an unused id", "server issues its own id",
          fx.get("session_id") != chosen, f"server used {'the client id' if fx.get('session_id') == chosen else 'a new id'}")
    # PT-05 malformed Content-Length
    resp, _ = raw_http(srv.port, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: abc\r\n\r\n{}")
    check("PT-05", "Malformed Content-Length header", "HTTP 400", resp.startswith(b"HTTP/1.0 400") or resp.startswith(b"HTTP/1.1 400"),
          resp[:40].decode("latin-1") or "no response")
    # PT-06 slow body (slowloris): declares 100 bytes, sends 10
    resp, held = raw_http(srv.port, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{\"message\"", wait=25)
    check("PT-06", "Slow or incomplete body", "connection closed within 20 s", b"<<still open>>" not in resp and held <= 20,
          f"{'still open after' if b'<<still open>>' in resp else 'closed after'} {held:.1f} s")
    # PT-07 oversized body
    resp, held = raw_http(srv.port, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: 2000000\r\n\r\n" + b"x" * 1000)
    check("PT-07", "Oversized body (2 MB declared)", "HTTP 400 without reading it", b" 400 " in resp[:20], resp[:30].decode("latin-1"))
    # PT-08 malformed JSON / wrong types
    codes = []
    for raw in (b"not json", b"[1,2]", b'{"message": 5}', b'{"message": ""}', b'{"message": {"a": 1}}'):
        r, _ = raw_http(srv.port, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: " + str(len(raw)).encode() + b"\r\n\r\n" + raw)
        codes.append(r[9:12].decode() or "none")
    check("PT-08", "Malformed JSON and wrong field types", "HTTP 400 for each, never 500", all(c == "400" for c in codes), ", ".join(codes))
    # PT-09 path traversal on GET
    paths = ["/../src/assistant/server.py", "/%2e%2e/.env", "/.env", "/ui/../.env", "/data/assistant.db"]
    gcodes = []
    for p in paths:
        try:
            with urllib.request.urlopen(srv.base + p, timeout=5) as r:
                gcodes.append(r.status)
        except urllib.error.HTTPError as e:
            gcodes.append(e.code)
    check("PT-09", "Path traversal / reading files over GET", "404 for every path", all(c == 404 for c in gcodes), ", ".join(map(str, gcodes)))
    # PT-10 stored XSS
    xss = "<img src=x onerror=alert(1)>"
    _, b, _ = post(srv.base, {"message": f"save note: {xss} - <script>alert(1)</script>"})
    ui = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    check("PT-10", "Stored XSS through a note", "returned as data; page never uses innerHTML",
          "innerHTML" not in ui and "insertAdjacentHTML" not in ui, f"innerHTML uses in ui/index.html: {ui.count('innerHTML')}")
    # PT-11 / PT-12 headers on the page
    with urllib.request.urlopen(srv.base + "/", timeout=5) as r:
        headers = {k.lower(): v for k, v in r.headers.items()}
    server_hdr = headers.get("server", "")
    check("PT-11", "Version disclosure in the Server header", "no Python/library version", "Python" not in server_hdr, server_hdr or "(none)")
    wanted = ["x-content-type-options", "x-frame-options", "content-security-policy", "referrer-policy"]
    missing = [h for h in wanted if h not in headers]
    check("PT-12", "Browser security headers on the page", "all present: " + ", ".join(wanted), not missing,
          "missing: " + ", ".join(missing) if missing else "all present")
    # PT-13 ReDoS: long crafted messages
    worst = 0.0
    for msg in ["a " * 7000, "due friday, " * 1200, "essay " * 2500 + "due", "1" * 15000, "thứ 2 " * 2500]:
        _, _, sec = post(srv.base, {"message": msg[:15000]}, timeout=60)
        worst = max(worst, sec)
    check("PT-13", "Regex denial of service (15 KB crafted input)", "every reply in < 2 s", worst < 2, f"slowest {worst:.2f} s")
    # PT-14 error messages do not leak internals
    r, _ = raw_http(srv.port, b"POST /api/nope HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}")
    check("PT-14", "Unknown endpoint and errors", "short JSON error, no stack trace", b"Traceback" not in r and b"404" in r[:20], r[:40].decode("latin-1"))
    srv.stop()

    if public:
        # PT-15 rate limit on the public site (10 rapid chat requests; sessions are deleted afterwards)
        codes, sids = [], []
        for _ in range(10):
            s, b, _ = post(PUBLIC, {"message": "hello"}, timeout=20)
            codes.append(s)
            if b.get("session_id"):
                sids.append(b["session_id"])
        time.sleep(11)
        for sid in sids:
            post(PUBLIC, {"session_id": sid}, path="/api/reset")
        check("PT-15", "Rate limit on assistant.triseet.site", "requests beyond 8 in 10 s are blocked", any(c == 429 for c in codes), ", ".join(map(str, codes)))
        # PT-16 model port not reachable from the internet
        try:
            socket.create_connection(("assistant.triseet.site", 11434), timeout=5).close()
            reach = "open"
        except OSError:
            reach = "not reachable"
        check("PT-16", "Ollama port 11434 from the internet", "not reachable", reach == "not reachable", reach)
        # PT-17 HTTP is redirected to HTTPS
        req = urllib.request.Request("http://assistant.triseet.site/", headers=UA, method="HEAD")

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        try:
            urllib.request.build_opener(NoRedirect).open(req, timeout=10)
            red = "no redirect"
        except urllib.error.HTTPError as e:
            red = f"{e.code} → {e.headers.get('Location')}"
        check("PT-17", "Plain HTTP on the public site", "301 redirect to https", red.startswith("301") and "https://" in red, red)

    md = ["## 5. Security / penetration test", "",
          "Run against a local copy of the server (and three safe checks on the team's own public site). "
          "No authentication exists by design: a random session id is the only key to a student's data.", "",
          "| ID | Test | Expected | Actual | Result |", "|---|---|---|---|---|"]
    md += [f"| {r['id']} | {r['test']} | {r['expected']} | {r['actual']} | {'Pass' if r['pass'] else '**Fail**'} |" for r in rows]
    md.append(f"\n{sum(r['pass'] for r in rows)}/{len(rows)} passed.")
    return md, {"checks": rows}


# ---------------------------------------------------------------- 6. bug reproduction across versions

def checkout(commit: str, into: Path) -> Path:
    archive = into / f"{commit}.zip"
    subprocess.run(["git", "archive", "--format=zip", "-o", str(archive), commit, "src", "data", "ui"], cwd=ROOT, check=True)
    root = into / commit
    with zipfile.ZipFile(archive) as z:
        z.extractall(root)
    return root


def run_py(root: Path, code: str) -> str:
    out = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(root / 'src')!r}); " + code],
                         capture_output=True, text=True, encoding="utf-8", env={**os.environ, "ASSISTANT_LLM": "none"})
    return (out.stdout or out.stderr).strip().splitlines()[-1] if (out.stdout or out.stderr).strip() else ""


def probe_server(root: Path, how: str) -> str:
    srv = Server(root, stdio_none=(how == "pythonw"))
    try:
        if how == "pythonw":
            s, b, _ = post(srv.base, {"message": "hello"}, timeout=10)
            return f"HTTP {s}" if s else "no response (connection closed)"
        if how == "content-length":
            r, _ = raw_http(srv.port, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Length: abc\r\n\r\n{}")
            return r[:12].decode("latin-1") or "no response (connection closed)"
        if how == "slow":
            r, held = raw_http(srv.port, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Length: 100\r\n\r\n{", wait=25)
            return f"still open after {held:.0f} s" if b"<<still open>>" in r else f"closed after {held:.0f} s"
        if how == "fixation":
            _, b, _ = post(srv.base, {"message": "hello", "session_id": "ab" * 16})
            return "client id accepted" if b.get("session_id") == "ab" * 16 else "new id issued"
        if how == "locked":
            r = ramp_level(srv.base, 200, 10)
            return f"{r['errors']} of {r['requests']} requests failed {r['codes'] or ''}".strip()
        if how == "headers":
            with urllib.request.urlopen(srv.base + "/", timeout=5) as r:
                return "nosniff/CSP present" if r.headers.get("X-Content-Type-Options") else f"no security headers; Server: {r.headers.get('Server')}"
    finally:
        srv.stop()
    return ""


BUGS = [
    {"id": "BUG-01", "title": "Busy days after the first one in a list are ignored", "severity": "High",
     "found": "Evaluation scenario C04", "before": "9ad5025", "after": "HEAD",
     "steps": "Send: \"Essay due Wednesday, 2 hours. 2 hours on weekdays. Busy on Monday, Tuesday and Wednesday.\"",
     "expected": "Mon, Tue and Wed blocked; warning that the essay does not fit",
     "cause": "Busy days were read one comma-separated piece at a time; \"Tuesday\" alone had no \"busy\" word.",
     "fix": "918eafb: a busy/hours rule carries over a following list of day names", "test": "tests/test_parser.py::test_busy_and_study_time_carry_over_a_list_of_days",
     "probe": ("py", "from datetime import date; from assistant.planning.parser import parse; "
                     "print('blocked days', sorted(parse('2 hours on weekdays. Busy on Monday, Tuesday and Wednesday.', date(2026,10,26)).blocked))")},
    {"id": "BUG-02", "title": "Casual Vietnamese sentence read as one task; model never asked", "severity": "Medium",
     "found": "Manual check of the public site", "before": "4c77594", "after": "HEAD",
     "steps": "Send: \"Tuần này mình phải lo vụ lab hóa với cái slide nhóm môn kinh tế, cuối tuần nộp\"",
     "expected": "Two tasks (Lab hóa, Slide nhóm môn kinh tế) due this Sunday",
     "cause": "\"với\" did not split tasks, \"cuối tuần\" was not a deadline, and any rule match skipped the model.",
     "fix": "9ad5025: Vietnamese splitting and deadline words; long titles go to the model", "test": "tests/test_vietnamese.py::test_casual_vietnamese_shares_the_closing_deadline",
     "probe": ("py", "from datetime import date; from assistant.planning.parser import parse; "
                     "r = parse('Tuần này mình phải lo vụ lab hóa với cái slide nhóm môn kinh tế, cuối tuần nộp', date(2026,11,21), lang='vi'); "
                     "print(len(r.tasks), 'task(s):', [t.title for t in r.tasks])")},
    {"id": "BUG-03", "title": "Every request fails when the server runs without a console (pythonw)", "severity": "Critical",
     "found": "Deployment on the RTX PC (auto-start task)", "before": "4c77594", "after": "HEAD",
     "steps": "Start the server with pythonw.exe (sys.stdout/sys.stderr are None) and send any message",
     "expected": "HTTP 200",
     "cause": "http.server writes each request log line to sys.stderr, which is None under pythonw, so every handler crashed.",
     "fix": "e1c7996: send output to data/server.log when there is no console", "test": "eval/quality_eval.py bugs (BUG-03 probe)",
     "probe": ("server", "pythonw")},
    {"id": "BUG-04", "title": "Malformed Content-Length closes the connection without an answer", "severity": "Medium",
     "found": "Penetration test PT-05", "before": "c2a1ef5", "after": "HEAD",
     "steps": "POST /api/chat with header \"Content-Length: abc\"",
     "expected": "HTTP 400",
     "cause": "int() on the header raised ValueError outside any error handling.",
     "fix": "server.py: invalid Content-Length is treated as a bad request", "test": "tests/test_security.py::test_malformed_content_length_gets_400",
     "probe": ("server", "content-length")},
    {"id": "BUG-05", "title": "Incomplete request body holds a server thread forever (slowloris)", "severity": "High",
     "found": "Penetration test PT-06", "before": "c2a1ef5", "after": "HEAD",
     "steps": "Declare Content-Length: 100, send 1 byte, keep the connection open",
     "expected": "Server gives up and closes the connection",
     "cause": "No socket timeout on the request handler, so the read blocks with no limit; many such connections exhaust threads.",
     "fix": "server.py: 15 s socket timeout on every connection", "test": "tests/test_security.py::test_slow_body_is_dropped",
     "probe": ("server", "slow")},
    {"id": "BUG-06", "title": "Server adopts a session id chosen by the client (session fixation)", "severity": "Medium",
     "found": "Penetration test PT-04", "before": "c2a1ef5", "after": "HEAD",
     "steps": "POST a message with a made-up 32-hex session_id that does not exist",
     "expected": "Server ignores it and issues its own random id",
     "cause": "Any well-formed id was used to create a new session.",
     "fix": "server.py: only ids that already exist are accepted", "test": "tests/test_security.py::test_unknown_session_id_is_replaced",
     "probe": ("server", "fixation")},
    {"id": "BUG-07", "title": "No browser security headers; Server header shows the Python version", "severity": "Low",
     "found": "Penetration test PT-11, PT-12", "before": "c2a1ef5", "after": "HEAD",
     "steps": "GET / and read the response headers",
     "expected": "X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Referrer-Policy; no version",
     "cause": "BaseHTTPRequestHandler defaults; no headers were added.",
     "fix": "server.py: security headers on every response, neutral Server header", "test": "tests/test_security.py::test_security_headers",
     "probe": ("server", "headers")},
    {"id": "BUG-08", "title": "HTTP 500 \"database is locked\" under 200 concurrent clients", "severity": "Medium",
     "found": "Stress test (concurrency ramp)", "before": "3af6f1d", "after": "HEAD",
     "steps": "200 clients send 10 requests each at the same moment",
     "expected": "Every request answered; slower is acceptable, failing is not",
     "cause": "Each SQLite writer waited up to 10 s for the write lock, then raised OperationalError, reported as HTTP 500.",
     "fix": "server.py: writes queue on one in-process lock; if SQLite is still busy the reply is 503 with Retry-After",
     "test": "tests/test_security.py::test_concurrent_writes_do_not_fail", "probe": ("server", "locked")},
]


def bugs_section() -> tuple[list[str], dict]:
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        roots = {"HEAD": ROOT}
        for bug in BUGS:
            for ref in (bug["before"], bug["after"]):
                if ref not in roots:
                    roots[ref] = checkout(ref, Path(tmp))
            kind, arg = bug["probe"]
            actual = {ref: (run_py(roots[ref], arg) if kind == "py" else probe_server(roots[ref], arg)) for ref in (bug["before"], bug["after"])}
            results.append({**{k: v for k, v in bug.items() if k != "probe"}, "actual_before": actual[bug["before"]], "actual_after": actual[bug["after"]]})
    md = ["## 6. Bug report (confirmed, reproduced on the old and the new version)", "",
          "| ID | Bug | Severity | Found by | Old version → actual | Fixed version → actual |", "|---|---|---|---|---|---|"]
    md += [f"| {b['id']} | {b['title']} | {b['severity']} | {b['found']} | `{b['before']}` → {b['actual_before']} | "
           f"`{version() if b['after'] == 'HEAD' else b['after']}` → {b['actual_after']} |" for b in results]
    for b in results:
        md += ["", f"**{b['id']} {b['title']}** ({b['severity']})", "",
               f"- Steps: {b['steps']}", f"- Expected: {b['expected']}", f"- Root cause: {b['cause']}",
               f"- Fix: {b['fix']}", f"- Regression test: `{b['test']}`"]
    return md, {"bugs": results}


# ---------------------------------------------------------------- main

SECTIONS = {"unit": unit_section, "sim": sim_section, "stress": stress_section, "profile": profile_section,
            "security": security_section, "bugs": bugs_section}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("section", choices=[*SECTIONS, "all"])
    parser.add_argument("--public", action="store_true", help="include checks against assistant.triseet.site")
    args = parser.parse_args()
    names = list(SECTIONS) if args.section == "all" else [args.section]
    ver = version()
    md = [f"# Quality evaluation — version `{ver}`", "",
          f"Run {time.strftime('%Y-%m-%d %H:%M:%S')} on one Windows 11 laptop, Python {sys.version.split()[0]}. "
          "Server under test in its own process, temporary SQLite file, rules path unless stated.", ""]
    data = {"version": ver}
    for name in names:
        fn = SECTIONS[name]
        section_md, section_data = fn(args.public) if name in ("sim", "security") else fn()
        md += section_md + [""]
        data[name] = section_data
        print("\n".join(section_md), flush=True)
    out = ROOT / "eval" / "results" / f"quality-{ver}" if args.section == "all" else ROOT / "eval" / "results" / f"quality-{ver}-{args.section}"
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"\nResults: {out.with_suffix('.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

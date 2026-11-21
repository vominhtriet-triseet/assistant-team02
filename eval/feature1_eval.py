"""Evaluate Feature 1 (Planning and Task Management) as the course evaluation guide asks.

Criterion -> Metric -> Target -> Evidence. Expected results live in
eval/feature1_scenarios.json and were written before the prototype was run.

    python eval/feature1_eval.py            # correctness, efficiency, reliability, scalability
    python eval/feature1_eval.py --public   # also time the local-LLM path on assistant.triseet.site

Writes eval/results/feature1-<commit>.json and .md with every raw observation.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from collections import defaultdict
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from assistant import storage  # noqa: E402
from assistant.planning.models import EXAM_KINDS  # noqa: E402
from assistant.server import make_server  # noqa: E402
from assistant.service import Session, process_request  # noqa: E402

SCENARIOS = json.loads((ROOT / "eval" / "feature1_scenarios.json").read_text(encoding="utf-8"))
TODAY = date.fromisoformat(SCENARIOS["today"])
PUBLIC = "https://assistant.triseet.site"
LLM_MESSAGE = "hôm nay phải hoàn thành bài tập mà thầy giao từ buổi trước liên quan tới đồ thị và cây nhị phân"


def p90(values: list[float]) -> float:
    return statistics.quantiles(values, n=10, method="inclusive")[8] if len(values) > 1 else values[0]


def find(tasks: list[dict], fragment: str) -> list[dict]:
    return [t for t in tasks if fragment.lower() in t["title"].lower()]


def oracle(schedule: list[dict], tasks: list[dict], warnings: list[str], cap: list[float],
           dependencies: set, today: date) -> list[str]:
    """Hard-constraint violations that the response does NOT disclose in a warning."""
    violations = []
    warned = " ".join(warnings).lower()
    by_id = {t["id"]: t for t in tasks}
    placed: dict[int, float] = defaultdict(float)
    first: dict[int, date] = {}
    last: dict[int, date] = {}
    for day in schedule:
        d = date.fromisoformat(day["date"])
        work = [b for b in day["blocks"] if not b["event"]]
        used = sum(b["hours"] for b in work)
        if used > cap[d.weekday()] + 1e-6:
            violations.append(f"{d}: {used:g} h planned, only {cap[d.weekday()]:g} h available")
        if work and d < today:
            violations.append(f"{d}: work planned in the past")
        for b in work:
            task = by_id[b["task_id"]]
            placed[task["id"]] += b["hours"]
            first.setdefault(task["id"], d)
            last[task["id"]] = d
            if task["status"] == "done":
                violations.append(f"{task['title']}: work planned after it was marked done")
            if task["deadline"]:
                limit = date.fromisoformat(task["deadline"]) - timedelta(days=1 if task["kind"] in EXAM_KINDS else 0)
                if d > limit:
                    violations.append(f"{task['title']}: work on {d}, after its last allowed day {limit}")
    for task in tasks:
        if task["status"] != "done" and abs(placed[task["id"]] - task["hours"]) > 0.01 and task["title"].lower() not in warned:
            violations.append(f"{task['title']}: {placed[task['id']]:g} of {task['hours']:g} h placed, not disclosed")
    if "loop" not in warned and "vòng tròn" not in warned:
        for a, b in dependencies:
            if a in first and b in last and first[a] < last[b]:
                violations.append(f"{by_id[a]['title']} starts before {by_id[b]['title']} is finished")
    return violations


def run_scenario(sc: dict) -> dict:
    session = Session()
    start = time.perf_counter()
    for message in sc["turns"]:
        response = process_request(message, session, today=TODAY)
    elapsed = time.perf_counter() - start
    tasks, problems = response["tasks"], []

    if "tasks" in sc and len(tasks) != sc["tasks"]:
        problems.append(f"expected {sc['tasks']} task(s), got {len(tasks)}: {[t['title'] for t in tasks]}")
    if "min_tasks" in sc and len(tasks) < sc["min_tasks"]:
        problems.append(f"expected at least {sc['min_tasks']} tasks from the goal, got {len(tasks)}: {[t['title'] for t in tasks]}")
    for key, field in (("deadlines", "deadline"), ("times", "deadline_time"), ("hours", "hours"), ("priority", "priority"),
                       ("status", "status"), ("source", "source"), ("hours_assumed", "hours_assumed")):
        for fragment, want in sc.get(key, {}).items():
            match = find(tasks, fragment)
            if not match:
                problems.append(f"no task matching '{fragment}'")
            elif match[0][field] != want:
                problems.append(f"'{fragment}' {field}: expected {want}, got {match[0][field]}")
    if sc.get("intent") and response["intent"] != sc["intent"]:
        problems.append(f"intent: expected {sc['intent']}, got {response['intent']}")
    if sc.get("lang") and response["lang"] != sc["lang"]:
        problems.append(f"reply language: expected {sc['lang']}, got {response['lang']}")
    for key, haystack in (("message_contains", [response["message"]]), ("assumption_contains", response["assumptions"]),
                          ("facts_contains", response["facts"]), ("warning_contains", response["warnings"])):
        if key in sc and not any(sc[key].lower() in text.lower() for text in haystack):
            problems.append(f"{key.split('_')[0]} should mention '{sc[key]}'")
    for a, b in sc.get("deps", []):
        ids = {(find(tasks, a) or [{}])[0].get("id"), (find(tasks, b) or [{}])[0].get("id")}
        if len(ids) != 2 or (find(tasks, a)[0]["id"], find(tasks, b)[0]["id"]) not in session.dependencies:
            problems.append(f"dependency '{a}' after '{b}' was not recorded")

    schedule, violations = response["schedule"], []
    if sc["feasible"] is None:
        if schedule:
            problems.append("a complete-looking schedule was shown although information is missing")
    else:
        # A task missing from the schedule is caught by the oracle unless a warning names it.
        if sc["feasible"] and response["warnings"]:
            problems.append(f"unexpected warning: {response['warnings']}")
        if sc["feasible"] is False and not response["warnings"]:
            problems.append("infeasible request was not disclosed")
        if schedule and not any(w in response["message"].lower() for w in ("draft", "nháp")):
            problems.append("schedule is not presented as a draft/proposal")
        violations = oracle(schedule or [], tasks, response["warnings"], sc["cap"], session.dependencies, TODAY)

    with closing(storage.connect(":memory:")) as conn:  # persistence: nothing lost or duplicated
        storage.save(conn, "eval", session)
        reloaded = storage.load(conn, "eval")
    persisted = [t.to_dict() for t in reloaded.tasks] == tasks

    return {"id": sc["id"], "category": sc["category"], "fr": sc["fr"], "feasible": sc["feasible"],
            "pass": not problems and not violations and persisted, "problems": problems, "hard_violations": violations,
            "persisted": persisted, "intent": response["intent"], "warnings": response["warnings"],
            "tasks": [(t["title"], t["deadline"], t["hours"], t["status"]) for t in tasks],
            "schedule": [(d["date"], [(b["title"], b["hours"]) for b in d["blocks"]]) for d in schedule or []],
            "seconds": round(elapsed, 4)}


# ---------------------------------------------------------------- HTTP runs (efficiency, reliability, scalability)

def post(base: str, path: str, body: dict, timeout: float = 180) -> tuple[int, dict, float]:
    request = urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "feature1-eval"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as r:
            return r.status, json.loads(r.read()), time.perf_counter() - start
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}"), time.perf_counter() - start


def http_runs(base: str, db_path: str, repeats: int) -> dict:
    final_times, all_times, runs = [], [], []
    for sc in SCENARIOS["scenarios"]:
        for repeat in range(repeats):
            sid, ok, error = None, True, ""
            for i, message in enumerate(sc["turns"]):
                status, body, seconds = post(base, "/api/chat", {"message": message, "session_id": sid})
                all_times.append(seconds)
                if i == len(sc["turns"]) - 1:
                    final_times.append(seconds)
                if status != 200:
                    ok, error = False, f"HTTP {status}"
                    break
                sid = body["session_id"]
            if ok:  # the stored record must match what the student was shown
                with closing(storage.connect(db_path)) as conn:
                    stored = storage.load(conn, sid)
                ids = [t.id for t in stored.tasks]
                if len(stored.tasks) != len(body["tasks"]) or len(set(ids)) != len(ids):
                    ok, error = False, "lost or duplicated task in storage"
            runs.append({"scenario": sc["id"], "repeat": repeat + 1, "ok": ok, "error": error})
    return {"final_times": final_times, "all_times": all_times, "runs": runs}


def scale_runs(base: str, sizes=(10, 30, 50), repeats: int = 5) -> list[dict]:
    today = date.today()
    results = []
    for n in sizes:
        tasks = "; ".join(f"report {k + 1} due {(today + timedelta(days=1 + (13 * k) // n)).isoformat()} for 1 hour" for k in range(n))
        status, body, seconds = post(base, "/api/chat", {"message": f"{tasks}. 4 hours a day."})
        sid, times, ok_runs, violations = body.get("session_id"), [], 0, 0
        for _ in range(repeats):
            status, body, seconds = post(base, "/api/chat", {"message": "show my plan", "session_id": sid})
            times.append(seconds)
            bad = oracle(body.get("schedule") or [], body.get("tasks", []), body.get("warnings", []), [4] * 7, set(), today)
            violations += len(bad)
            ok_runs += status == 200 and len(body.get("tasks", [])) == n and not bad and not body.get("warnings")
        results.append({"tasks": n, "median_s": statistics.median(times), "p90_s": p90(times), "success": ok_runs,
                        "runs": repeats, "violations": violations, "times": times})
    return results


def public_llm_runs(repeats: int = 5) -> list[dict]:
    """Time the local Qwen3 path through Cloudflare. Spaced out to stay under the site's rate limit."""
    out = []
    for _ in range(repeats):
        status, body, seconds = post(PUBLIC, "/api/chat", {"message": LLM_MESSAGE})
        out.append({"status": status, "seconds": round(seconds, 2), "source": [t["source"] for t in body.get("tasks", [])],
                    "warnings": body.get("warnings", [])})
        if body.get("session_id"):
            post(PUBLIC, "/api/reset", {"session_id": body["session_id"]})
        time.sleep(3)
    return out


# ---------------------------------------------------------------- report

def pct(a: int, b: int) -> str:
    return f"{a}/{b} = {100 * a / b:.1f}%" if b else "n/a"


def status(met: bool | None) -> str:
    return {True: "Met", False: "Not met", None: "Not measurable yet"}[met]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="store_true", help="also time the local-LLM path on the public site")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "src"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    version = commit + ("-dirty" if dirty else "")
    scenarios = SCENARIOS["scenarios"]
    results = [run_scenario(sc) for sc in scenarios]

    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "eval.db")
        server = make_server("127.0.0.1", 0, db_path=db)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        http = http_runs(base, db, args.repeats)
        scale = scale_runs(base)
        server.shutdown()
        server.server_close()
    llm_runs = public_llm_runs() if args.public else []

    core = [r for r in results if r["category"] != "FR check"]
    passed = sum(r["pass"] for r in results)
    core_passed = sum(r["pass"] for r in core)
    hard = sum(len(r["hard_violations"]) for r in results)
    infeasible = [r for r in results if r["feasible"] is False]
    disclosed = sum(1 for r in infeasible if r["warnings"] and not any("should mention" in p or "not disclosed" in p for p in r["problems"]))
    ambiguous = [r for r in results if r["feasible"] is None]
    clarified = sum(1 for r in ambiguous if r["pass"])
    ok_runs = sum(r["ok"] for r in http["runs"])
    base10 = next(s for s in scale if s["tasks"] == 10)
    s50 = next(s for s in scale if s["tasks"] == 50)
    ratio = s50["median_s"] / base10["median_s"]
    fr_rows = []
    for fr in ("FR-01", "FR-02", "FR-03", "FR-04", "FR-05", "FR-06"):
        tagged = [r for r in results if fr in r["fr"]]
        fr_rows.append((fr, sum(r["pass"] for r in tagged), len(tagged), [r["id"] for r in tagged if not r["pass"]]))

    med, high = statistics.median(http["final_times"]), p90(http["final_times"])
    rows = [
        ("Correctness", "Schedule validity rate (30 core scenarios)", ">= 90%", pct(core_passed, len(core)), core_passed / len(core) >= 0.9),
        ("Correctness", "All scenarios incl. FR checks", "(info)", pct(passed, len(results)), None),
        ("Efficiency", "Median / P90 response time, rules path (HTTP + SQLite)", "<= 5 s / <= 10 s", f"{med * 1000:.1f} ms / {high * 1000:.1f} ms", med <= 5 and high <= 10),
        ("Reliability", f"Successful-run rate ({len(http['runs'])} conversations)", ">= 98%, 0 lost/duplicated", pct(ok_runs, len(http["runs"])), ok_runs / len(http["runs"]) >= 0.98),
        ("Usability", "Unaided task completion (5 users)", ">= 80%", "not run yet", None),
        ("Scalability", "50-task median vs 10-task baseline; success", "<= 2x; >= 95%", f"{ratio:.2f}x; {pct(s50['success'], s50['runs'])}", ratio <= 2 and s50["success"] / s50["runs"] >= 0.95),
        ("Constraint handling", "Undisclosed hard-constraint violations", "0", str(hard), hard == 0),
        ("Constraint handling", "Infeasible cases disclosed", ">= 90%", pct(disclosed, len(infeasible)), disclosed / len(infeasible) >= 0.9),
        ("Constraint handling", "Missing-information cases clarified (FR-03)", "100%", pct(clarified, len(ambiguous)), clarified == len(ambiguous)),
    ]
    if llm_runs:
        times = [r["seconds"] for r in llm_runs if r["status"] == 200]
        rows.insert(3, ("Efficiency", f"Median / P90, local-LLM path via Cloudflare ({len(times)} runs)", "<= 5 s / <= 10 s",
                        f"{statistics.median(times):.2f} s / {p90(times):.2f} s" if times else "failed",
                        bool(times) and statistics.median(times) <= 5 and p90(times) <= 10))

    md = [f"# Feature 1 evaluation results — version `{version}`", "",
          f"Run {datetime.now().isoformat(timespec='seconds')} on {platform.system()} {platform.release()}, Python {platform.python_version()}. "
          f"Scenario dates are resolved against {TODAY} (Monday). Rules-only mode (no language model) unless stated.", "",
          "## Summary", "", "| Criterion | Metric | Target | Evidence | Status |", "|---|---|---|---|---|"]
    md += [f"| {c} | {m} | {t} | {e} | {status(s) if c != 'Correctness' or 'core' in m else 'info'} |" for c, m, t, e, s in rows]
    md += ["", "## Functional requirements", "", "| FR | Scenarios passed | Failed scenarios |", "|---|---|---|"]
    md += [f"| {fr} | {pct(p, n)} | {', '.join(f) or '-'} |" for fr, p, n, f in fr_rows]
    md += ["", "## Scalability", "", "| Tasks | Median | P90 | Successful runs | Violations |", "|---|---|---|---|---|"]
    md += [f"| {s['tasks']} | {s['median_s'] * 1000:.1f} ms | {s['p90_s'] * 1000:.1f} ms | {s['success']}/{s['runs']} | {s['violations']} |" for s in scale]
    if llm_runs:
        md += ["", "## Local-LLM path (assistant.triseet.site, Qwen3 14B on RTX 5070)", "",
               "| Run | HTTP | Seconds | Task source |", "|---|---|---|---|"]
        md += [f"| {i + 1} | {r['status']} | {r['seconds']} | {', '.join(r['source']) or '-'} |" for i, r in enumerate(llm_runs)]
    md += ["", "## Scenario results", "", "| ID | Category | FR | Result | Problems / undisclosed violations |", "|---|---|---|---|---|"]
    md += [f"| {r['id']} | {r['category']} | {', '.join(r['fr'])} | {'Pass' if r['pass'] else 'Fail'} | "
           f"{'; '.join(r['problems'] + r['hard_violations'] + ([] if r['persisted'] else ['storage round trip changed tasks'])) or '-'} |" for r in results]
    failed_runs = [r for r in http["runs"] if not r["ok"]]
    failed_text = ", ".join("{}#{} ({})".format(r["scenario"], r["repeat"], r["error"]) for r in failed_runs) or "none"
    md += ["", f"Failed HTTP runs: {failed_text}."]

    out = ROOT / "eval" / "results" / f"feature1-{version}"
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps({"version": version, "today": str(TODAY), "scenarios": results, "http": http,
                                                    "scale": scale, "public_llm": llm_runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md[:len(rows) + 8]))
    print(f"\nFailed scenarios: {', '.join(r['id'] for r in results if not r['pass']) or 'none'}")
    print(f"Full results: {out.with_suffix('.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

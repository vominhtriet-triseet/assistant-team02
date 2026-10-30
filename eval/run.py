"""Run the benchmark in eval/cases.csv against process_request.

Each case starts with an empty session and a fixed date (Monday 26 Oct 2026), so the
results do not depend on when the script runs. A case passes when the intent matches
and the expected text appears in the message or warnings (case-insensitive).

    python eval/run.py
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

from assistant.service import Session, process_request

TODAY = date(2026, 10, 26)
CASES = Path(__file__).with_name("cases.csv")


def run() -> int:
    with CASES.open(encoding="utf-8", newline="") as f:
        cases = list(csv.DictReader(f))
    failures = 0
    for case in cases:
        response = process_request(case["input"], Session(), today=TODAY)
        haystack = " ".join([response["message"], *response["warnings"]]).lower()
        ok = response["intent"] == case["expected_intent"] and case["expected_text"].lower() in haystack
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  #{case['id']:>2}  {case['input']}")
        if not ok:
            print(f"        expected {case['expected_intent']!r} containing {case['expected_text']!r}")
            print(f"        got      {response['intent']!r}: {response['message'][:120]!r}")
    print(f"\n{len(cases) - failures}/{len(cases)} cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())

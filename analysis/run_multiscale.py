#!/usr/bin/env python3
"""Run a reproducible multi-scale scheduler benchmark matrix."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICIES = "SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ"
WORK_VALUES = (5, 10, 20, 30, 40, 60, 80, 100)
JOB_VALUES = (1, 3, 6, 9, 12)


def run_case(label: str, output: Path, jobs: int, work: int) -> None:
    command = [
        sys.executable,
        "scripts/run-schedbench.py",
        "--policies",
        POLICIES,
        "--jobs",
        str(jobs),
        "--work",
        str(work),
        "--cpu-priority",
        "1",
        "--io-priority",
        "9",
        "--mixed-priority",
        "5",
        "--repeat",
        "3",
        "--timeout",
        "300",
        "--output",
        str(output),
    ]
    print(f"[multiscale] {label}: jobs={jobs} work={work}", flush=True)
    for attempt in range(1, 4):
        try:
            subprocess.run(command, cwd=ROOT, check=True)
            return
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            print(
                f"[multiscale] retry {label} ({attempt + 1}/3)",
                file=sys.stderr,
                flush=True,
            )


def main() -> None:
    results = ROOT / "results"
    results.mkdir(parents=True, exist_ok=True)

    for work in WORK_VALUES:
        run_case(
            f"work{work}",
            results / f"schedbench-rr-spq-mlfq-work{work}.csv",
            jobs=6,
            work=work,
        )

    for jobs in JOB_VALUES:
        run_case(
            f"jobs{jobs}",
            results / f"schedbench-rr-spq-mlfq-jobs{jobs}.csv",
            jobs=jobs,
            work=40,
        )

    print("[multiscale] completed all cases")


if __name__ == "__main__":
    main()

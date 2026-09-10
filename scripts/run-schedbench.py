#!/usr/bin/env python3
"""Build xv6, run the common scheduler benchmark, and emit CSV results."""

import argparse
import csv
import os
import re
import selectors
import subprocess
import sys
import time
from collections import defaultdict


RESULT_RE = re.compile(
    r"SCHEDBENCH job=(\d+) kind=(\w+) start=(\d+) first=(\d+) "
    r"finish=(\d+) service=(\d+) turnaround=(\d+) response=(\d+)"
)
END_RE = re.compile(r"SCHEDBENCH_END start=(\d+) finish=(\d+)")


def run_command(command, cwd):
    subprocess.run(command, cwd=cwd, check=True)


def build(repo, policy):
    run_command(["make", "clean"], repo)
    run_command(
        [
            "make",
            f"SCHED_DEFAULT_POLICY={policy}",
            "TOOLPREFIX=riscv64-linux-gnu-",
            "-j",
        ],
        repo,
    )


def run_qemu(repo, jobs, work):
    process = subprocess.Popen(
        ["make", "qemu", "TOOLPREFIX=riscv64-linux-gnu-", "CPUS=1"],
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output = []
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    os.set_blocking(process.stdout.fileno(), False)
    deadline = time.time() + 120
    launch_time = time.time()
    sent = False

    try:
        while time.time() < deadline:
            events = selector.select(timeout=0.2)
            if not events:
                # xv6 的 shell 提示符可能没有及时产生完整换行，
                # 因此除了启动提示外，再用短延迟作为发送命令的兜底。
                if not sent and time.time() - launch_time >= 2:
                    process.stdin.write(f"schedbench {jobs} {work}\n")
                    process.stdin.flush()
                    sent = True
                if process.poll() is not None:
                    break
                continue

            try:
                chunk = os.read(process.stdout.fileno(), 4096).decode(
                    "utf-8", errors="replace"
                )
            except BlockingIOError:
                continue
            if chunk:
                output.append(chunk)
                joined = "".join(output)
                if "init: starting sh" in joined and not sent:
                    process.stdin.write(f"schedbench {jobs} {work}\n")
                    process.stdin.flush()
                    sent = True
                if END_RE.search(joined):
                    break
            else:
                break

        output_text = "".join(output)
        if not END_RE.search(output_text):
            raise RuntimeError("benchmark did not finish within 120 seconds")
    finally:
        if process.poll() is None:
            process.stdin.write("\x01x")
            process.stdin.flush()
            process.wait(timeout=10)

    return "".join(output)


def parse_output(output, policy):
    rows = []
    experiment_start = None
    experiment_finish = None

    for line in output.splitlines():
        match = RESULT_RE.search(line)
        if match:
            job, kind, start, first, finish, service, turnaround, response = (
                match.groups()
            )
            rows.append(
                {
                    "policy": policy,
                    "job": int(job),
                    "kind": kind,
                    "start": int(start),
                    "first": int(first),
                    "finish": int(finish),
                    "service": int(service),
                    "turnaround": int(turnaround),
                    "response": int(response),
                }
            )
        match = END_RE.search(line)
        if match:
            experiment_start, experiment_finish = map(int, match.groups())

    if not rows or experiment_start is None or experiment_finish is None:
        raise RuntimeError("could not parse benchmark output")

    elapsed = experiment_finish - experiment_start
    for row in rows:
        row["weighted_turnaround"] = (
            row["turnaround"] / row["service"] if row["service"] else 0.0
        )
        row["throughput"] = len(rows) / elapsed if elapsed else 0.0
    return rows


def print_results(rows, output_path):
    fields = [
        "policy",
        "job",
        "kind",
        "start",
        "first",
        "finish",
        "service",
        "turnaround",
        "weighted_turnaround",
        "response",
        "throughput",
    ]
    if output_path:
        parent = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(parent, exist_ok=True)
    stream = open(output_path, "w", newline="") if output_path else sys.stdout
    try:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if output_path:
            stream.close()


def print_summary(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["policy"], row["kind"])].append(row)

    print("\n[schedbench] summary", file=sys.stderr)
    print(
        "policy,kind,count,avg_turnaround,avg_weighted_turnaround,"
        "avg_response,throughput",
        file=sys.stderr,
    )
    for (policy, kind), group in groups.items():
        count = len(group)
        avg_turnaround = sum(row["turnaround"] for row in group) / count
        avg_weighted = sum(row["weighted_turnaround"] for row in group) / count
        avg_response = sum(row["response"] for row in group) / count
        throughput = group[0]["throughput"]
        print(
            f"{policy},{kind},{count},{avg_turnaround:.2f},"
            f"{avg_weighted:.2f},{avg_response:.2f},{throughput:.4f}",
            file=sys.stderr,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policies",
        default="SCHED_RR",
        help="comma-separated build-time policies, e.g. SCHED_RR,SCHED_MLFQ",
    )
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--work", type=int, default=40)
    parser.add_argument("--output", help="write CSV here; otherwise print CSV")
    args = parser.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_rows = []
    for policy in [item.strip() for item in args.policies.split(",") if item.strip()]:
        print(f"[schedbench] building {policy}", file=sys.stderr)
        build(repo, policy)
        output = run_qemu(repo, args.jobs, args.work)
        all_rows.extend(parse_output(output, policy))

    print_results(all_rows, args.output)
    print_summary(all_rows)


if __name__ == "__main__":
    main()

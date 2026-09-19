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
from pathlib import Path


RESULT_RE = re.compile(r"^SCHEDBENCH\s+(.*)$")
END_RE = re.compile(r"SCHEDBENCH_END start=(\d+) finish=(\d+)")
INT_FIELDS = {
    "job",
    "start",
    "first",
    "finish",
    "service",
    "turnaround",
    "response",
    "priority",
    "queue",
    "slice",
    "run_ticks",
    "ready_count",
    "ready_ticks",
    "total_ready_time",
    "wait_count",
    "schedule_count",
    "create_tick",
    "first_run_tick",
    "kernel_response",
    "policy",
}


def run_command(command, cwd):
    subprocess.run(command, cwd=cwd, check=True)


def cleanup_intermediate_artifacts(repo):
    """Keep kernel/kernel and fs.img, but remove build-only generated files."""
    root = Path(repo)
    patterns = [
        "kernel/*.o",
        "kernel/*.d",
        "kernel/*.asm",
        "kernel/*.sym",
        "user/*.o",
        "user/*.d",
        "user/*.asm",
        "user/*.sym",
        "user/usys.S",
        "mkfs/mkfs",
        ".gdbinit",
    ]
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() or path.is_symlink():
                path.unlink()


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
    cleanup_intermediate_artifacts(repo)


def run_qemu(repo, jobs, work, priorities, timeout):
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
    deadline = time.time() + timeout
    launch_time = time.time()
    sent = False
    command = (
        f"schedbench {jobs} {work} "
        f"{priorities[0]} {priorities[1]} {priorities[2]}\n"
    )

    try:
        while time.time() < deadline:
            events = selector.select(timeout=0.2)
            if not events:
                # xv6 的 shell 提示符可能没有及时产生完整换行，
                # 因此除了启动提示外，再用短延迟作为发送命令的兜底。
                if not sent and time.time() - launch_time >= 2:
                    process.stdin.write(command)
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
                    process.stdin.write(command)
                    process.stdin.flush()
                    sent = True
                if END_RE.search(joined):
                    break
            else:
                break

        output_text = "".join(output)
        if not END_RE.search(output_text):
            raise RuntimeError(f"benchmark did not finish within {timeout} seconds")
    finally:
        if process.poll() is None:
            process.stdin.write("\x01x")
            process.stdin.flush()
            process.wait(timeout=10)

    return "".join(output)


def parse_key_values(text):
    result = {}
    for item in text.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key == "policy":
            result["kernel_policy"] = int(value)
            continue
        if key in INT_FIELDS:
            result[key] = int(value)
        else:
            result[key] = value
    return result


def parse_output(output, policy, run_index):
    rows = []
    experiment_start = None
    experiment_finish = None

    for line in output.splitlines():
        match = RESULT_RE.search(line)
        if match:
            row = parse_key_values(match.group(1))
            row["policy"] = policy
            row["run"] = run_index
            rows.append(row)
        match = END_RE.search(line)
        if match:
            experiment_start, experiment_finish = map(int, match.groups())

    if not rows or experiment_start is None or experiment_finish is None:
        raise RuntimeError("could not parse benchmark output")

    elapsed = experiment_finish - experiment_start
    for row in rows:
        row["experiment_start"] = experiment_start
        row["experiment_finish"] = experiment_finish
        row["elapsed"] = elapsed
        row["weighted_turnaround"] = (
            row["turnaround"] / row["service"] if row["service"] else 0.0
        )
        row["cpu_share"] = row["run_ticks"] / elapsed if elapsed else 0.0
        row["avg_ready_per_schedule"] = (
            row["total_ready_time"] / row["schedule_count"]
            if row["schedule_count"]
            else 0.0
        )
        row["throughput"] = len(rows) / elapsed if elapsed else 0.0
    return rows


def print_results(rows, output_path):
    fields = [
        "policy",
        "kernel_policy",
        "run",
        "job",
        "kind",
        "priority",
        "start",
        "first",
        "finish",
        "experiment_start",
        "experiment_finish",
        "elapsed",
        "service",
        "turnaround",
        "weighted_turnaround",
        "response",
        "kernel_response",
        "throughput",
        "queue",
        "slice",
        "run_ticks",
        "cpu_share",
        "ready_count",
        "ready_ticks",
        "total_ready_time",
        "avg_ready_per_schedule",
        "wait_count",
        "schedule_count",
        "create_tick",
        "first_run_tick",
    ]
    if output_path:
        parent = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(parent, exist_ok=True)
    stream = open(output_path, "w", newline="") if output_path else sys.stdout
    try:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
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
        "avg_response,avg_kernel_response,avg_run_ticks,"
        "avg_schedule_count,avg_total_ready_time,throughput",
        file=sys.stderr,
    )
    for (policy, kind), group in groups.items():
        count = len(group)
        avg_turnaround = sum(row["turnaround"] for row in group) / count
        avg_weighted = sum(row["weighted_turnaround"] for row in group) / count
        avg_response = sum(row["response"] for row in group) / count
        avg_kernel_response = sum(row["kernel_response"] for row in group) / count
        avg_run_ticks = sum(row["run_ticks"] for row in group) / count
        avg_schedule_count = sum(row["schedule_count"] for row in group) / count
        avg_total_ready_time = sum(row["total_ready_time"] for row in group) / count
        throughput = group[0]["throughput"]
        print(
            f"{policy},{kind},{count},{avg_turnaround:.2f},"
            f"{avg_weighted:.2f},{avg_response:.2f},"
            f"{avg_kernel_response:.2f},{avg_run_ticks:.2f},"
            f"{avg_schedule_count:.2f},{avg_total_ready_time:.2f},"
            f"{throughput:.4f}",
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
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--cpu-priority", type=int, default=1)
    parser.add_argument("--io-priority", type=int, default=9)
    parser.add_argument("--mixed-priority", type=int, default=5)
    parser.add_argument("--output", help="write CSV here; otherwise print CSV")
    args = parser.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_rows = []
    for policy in [item.strip() for item in args.policies.split(",") if item.strip()]:
        print(f"[schedbench] building {policy}", file=sys.stderr)
        build(repo, policy)
        for run_index in range(args.repeat):
            print(
                f"[schedbench] running {policy} repeat {run_index + 1}/{args.repeat}",
                file=sys.stderr,
            )
            try:
                output = run_qemu(
                    repo,
                    args.jobs,
                    args.work,
                    [args.cpu_priority, args.io_priority, args.mixed_priority],
                    args.timeout,
                )
                all_rows.extend(parse_output(output, policy, run_index))
            finally:
                cleanup_intermediate_artifacts(repo)

    print_results(all_rows, args.output)
    print_summary(all_rows)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Shared helpers for scenario scheduler experiments."""

import csv
import os
import re
import selectors
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


RESULT_RE = re.compile(
    r"SCENEBENCH\s+(?=scenario=)(.*?)(?=\r?\n|SCENEBENCH(?:\s|_|$)|$)"
)
END_RE = re.compile(r"SCENEBENCH_END start=(\d+) finish=(\d+)(?=\r?\n)")
POLICY_TARGETS = {
    "SCHED_RR": "rr",
    "SCHED_STATIC_PRIORITY": "static-priority",
    "SCHED_MLFQ": "mlfq",
}
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

CSV_FIELDS = [
    "policy",
    "kernel_policy",
    "run",
    "scenario",
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


def run_command(command, cwd):
    subprocess.run(command, cwd=cwd, check=True, stdout=sys.stderr)


def cleanup_intermediate_artifacts(repo):
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
        "schedworkloads/*.o",
        "schedworkloads/*.d",
        "schedworkloads/*.asm",
        "schedworkloads/*.sym",
        "user/usys.S",
        "mkfs/mkfs",
        ".gdbinit",
    ]
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() or path.is_symlink():
                path.unlink()


def policy_image_paths(repo, policy):
    if policy not in POLICY_TARGETS:
        supported = ", ".join(sorted(POLICY_TARGETS))
        raise ValueError(f"unsupported policy {policy}; expected one of {supported}")

    name = POLICY_TARGETS[policy]
    root = Path(repo) / "build" / "policies" / name
    return {
        "kernel": root / f"kernel-{name}",
        "fs_image": root / f"fs-{name}.img",
        "target": name,
    }


def ensure_policy_image(repo, policy):
    paths = policy_image_paths(repo, policy)
    if paths["kernel"].is_file() and paths["fs_image"].is_file():
        print(
            f"[policy] reuse {policy}: {paths['kernel'].relative_to(repo)}",
            file=sys.stderr,
        )
        return paths

    print(f"[policy] build {policy} with make {paths['target']}", file=sys.stderr)
    run_command(
        ["make", paths["target"], "TOOLPREFIX=riscv64-linux-gnu-"],
        repo,
    )
    cleanup_intermediate_artifacts(repo)

    if not paths["kernel"].is_file() or not paths["fs_image"].is_file():
        raise RuntimeError(
            f"make {paths['target']} completed without creating policy images"
        )
    return paths


def run_qemu(repo, command, end_re, timeout, label, kernel, fs_image):
    process = subprocess.Popen(
        [
            "make",
            "qemu",
            "TOOLPREFIX=riscv64-linux-gnu-",
            "CPUS=1",
            f"KERNEL={kernel}",
            f"FS_IMAGE={fs_image}",
        ],
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
    boot_seen = False
    sent = False
    last_progress = launch_time

    try:
        while time.time() < deadline:
            now = time.time()
            if boot_seen and not sent:
                process.stdin.write(command + "\n")
                process.stdin.flush()
                sent = True
                last_progress = now
                print(f"[{label}] sent command: {command}", file=sys.stderr)
            if sent and now - last_progress >= 30:
                print(
                    f"[{label}] waiting for benchmark output "
                    f"({int(now - launch_time)}s/{timeout}s)",
                    file=sys.stderr,
                )
                last_progress = now

            events = selector.select(timeout=0.2)
            if not events:
                if process.poll() is not None:
                    break
                continue

            try:
                chunk = os.read(process.stdout.fileno(), 4096).decode(
                    "utf-8", errors="replace"
                )
            except BlockingIOError:
                continue
            if not chunk:
                break

            output.append(chunk)
            joined = "".join(output)
            if "init: starting sh" in joined or "$ " in joined:
                boot_seen = True
            if end_re.search(joined):
                break

        output_text = "".join(output)
        if not end_re.search(output_text):
            tail = output_text[-2000:].replace("\r", "")
            raise RuntimeError(
                f"benchmark did not finish within {timeout} seconds\n"
                f"--- qemu output tail ---\n{tail}"
            )
    finally:
        if process.poll() is None:
            try:
                process.stdin.write("\x01x")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                # QEMU 可能已经关闭标准输入，继续等待并回收进程即可。
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    return "".join(output)


def parse_key_values(text):
    result = {}
    for item in text.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if value == "":
            continue
        if key == "policy":
            field = "kernel_policy"
        elif key in INT_FIELDS:
            field = key
        else:
            result[key] = value
            continue
        try:
            result[field] = int(value)
        except ValueError as exc:
            raise ValueError(f"invalid integer field {key}={value!r}") from exc
    return result


def parse_output(output, policy, run_index):
    rows = []
    end_match = END_RE.search(output)
    if end_match is None:
        raise RuntimeError("could not parse scenario benchmark end marker")

    experiment_start, experiment_finish = map(int, end_match.groups())
    elapsed = experiment_finish - experiment_start
    malformed = []
    for match in RESULT_RE.finditer(output):
        try:
            row = parse_key_values(match.group(1))
        except ValueError:
            malformed.append(match.group(1))
            continue
        required = {"scenario", "job", "kind", "service", "turnaround"}
        if not required.issubset(row):
            malformed.append(match.group(1))
            continue
        row["policy"] = policy
        row["run"] = run_index
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
        row["throughput"] = 0.0
        rows.append(row)

    if not rows:
        raise RuntimeError(
            "could not parse scenario benchmark rows; "
            f"raw output tail={output[-1000:]!r}"
        )
    if malformed:
        raise RuntimeError(
            f"malformed scenario benchmark record(s): {malformed[0]!r}"
        )

    throughput = len(rows) / elapsed if elapsed else 0.0
    for row in rows:
        row["throughput"] = throughput
    return rows


def write_csv(rows, output_path):
    if output_path:
        parent = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(parent, exist_ok=True)
    stream = open(output_path, "w", newline="") if output_path else sys.stdout
    try:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if output_path:
            stream.close()


def print_summary(rows, label):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["policy"], row["scenario"], row["kind"])].append(row)

    print(f"\n[{label}] summary", file=sys.stderr)
    print(
        "policy,scenario,kind,count,avg_turnaround,"
        "avg_weighted_turnaround,avg_response,avg_kernel_response,"
        "avg_run_ticks,avg_schedule_count,avg_total_ready_time,throughput",
        file=sys.stderr,
    )
    for (policy, scenario, kind), group in groups.items():
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
            f"{policy},{scenario},{kind},{count},{avg_turnaround:.2f},"
            f"{avg_weighted:.2f},{avg_response:.2f},"
            f"{avg_kernel_response:.2f},{avg_run_ticks:.2f},"
            f"{avg_schedule_count:.2f},{avg_total_ready_time:.2f},"
            f"{throughput:.4f}",
            file=sys.stderr,
        )

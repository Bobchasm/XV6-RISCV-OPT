#!/usr/bin/env python3
"""Run scenario-based scheduler workloads and emit CSV results."""

import argparse
import os
import sys

from xv6_runner import END_RE, POLICY_TARGETS, cleanup_intermediate_artifacts
from xv6_runner import ensure_policy_image
from xv6_runner import parse_output, print_summary, run_qemu, write_csv


SUPPORTED_SCENARIOS = {"compute", "io", "mixed"}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policies",
        default="SCHED_RR",
        help="comma-separated build-time policies",
    )
    parser.add_argument(
        "--scenarios",
        default="compute,io,mixed",
        help="comma-separated scenarios: compute,io,mixed",
    )
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--work", type=int, default=20)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--compute-priority", type=int, default=1)
    parser.add_argument("--io-priority", type=int, default=9)
    parser.add_argument("--interactive-priority", type=int, default=12)
    parser.add_argument(
        "--output",
        nargs="?",
        const="",
        help=(
            "write CSV here; if no path is given, write to "
            "results/schedscene-<algorithms>.csv"
        ),
    )
    args = parser.parse_args()
    if args.output == "":
        names = [
            POLICY_TARGETS.get(policy.strip(), policy.strip().lower())
            for policy in args.policies.split(",")
            if policy.strip()
        ]
        args.output = os.path.join(
            REPO_ROOT, "results", f"schedscene-{'-'.join(names)}.csv"
        )

    repo = REPO_ROOT
    policies = [item.strip() for item in args.policies.split(",") if item.strip()]
    scenarios = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    unsupported = sorted(set(scenarios) - SUPPORTED_SCENARIOS)
    if unsupported:
        parser.error(
            "unsupported scenarios: " + ", ".join(unsupported)
        )

    rows = []
    for policy in policies:
        image = ensure_policy_image(repo, policy)
        for scenario in scenarios:
            for run_index in range(args.repeat):
                print(
                    f"[schedscene] running {policy} {scenario} "
                    f"repeat {run_index + 1}/{args.repeat}",
                    file=sys.stderr,
                )
                command = (
                    f"schedscene {scenario} {args.jobs} {args.work} "
                    f"{args.compute_priority} {args.io_priority} "
                    f"{args.interactive_priority}"
                )
                try:
                    output = run_qemu(
                        repo,
                        command,
                        END_RE,
                        args.timeout,
                        "schedscene",
                        image["kernel"],
                        image["fs_image"],
                    )
                    rows.extend(parse_output(output, policy, run_index))
                finally:
                    cleanup_intermediate_artifacts(repo)

    write_csv(rows, args.output)
    print_summary(rows, "schedscene")


if __name__ == "__main__":
    main()

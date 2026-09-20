#!/usr/bin/env python3
"""Plot scheduler benchmark and scenario CSV files.

Run from the repository root:
    python3 analysis/plot_scheduler_results.py
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PLOTS = ROOT / "analysis" / "plots"

POLICIES = ["SCHED_RR", "SCHED_STATIC_PRIORITY", "SCHED_MLFQ"]
LABELS = {
    "SCHED_RR": "RR",
    "SCHED_STATIC_PRIORITY": "SPQ",
    "SCHED_MLFQ": "MLFQ",
}
COLORS = {
    "SCHED_RR": "#2563eb",
    "SCHED_STATIC_PRIORITY": "#dc2626",
    "SCHED_MLFQ": "#059669",
}

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 220,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
        "legend.frameon": False,
    }
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def mean(rows: list[dict[str, str]], field: str) -> float:
    values = [float(row[field]) for row in rows]
    return sum(values) / len(values) if values else math.nan


def population_std(rows: list[dict[str, str]], field: str) -> float:
    values = [float(row[field]) for row in rows]
    if not values:
        return math.nan
    average = sum(values) / len(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def grouped(rows: list[dict[str, str]], *fields: str):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(field, "") for field in fields)].append(row)
    return groups


def save(fig, name: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(PLOTS / f"{name}.png", bbox_inches="tight")
    fig.savefig(PLOTS / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def metric_title(field: str) -> str:
    return {
        "turnaround": "Mean Turnaround (ticks)",
        "response": "Mean Response (ticks)",
        "kernel_response": "Mean Kernel Response (ticks)",
        "run_ticks": "Mean Run Ticks",
        "cpu_share": "Mean CPU Share",
        "throughput": "Mean Throughput (jobs/tick)",
    }[field]


def work_scaling() -> None:
    files = {
        10: RESULTS / "schedbench-rr-spq-mlfq-work10.csv",
        40: RESULTS / "schedbench-rr-spq-mlfq-work40.csv",
        80: RESULTS / "schedbench-rr-spq-mlfq-work80.csv",
    }
    data = {work: read_rows(path) for work, path in files.items()}

    for field, name in [
        ("turnaround", "work_scaling_turnaround"),
        ("response", "work_scaling_response"),
        ("run_ticks", "work_scaling_run_ticks"),
        ("cpu_share", "work_scaling_cpu_share"),
    ]:
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        for policy in POLICIES:
            values = [
                mean(
                    [
                        row
                        for row in data[work]
                        if row["policy"] == policy
                    ],
                    field,
                )
                for work in files
            ]
            ax.plot(
                list(files),
                values,
                marker="o",
                linewidth=2,
                label=LABELS[policy],
                color=COLORS[policy],
            )
        ax.set_title(f"Scheduler Comparison Across Workload Size: {metric_title(field)}")
        ax.set_xlabel("Work parameter")
        ax.set_ylabel(metric_title(field))
        ax.set_xticks(list(files))
        ax.legend()
        save(fig, name)


def scenario_comparison() -> None:
    rows = read_rows(RESULTS / "schedscene-rr-spq-mlfq-repeat3.csv")
    scenarios = ["compute-heavy", "io-heavy", "mixed-interactive"]
    scenario_labels = {
        "compute-heavy": "Compute",
        "io-heavy": "I/O",
        "mixed-interactive": "Mixed",
    }

    for field, name in [
        ("turnaround", "scenario_turnaround"),
        ("response", "scenario_response"),
        ("kernel_response", "scenario_kernel_response"),
        ("run_ticks", "scenario_run_ticks"),
    ]:
        fig, ax = plt.subplots(figsize=(8.2, 4.5))
        width = 0.24
        positions = list(range(len(scenarios)))
        for index, policy in enumerate(POLICIES):
            values = []
            for scenario in scenarios:
                subset = [
                    row
                    for row in rows
                    if row["policy"] == policy and row["scenario"] == scenario
                ]
                values.append(mean(subset, field))
            offsets = [
                position + (index - 1) * width for position in positions
            ]
            ax.bar(
                offsets,
                values,
                width=width,
                label=LABELS[policy],
                color=COLORS[policy],
            )
        ax.set_title(f"Scenario Comparison: {metric_title(field)}")
        ax.set_xlabel("Workload scenario")
        ax.set_ylabel(metric_title(field))
        ax.set_xticks(positions)
        ax.set_xticklabels([scenario_labels[item] for item in scenarios])
        ax.legend()
        save(fig, name)


def repeat_variability() -> None:
    rows = read_rows(RESULTS / "schedbench-rr-spq-mlfq-work40.csv")
    groups = grouped(rows, "policy", "kind")
    kinds = ["cpu", "io", "mixed"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharex=True)
    for axis, field in zip(axes, ["turnaround", "response"]):
        width = 0.24
        positions = list(range(len(kinds)))
        for index, policy in enumerate(POLICIES):
            values = []
            errors = []
            for kind in kinds:
                subset = groups[(policy, kind)]
                values.append(mean(subset, field))
                errors.append(population_std(subset, field))
            offsets = [
                position + (index - 1) * width for position in positions
            ]
            axis.bar(
                offsets,
                values,
                width=width,
                yerr=errors,
                capsize=3,
                label=LABELS[policy],
                color=COLORS[policy],
            )
        axis.set_title(f"{metric_title(field)} with Population Std. Dev.")
        axis.set_xticks(positions)
        axis.set_xticklabels(["CPU", "I/O", "Mixed"])
        axis.set_ylabel("ticks")
    axes[0].legend()
    save(fig, "work40_variability")


def main() -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    work_scaling()
    scenario_comparison()
    repeat_variability()
    print(f"generated plots in {PLOTS}")


if __name__ == "__main__":
    main()

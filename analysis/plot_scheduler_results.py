#!/usr/bin/env python3
"""Create presentation-ready plots from the scheduler CSV matrix."""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


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
KINDS = ["cpu", "io", "mixed"]
KIND_LABELS = {"cpu": "CPU", "io": "I/O", "mixed": "Mixed"}

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 240,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.alpha": 0.22,
        "grid.linestyle": "--",
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def mean(rows: list[dict[str, str]], field: str) -> float:
    values = [float(row[field]) for row in rows]
    return sum(values) / len(values) if values else math.nan


def std(rows: list[dict[str, str]], field: str) -> float:
    values = [float(row[field]) for row in rows]
    if not values:
        return math.nan
    average = sum(values) / len(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def save(fig, name: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(PLOTS / f"{name}.png", bbox_inches="tight")
    fig.savefig(PLOTS / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def subset(rows, policy=None, kind=None):
    return [
        row
        for row in rows
        if (policy is None or row["policy"] == policy)
        and (kind is None or row["kind"] == kind)
    ]


def metric_title(field: str) -> str:
    return {
        "turnaround": "Turnaround (ticks)",
        "response": "Response (ticks)",
        "kernel_response": "Kernel response (ticks)",
        "run_ticks": "Run ticks",
        "total_ready_time": "Ready wait (ticks)",
    }[field]


def scale_files(prefix: str) -> dict[int, Path]:
    pattern = re.compile(rf"schedbench-rr-spq-mlfq-{prefix}(\d+)\.csv$")
    files = {}
    for path in RESULTS.glob(f"schedbench-rr-spq-mlfq-{prefix}*.csv"):
        match = pattern.match(path.name)
        if match:
            files[int(match.group(1))] = path
    if not files:
        raise FileNotFoundError(f"no {prefix} scale CSV files in {RESULTS}")
    return dict(sorted(files.items()))


def load_scale(prefix: str) -> dict[int, list[dict[str, str]]]:
    return {scale: read_rows(path) for scale, path in scale_files(prefix).items()}


def work_scaling() -> None:
    data = load_scale("work")
    works = list(data)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), sharey=False)
    for axis, kind in zip(axes, KINDS):
        for policy in POLICIES:
            values = [
                mean(subset(data[work], policy, kind), "turnaround")
                for work in works
            ]
            axis.plot(
                works,
                values,
                marker="o",
                markersize=4,
                linewidth=2.2,
                label=LABELS[policy],
                color=COLORS[policy],
            )
        axis.set_title(f"{KIND_LABELS[kind]} workload")
        axis.set_xlabel("Work parameter")
        axis.set_ylabel("Mean turnaround (ticks)")
        axis.set_xticks(works)
        axis.tick_params(axis="x", rotation=35)
    axes[0].legend()
    fig.suptitle("Turnaround Scaling by Task Type", y=1.02, fontsize=14)
    save(fig, "multiscale_turnaround_by_kind")

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), sharex=True)
    for axis, field in zip(
        axes.flat,
        ["turnaround", "response", "run_ticks", "total_ready_time"],
    ):
        for policy in POLICIES:
            averages = []
            deviations = []
            for work in works:
                rows = subset(data[work], policy)
                averages.append(mean(rows, field))
                deviations.append(std(rows, field))
            lower = [
                max(0, value - error)
                for value, error in zip(averages, deviations)
            ]
            upper = [value + error for value, error in zip(averages, deviations)]
            axis.plot(
                works,
                averages,
                marker="o",
                markersize=3.5,
                linewidth=2,
                label=LABELS[policy],
                color=COLORS[policy],
            )
            axis.fill_between(
                works, lower, upper, color=COLORS[policy], alpha=0.10
            )
        axis.set_title(metric_title(field))
        axis.set_xticks(works)
        axis.tick_params(axis="x", rotation=35)
        axis.set_xlabel("Work parameter")
    axes[0, 0].set_ylabel("Mean")
    axes[1, 0].set_ylabel("Mean")
    axes[0, 0].legend()
    fig.suptitle(
        "Multi-scale Scheduler Profile (mean +/- population std. dev.)",
        y=1.01,
    )
    save(fig, "multiscale_profile")


def heatmap(
    matrix: list[list[float]],
    x_labels: list[str],
    y_labels: list[str],
    title: str,
    name: str,
) -> None:
    fig, axis = plt.subplots(figsize=(7.2, 4.8))
    cmap = LinearSegmentedColormap.from_list(
        "scheduler", ["#eff6ff", "#1d4ed8"]
    )
    image = axis.imshow(matrix, cmap=cmap, aspect="auto")
    axis.set_xticks(range(len(x_labels)), x_labels)
    axis.set_yticks(range(len(y_labels)), y_labels)
    axis.set_xlabel("Scheduler policy")
    axis.set_ylabel("Scale")
    axis.set_title(title)
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            axis.text(x, y, f"{value:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(image, ax=axis, label="Mean turnaround (ticks)")
    save(fig, name)


def scale_heatmaps() -> None:
    work_data = load_scale("work")
    works = list(work_data)
    for kind in KINDS:
        matrix = [
            [
                mean(subset(work_data[work], policy, kind), "turnaround")
                for policy in POLICIES
            ]
            for work in works
        ]
        heatmap(
            matrix,
            [LABELS[policy] for policy in POLICIES],
            [str(work) for work in works],
            f"Turnaround Heatmap: {KIND_LABELS[kind]} Tasks",
            f"heatmap_work_{kind}",
        )

    job_data = load_scale("jobs")
    jobs = list(job_data)
    matrix = [
        [
            mean(subset(job_data[job], policy), "turnaround")
            for policy in POLICIES
        ]
        for job in jobs
    ]
    heatmap(
        matrix,
        [LABELS[policy] for policy in POLICIES],
        [str(job) for job in jobs],
        "Turnaround Heatmap Across Concurrent Job Counts",
        "heatmap_jobs_all_tasks",
    )


def jobs_scaling() -> None:
    data = load_scale("jobs")
    jobs = list(data)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), sharex=True)
    for axis, kind in zip(axes, KINDS):
        for policy in POLICIES:
            values = [
                mean(subset(data[job], policy, kind), "turnaround")
                for job in jobs
            ]
            axis.plot(
                jobs,
                values,
                marker="o",
                linewidth=2.2,
                label=LABELS[policy],
                color=COLORS[policy],
            )
        axis.set_title(f"{KIND_LABELS[kind]} tasks")
        axis.set_xlabel("Concurrent jobs")
        axis.set_ylabel("Mean turnaround (ticks)")
        axis.set_xticks(jobs)
    axes[0].legend()
    fig.suptitle("Concurrency Scaling by Task Type", y=1.02, fontsize=14)
    save(fig, "job_scaling_by_kind")


def distribution_and_correlation() -> None:
    data = load_scale("work")
    rows = [row for scale in data.values() for row in scale]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6))
    for axis, kind in zip(axes, KINDS):
        values = [
            [float(row["turnaround"]) for row in subset(rows, policy, kind)]
            for policy in POLICIES
        ]
        plot = axis.boxplot(
            values,
            tick_labels=[LABELS[p] for p in POLICIES],
            patch_artist=True,
        )
        for patch, policy in zip(plot["boxes"], POLICIES):
            patch.set_facecolor(COLORS[policy])
            patch.set_alpha(0.70)
        axis.set_title(f"{KIND_LABELS[kind]} tasks")
        axis.set_ylabel("Turnaround (ticks)")
        axis.grid(axis="y", alpha=0.22)
    fig.suptitle(
        "Turnaround Distribution Across All Work Scales",
        y=1.02,
        fontsize=14,
    )
    save(fig, "turnaround_distribution_by_kind")

    markers = {"cpu": "o", "io": "s", "mixed": "^"}
    fig, axis = plt.subplots(figsize=(7.8, 5.2))
    for policy in POLICIES:
        for kind in KINDS:
            selected = subset(rows, policy, kind)
            axis.scatter(
                [float(row["response"]) for row in selected],
                [float(row["turnaround"]) for row in selected],
                s=[35 + 20 * float(row["run_ticks"]) for row in selected],
                alpha=0.55,
                color=COLORS[policy],
                marker=markers[kind],
                label=f"{LABELS[policy]} / {KIND_LABELS[kind]}",
            )
    axis.set_xlabel("Response (ticks)")
    axis.set_ylabel("Turnaround (ticks)")
    axis.set_title("Response vs. Turnaround; marker size follows run ticks")
    axis.legend(ncol=2, fontsize=8)
    save(fig, "response_turnaround_correlation")


def scenario_comparison() -> None:
    rows = read_rows(RESULTS / "schedscene-rr-spq-mlfq-repeat3.csv")
    scenarios = ["compute-heavy", "io-heavy", "mixed-interactive"]
    labels = {
        "compute-heavy": "Compute",
        "io-heavy": "I/O",
        "mixed-interactive": "Mixed",
    }
    for field, name in [
        ("turnaround", "scenario_turnaround"),
        ("response", "scenario_response"),
        ("kernel_response", "scenario_kernel_response"),
    ]:
        fig, axis = plt.subplots(figsize=(8.5, 4.8))
        width = 0.24
        positions = list(range(len(scenarios)))
        for index, policy in enumerate(POLICIES):
            values = [
                mean(
                    [
                        row
                        for row in rows
                        if row["policy"] == policy
                        and row["scenario"] == scenario
                    ],
                    field,
                )
                for scenario in scenarios
            ]
            axis.bar(
                [position + (index - 1) * width for position in positions],
                values,
                width=width,
                label=LABELS[policy],
                color=COLORS[policy],
            )
        axis.set_title(f"Scenario Comparison: {metric_title(field)}")
        axis.set_xlabel("Workload scenario")
        axis.set_ylabel(metric_title(field))
        axis.set_xticks(positions, [labels[item] for item in scenarios])
        axis.legend()
        save(fig, name)


def main() -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    work_scaling()
    scale_heatmaps()
    jobs_scaling()
    distribution_and_correlation()
    scenario_comparison()
    print(f"generated plots in {PLOTS}")


if __name__ == "__main__":
    main()

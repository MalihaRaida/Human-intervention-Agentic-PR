#!/usr/bin/env python3
"""Create RQ2 merged-PR boxplots for human and agent file/line changes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FILE_METRICS = ["modified_files", "added_files", "removed_files"]
LINE_METRICS = ["changed_lines", "added_lines", "removed_lines"]
ACTORS = ["human", "agent"]


def to_actor_metrics(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    if "commit_author_type" in df.columns:
        if "changed_lines" in metrics and "changed_lines" not in df.columns:
            df = df.rename(columns={"modified_lines": "changed_lines"})
        needed = ["commit_author_type", *metrics]
        missing = [column for column in needed if column not in df.columns]
        if missing:
            raise KeyError(f"Missing columns: {missing}")
        result = df[["commit_author_type", *metrics]].copy()
        result["actor"] = result.pop("commit_author_type").astype(str).str.strip().str.title()
        return result[result["actor"].isin(["Human", "Agent"])].copy()

    records = []
    for actor in ACTORS:
        actor_columns = [f"{actor}_{metric}" for metric in metrics]
        missing = [column for column in actor_columns if column not in df.columns]
        if missing:
            raise KeyError(f"Missing columns: {missing}")

        actor_data = df[["pr_id", *actor_columns]].copy()
        actor_data.columns = ["pr_id", *metrics]
        actor_data["actor"] = actor.title()
        records.append(actor_data)
    return pd.concat(records, ignore_index=True)


def plot_metric(df: pd.DataFrame, metric: str, level: str, output_dir: Path) -> None:
    groups = [
        pd.to_numeric(df.loc[df["actor"] == actor, metric], errors="coerce").dropna()
        for actor in ["Human", "Agent"]
    ]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.boxplot(groups, tick_labels=["Human", "Agent"], showfliers=False)
    label = metric.replace("_", " ").title()
    ax.set_title(f"Merged PRs ({level.replace('_', ' ').title()}): {label}")
    ax.set_ylabel(label)
    fig.tight_layout()
    fig.savefig(output_dir / f"merged_{level}_{metric}_boxplot.png", dpi=300)
    plt.close(fig)


def plot_file_changes(df: pd.DataFrame, level: str, output_dir: Path) -> None:
    groups = []
    positions = []
    labels = []
    for index, metric in enumerate(FILE_METRICS):
        center = index * 3
        for offset, actor in enumerate(["Human", "Agent"]):
            values = pd.to_numeric(
                df.loc[df["actor"] == actor, metric], errors="coerce"
            ).dropna()
            groups.append(values)
            positions.append(center + offset)
        labels.append(metric.replace("_files", "").title())

    fig, ax = plt.subplots(figsize=(9, 5))
    boxes = ax.boxplot(groups, positions=positions, widths=0.7, showfliers=False, patch_artist=True)
    for box, color in zip(boxes["boxes"],  [ "#F58518","#4C78A8"]  * len(FILE_METRICS)):
        box.set_facecolor(color)
    ax.set_xticks([index * 3 + 0.5 for index in range(len(FILE_METRICS))], labels)
    ax.set_title(f"Merged PRs ({level.replace('_', ' ').title()}): File Changes")
    ax.set_ylabel("Number of Files")
    ax.legend(
        [boxes["boxes"][0], boxes["boxes"][1]], ["Human", "Agent"], loc="upper right"
    )
    fig.tight_layout()
    fig.savefig(output_dir / f"merged_{level}_file_changes_boxplot.png", dpi=300)
    plt.close(fig)


def plot_line_changes(df: pd.DataFrame, level: str, output_dir: Path) -> None:
    groups = []
    positions = []
    labels = []
    for index, metric in enumerate(LINE_METRICS):
        center = index * 3
        for offset, actor in enumerate(["Human", "Agent"]):
            values = pd.to_numeric(
                df.loc[df["actor"] == actor, metric], errors="coerce"
            ).dropna()
            groups.append(values)
            positions.append(center + offset)
        label = "Modified" if metric == "changed_lines" else metric.replace("_lines", "").title()
        labels.append(label)

    fig, ax = plt.subplots(figsize=(9, 5))
    boxes = ax.boxplot(groups, positions=positions, widths=0.7, showfliers=False, patch_artist=True)
    for box, color in zip(boxes["boxes"], [ "#F58518","#4C78A8"] * len(LINE_METRICS)):
        box.set_facecolor(color)
    ax.set_xticks([index * 3 + 0.5 for index in range(len(LINE_METRICS))], labels)
    ax.set_title(f"Merged PRs ({level.replace('_', ' ').title()}): Line Changes")
    ax.set_ylabel("Number of Lines")
    ax.legend(
        [boxes["boxes"][0], boxes["boxes"][1]], ["Human", "Agent"], loc="upper right"
    )
    fig.tight_layout()
    fig.savefig(output_dir / f"merged_{level}_line_changes_boxplot.png", dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file-changes",
        default="results/rq2/merged_pr_level_file_changes.csv",
        help="Merged PR-level or commit-level file changes CSV.",
    )
    parser.add_argument(
        "--line-changes",
        default="results/rq2/merged_pr_level_line_changes.csv",
        help="Merged PR-level or commit-level line changes CSV.",
    )
    parser.add_argument("--output-dir", default="figures/rq2")
    args = parser.parse_args()

    file_source = pd.read_csv(args.file_changes)
    line_source = pd.read_csv(args.line_changes)
    level = "commit_level" if "commit_author_type" in file_source.columns else "pr_level"
    if ("commit_author_type" in line_source.columns) != (level == "commit_level"):
        raise ValueError("File and line change inputs must use the same aggregation level.")
    file_data = to_actor_metrics(file_source, FILE_METRICS)
    line_data = to_actor_metrics(line_source, LINE_METRICS)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_file_changes(file_data, level, output_dir)
    plot_line_changes(line_data, level, output_dir)

    print(f"Saved 2 merged {level.replace('_', '-')} boxplots to {output_dir}")


if __name__ == "__main__":
    main()

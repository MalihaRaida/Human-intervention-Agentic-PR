#!/usr/bin/env python3
"""Create RQ2 boxplots for closed and open human-intervened PRs."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FILE_METRICS = ["modified_files", "added_files", "removed_files"]
LINE_METRICS = ["added_lines", "removed_lines", "changed_lines"]
OUTCOMES = ["closed", "open"]
ACTORS = ["Human", "Agent"]
COLORS = {"Human": "#F58518", "Agent": "#4C78A8"}


def load_actor_metrics(
    changes_path: str, mapping_path: str, metrics: list[str]
) -> pd.DataFrame:
    changes = pd.read_csv(changes_path)
    mapping = pd.read_csv(mapping_path, low_memory=False)
    required_mapping = {"pr_id", "state", "pr_commit_type"}
    missing_mapping = required_mapping - set(mapping.columns)
    if missing_mapping:
        raise KeyError(f"Mapping file is missing columns: {sorted(missing_mapping)}")

    state_by_pr = mapping.loc[
        mapping["pr_commit_type"] == "human-intervened", ["pr_id", "state"]
    ].drop_duplicates(subset=["pr_id"])
    records = []
    for actor in ACTORS:
        prefix = actor.lower()
        actor_columns = [f"{prefix}_{metric}" for metric in metrics]
        missing = [column for column in actor_columns if column not in changes.columns]
        if missing:
            raise KeyError(f"Changes file is missing columns: {missing}")

        actor_data = changes[["pr_id", *actor_columns]].copy()
        actor_data.columns = ["pr_id", *metrics]
        actor_data["actor"] = actor
        records.append(actor_data)

    data = pd.concat(records, ignore_index=True).merge(state_by_pr, on="pr_id", how="left")
    data["state"] = data["state"].astype(str).str.strip().str.lower()
    return data[data["state"].isin(OUTCOMES)].copy()


def plot_changes(df: pd.DataFrame, metrics: list[str], unit: str, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)

    for ax, outcome in zip(axes, OUTCOMES):
        groups = []
        positions = []
        labels = []
        for index, metric in enumerate(metrics):
            for offset, actor in enumerate(ACTORS):
                values = pd.to_numeric(
                    df.loc[(df["state"] == outcome) & (df["actor"] == actor), metric],
                    errors="coerce",
                ).dropna()
                groups.append(values)
                positions.append(index * 3 + offset)
            labels.append(metric.replace(f"_{unit.lower()}", "").title())

        boxes = ax.boxplot(
            groups, positions=positions, widths=0.7, showfliers=False, patch_artist=True
        )
        for box, actor in zip(boxes["boxes"], ACTORS * len(metrics)):
            box.set_facecolor(COLORS[actor])
        ax.set_xticks([index * 3 + 0.5 for index in range(len(metrics))], labels)
        ax.set_title(f"{outcome.title()} PRs")
        ax.set_ylabel(f"Number of {unit}" if outcome == "closed" else "")
        ax.legend([boxes["boxes"][0], boxes["boxes"][1]], ACTORS, loc="upper right")

    fig.suptitle(f"Human-Intervened Unmerged PRs: {unit} Changes")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file-changes",
        default="results/rq2/unmerged_pr_level_file_changes.csv",
    )
    parser.add_argument(
        "--line-changes",
        default="results/rq2/unmerged_pr_level_line_changes.csv",
    )
    parser.add_argument(
        "--mapping",
        default="data/processed/unmerged_pr_commit_mapping.csv",
        help="PR mapping CSV that supplies each PR's closed or open state.",
    )
    parser.add_argument("--output-dir", default="figures/rq2")
    args = parser.parse_args()

    file_data = load_actor_metrics(args.file_changes, args.mapping, FILE_METRICS)
    line_data = load_actor_metrics(args.line_changes, args.mapping, LINE_METRICS)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_changes(file_data, FILE_METRICS, "Files", output_dir / "unmerged_file_changes_boxplot.png")
    plot_changes(line_data, LINE_METRICS, "Lines", output_dir / "unmerged_line_changes_boxplot.png")

    print(f"Saved closed/open file and line boxplots to {output_dir}")


if __name__ == "__main__":
    main()

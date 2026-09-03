#!/usr/bin/env python3
"""
RQ2: PR-level file and line changes using a preprocessed commit CSV with authorship.

Expected input columns
----------------------
[
    "sha", "pr_id", "author", "committer", "message",
    "commit_stats_total", "commit_stats_additions", "commit_stats_deletions",
    "filename", "status", "additions", "deletions", "changes", "patch",
    "commit_author_type",
]

Outputs
-------
- pr_level_file_changes.csv
- pr_level_line_changes.csv
- agent_file_human_refinement.csv
- agent_file_human_refinement_overall.csv

Example
-------
python rq2_pr_level_changes.py \
    merged_pr_commits_with_authorship.csv \
    --output-dir results/rq2/merged
"""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "sha", "pr_id", "author", "committer", "message",
    "commit_stats_total", "commit_stats_additions", "commit_stats_deletions",
    "filename", "status", "additions", "deletions", "changes", "patch",
    "commit_author_type",
]


def validate_schema(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "Input CSV does not match the expected schema. "
            f"Missing columns: {missing}"
        )


def normalize_status(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip().lower()
    mapping = {
        "add": "added",
        "added": "added",
        "new": "added",
        "modify": "modified",
        "modified": "modified",
        "changed": "modified",
        "delete": "removed",
        "deleted": "removed",
        "removed": "removed",
    }
    return mapping.get(s, s)


def normalize_actor(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def filter_human_involved_prs(df: pd.DataFrame) -> pd.DataFrame:
    actors = df["commit_author_type"].map(normalize_actor)
    has_human = actors.eq("human").groupby(df["pr_id"]).any()
    human_involved_pr_ids = has_human.index[has_human]
    return df[df["pr_id"].isin(human_involved_pr_ids)].copy()


def compute_pr_level_file_changes(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["_actor"] = work["commit_author_type"].map(normalize_actor)
    work["_status"] = work["status"].map(normalize_status)

    counts = (
        work.groupby(["pr_id", "_actor", "_status"])["filename"]
        .nunique()
        .rename("file_count")
        .reset_index()
    )

    pivot = counts.pivot_table(
        index="pr_id",
        columns=["_actor", "_status"],
        values="file_count",
        fill_value=0,
    )

    if len(pivot.columns):
        pivot.columns = [
            f"{actor}_{status}_files"
            for actor, status in pivot.columns
        ]

    pivot = pivot.reset_index()

    expected = [
        "human_added_files",
        "human_modified_files",
        "human_removed_files",
        "agent_added_files",
        "agent_modified_files",
        "agent_removed_files",
    ]
    for col in expected:
        if col not in pivot.columns:
            pivot[col] = 0

    return pivot[
        [
            "pr_id",
            "human_modified_files",
            "human_added_files",
            "human_removed_files",
            "agent_modified_files",
            "agent_added_files",
            "agent_removed_files",
        ]
    ]


def compute_pr_level_line_changes(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["_actor"] = work["commit_author_type"].map(normalize_actor)

    for col in ["additions", "deletions", "changes"]:
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0)

    grouped = (
        work.groupby(["pr_id", "_actor"], as_index=False)
        .agg(
            added_lines=("additions", "sum"),
            removed_lines=("deletions", "sum"),
            changed_lines=("changes", "sum"),
        )
    )

    rows = []
    for pr_id, group in grouped.groupby("pr_id"):
        row = {
            "pr_id": pr_id,
            "human_added_lines": 0,
            "human_removed_lines": 0,
            "human_changed_lines": 0,
            "agent_added_lines": 0,
            "agent_removed_lines": 0,
            "agent_changed_lines": 0,
        }

        for _, rec in group.iterrows():
            actor = rec["_actor"]
            if actor not in {"human", "agent"}:
                continue
            row[f"{actor}_added_lines"] = rec["added_lines"]
            row[f"{actor}_removed_lines"] = rec["removed_lines"]
            row[f"{actor}_changed_lines"] = rec["changed_lines"]

        rows.append(row)

    return pd.DataFrame(rows)



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        help="Path to merged_pr_commits_with_authorship.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to results/rq2/<input-stem>.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input, low_memory=False)
    validate_schema(df)

    normalized_actor = (
        df["commit_author_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    unknown = sorted(set(normalized_actor.unique()) - {"human", "agent"})
    if unknown:
        raise ValueError(
            "Unexpected values in commit_author_type: "
            f"{unknown}. Expected only Human and Agent."
        )

    output_dir = Path(args.output_dir) if args.output_dir else Path("results/rq2")
    output_dir.mkdir(parents=True, exist_ok=True)
    outcome = "unmerged" if "unmerged" in Path(args.input).stem.lower() else "merged"

    human_involved_df = filter_human_involved_prs(df)
    file_changes = compute_pr_level_file_changes(human_involved_df)
    line_changes = compute_pr_level_line_changes(human_involved_df)

    file_path = output_dir / f"{outcome}_pr_level_file_changes.csv"
    line_path = output_dir / f"{outcome}_pr_level_line_changes.csv"


    file_changes.to_csv(file_path, index=False)
    line_changes.to_csv(line_path, index=False)

    print("\nSaved:")
    print(f"  {file_path}")
    print(f"  {line_path}")


if __name__ == "__main__":
    main()
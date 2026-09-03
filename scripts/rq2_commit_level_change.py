"""
RQ2: Commit-level file and line changes by humans and agents.

Expected input: one row per changed file in a commit.

Outputs one row per commit with:
- number of added / modified / removed files
- lines added / removed
- PR, state, and actor

"""

import argparse
from pathlib import Path
import pandas as pd



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


def filter_prs_with_human_commits(df: pd.DataFrame, actor_col: str) -> pd.DataFrame:
    actors = df[actor_col].astype(str).str.strip().str.lower()
    human_pr_ids = df.loc[actors == "human", "pr_id"].unique()
    return df[df["pr_id"].isin(human_pr_ids)].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--pr-col", default="pr_id")
    parser.add_argument("--commit-col", default="sha")
    parser.add_argument("--actor-col", default="commit_author_type")
    parser.add_argument("--file-col", default="filename")
    parser.add_argument("--status-col", default="status")
    parser.add_argument("--additions-col", default="additions")
    parser.add_argument("--deletions-col", default="deletions")
    parser.add_argument("--modified-lines-col", default="changes")
    parser.add_argument("--output-dir", default="results/rq2_commit")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    needed = [
        args.pr_col, args.commit_col, args.actor_col,
        args.file_col, args.status_col, args.additions_col, args.deletions_col
    ]
    if args.modified_lines_col:
        needed.append(args.modified_lines_col)
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns: {missing}")

    w = filter_prs_with_human_commits(df, args.actor_col)
    w["_status"] = w[args.status_col].map(normalize_status)
    for c in [args.additions_col, args.deletions_col]:
        w[c] = pd.to_numeric(w[c], errors="coerce").fillna(0)
    if args.modified_lines_col:
        w[args.modified_lines_col] = pd.to_numeric(
            w[args.modified_lines_col], errors="coerce"
        ).fillna(0)

    key = [args.pr_col, args.commit_col, args.actor_col]

    file_counts = (
        w.groupby(key + ["_status"])[args.file_col]
        .nunique()
        .rename("count")
        .reset_index()
        .pivot_table(index=key, columns="_status", values="count", fill_value=0)
        .reset_index()
    )
    for c in ["added", "modified", "removed"]:
        if c not in file_counts.columns:
            file_counts[c] = 0
    file_counts = file_counts.rename(columns={
        "added": "added_files",
        "modified": "modified_files",
        "removed": "removed_files",
    })

    agg = {
        args.additions_col: "sum",
        args.deletions_col: "sum",
    }
    if args.modified_lines_col:
        agg[args.modified_lines_col] = "sum"

    line_counts = w.groupby(key, as_index=False).agg(agg).rename(columns={
        args.additions_col: "added_lines",
        args.deletions_col: "removed_lines",
        **({args.modified_lines_col: "modified_lines"} if args.modified_lines_col else {}),
    })

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    outcome = "unmerged" if "unmerged" in Path(args.input).stem.lower() else "merged"
    file_path = out / f"{outcome}_commit_level_file_changes.csv"
    line_path = out / f"{outcome}_commit_level_line_changes.csv"
    file_counts.to_csv(file_path, index=False)
    line_counts.to_csv(line_path, index=False)

    print(f"Included human-intervened or human-only PRs: {w[args.pr_col].nunique():,}")
    print(f"Saved {len(file_counts):,} commit-level file-change records: {file_path}")
    print(f"Saved {len(line_counts):,} commit-level line-change records: {line_path}")


if __name__ == "__main__":
    main()

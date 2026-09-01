#!/usr/bin/env python3
"""
Join PR metadata with already-labelled commit data to produce one PR-level record.

Inputs
------
prs CSV     : id, type, state, agent  (column names configurable)
commits CSV : pr_id, commit_author_type  (output of preprocess_commit_authorship.py)

Output schema
-------------
pr_id, type, state, agent, pr_commit_type

pr_commit_type values
---------------------
agent-only        : only Agent commits
human-intervened  : both Agent and Human commits
human-only        : only Human commits
no-commits        : PR has no associated commits (excluded by default)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def determine_pr_commit_type(has_agent: bool, has_human: bool) -> str:
    if has_agent and has_human:
        return "human-intervened"
    if has_agent:
        return "agent-only"
    if has_human:
        return "human-only"
    return "no-commits"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Join PR metadata with labelled commits to produce a PR-level CSV."
    )
    parser.add_argument("prs", help="PR metadata CSV")
    parser.add_argument("commits", help="Labelled commits CSV (must contain commit_author_type)")
    parser.add_argument("--output", default=None,
                        help="Output CSV path. Defaults to data/processed/<prs_stem>_commit_mapping.csv")
    parser.add_argument("--pr-id-col", default="id")
    parser.add_argument("--pr-type-col", default="type")
    parser.add_argument("--pr-state-col", default="state")
    parser.add_argument("--agent-col", default="agent")
    parser.add_argument("--commit-pr-id-col", default="pr_id")
    parser.add_argument("--commit-type-col", default="commit_author_type")
    parser.add_argument("--merged-at-col", default="merged_at",
                        help="Column used to detect merged PRs; rows with a non-null value become state='merged'")
    parser.add_argument("--keep-no-commit-prs", action="store_true")
    args = parser.parse_args()

    prs = pd.read_csv(args.prs, low_memory=False)
    commits = pd.read_csv(args.commits, low_memory=False)

    for col in [args.pr_id_col, args.pr_type_col, args.pr_state_col, args.agent_col]:
        if col not in prs.columns:
            raise ValueError(f"PR CSV is missing column: {col!r}")

    if args.merged_at_col in prs.columns:
        prs = prs.copy()
        prs[args.pr_state_col] = prs.apply(
            lambda r: "merged" if pd.notna(r[args.merged_at_col]) and str(r[args.merged_at_col]).strip() else r[args.pr_state_col],
            axis=1,
        )
    for col in [args.commit_pr_id_col, args.commit_type_col]:
        if col not in commits.columns:
            raise ValueError(f"Commits CSV is missing column: {col!r}")

    pr_meta = (
        prs[[args.pr_id_col, args.pr_type_col, args.pr_state_col, args.agent_col]]
        .drop_duplicates(subset=[args.pr_id_col])
        .copy()
    )

    dedup_cols = [args.commit_pr_id_col, "sha"] if "sha" in commits.columns else [args.commit_pr_id_col, args.commit_type_col]
    unique_commits = commits.drop_duplicates(subset=dedup_cols)

    commit_summary = (
        unique_commits.groupby(args.commit_pr_id_col)
        .agg(
            has_agent=(args.commit_type_col, lambda s: (s == "Agent").any()),
            has_human=(args.commit_type_col, lambda s: (s == "Human").any()),
        )
        .reset_index()
    )
    commit_summary["pr_commit_type"] = commit_summary.apply(
        lambda r: determine_pr_commit_type(r["has_agent"], r["has_human"]), axis=1
    )

    result = pr_meta.merge(
        commit_summary[[args.commit_pr_id_col, "pr_commit_type"]],
        left_on=args.pr_id_col,
        right_on=args.commit_pr_id_col,
        how="left",
    )
    result["pr_commit_type"] = result["pr_commit_type"].fillna("no-commits")

    if args.commit_pr_id_col != args.pr_id_col and args.commit_pr_id_col in result.columns:
        result = result.drop(columns=[args.commit_pr_id_col])

    if not args.keep_no_commit_prs:
        result = result[result["pr_commit_type"] != "no-commits"]

    result = result.rename(columns={
        args.pr_id_col: "pr_id",
        args.pr_type_col: "type",
        args.pr_state_col: "state",
        args.agent_col: "agent",
    })[["pr_id", "type", "state", "agent", "pr_commit_type"]]

    output = Path(args.output) if args.output else Path("data/processed") / f"{Path(args.prs).stem}_commit_mapping.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)

    print(f"PRs written : {len(result):,}")
    print(f"Output CSV : {output}")


if __name__ == "__main__":
    main()

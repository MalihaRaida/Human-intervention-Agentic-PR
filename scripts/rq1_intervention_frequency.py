from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

COMMIT_TYPES = ["agent-only", "human-intervened", "human-only"]


def load_mapping(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    required = {"pr_id", "state", "pr_commit_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    return df[["pr_id", "state", "agent", "pr_commit_type"]].drop_duplicates(subset=["pr_id"])


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    counts = (
        df.groupby(["state", "pr_commit_type"])["pr_id"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(columns=COMMIT_TYPES, fill_value=0)
        .reset_index()
        .rename(columns={
            "state":            "PR Outcome",
            "agent-only":       "#Agent-only PRs",
            "human-intervened": "#Human-intervened PRs",
            "human-only":       "#Human-only PRs",
        })
    )
    counts["Total PRs"] = (
        counts["#Agent-only PRs"]
        + counts["#Human-intervened PRs"]
        + counts["#Human-only PRs"]
    )
    return counts


def build_agent_summary(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby(["agent", "state"])
    total       = grp["pr_id"].nunique()
    intervened  = grp["pr_commit_type"].apply(lambda s: (s == "human-intervened").sum())
    result = pd.DataFrame({"total": total, "intervened": intervened}).reset_index()
    result["#Human-intervened PRs"] = result.apply(
        lambda r: f"{int(r.intervened)}/{int(r.total)} ({100*r.intervened/r.total:.2f}%)",
        axis=1,
    )
    return (
        result[["agent", "state", "#Human-intervened PRs"]]
        .rename(columns={"agent": "Agent", "state": "Outcome"})
        .sort_values(["Agent", "Outcome"])
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PR composition by outcome using pre-built mapping files"
    )
    parser.add_argument(
        "--merged-mapping",
        default="data/processed/merged_pr_commit_mapping.csv",
        help="merged_pr_commit_mapping.csv (cols: pr_id, type, state, agent, pr_commit_type)",
    )
    parser.add_argument(
        "--unmerged-mapping",
        default="data/processed/unmerged_pr_commit_mapping.csv",
        help="unmerged_pr_commit_mapping.csv (cols: pr_id, type, state, agent, pr_commit_type)",
    )
    parser.add_argument("--output-dir", default="results/rq1")
    args = parser.parse_args()

    merged   = load_mapping(args.merged_mapping)
    unmerged = load_mapping(args.unmerged_mapping)
    df = pd.concat([merged, unmerged], ignore_index=True)

    summary = build_summary(df)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    out_path = out / "pr_composition_by_outcome.csv"
    summary.to_csv(out_path, index=False)

    agent_summary = build_agent_summary(df)
    agent_path = out / "intervention_by_agent_and_outcome.csv"
    agent_summary.to_csv(agent_path, index=False)

    print("\n=== PR Composition by Outcome ===")
    print(summary.to_string(index=False))
    print(f"\nSaved {out_path}")
    print("\n=== Human-intervention Frequency by Agent and Outcome ===")
    print(agent_summary.to_string(index=False))
    print(f"\nSaved {agent_path}")


if __name__ == "__main__":
    main()

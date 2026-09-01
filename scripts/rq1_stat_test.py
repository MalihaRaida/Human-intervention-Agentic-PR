
from __future__ import annotations
import argparse
from itertools import combinations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def read_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    if p.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    raise ValueError("Input must be CSV or Parquet.")


def holm_adjust(pvalues):
    pvalues = np.asarray(pvalues, dtype=float)
    n = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = np.empty(n)
    running = 0.0
    for rank, idx in enumerate(order):
        candidate = (n - rank) * pvalues[idx]
        running = max(running, candidate)
        adjusted[idx] = min(running, 1.0)
    return adjusted


def cramers_v(table: np.ndarray) -> float:
    chi2, _, _, _ = chi2_contingency(table)
    n = table.sum()
    r, c = table.shape
    return float(np.sqrt(chi2 / (n * min(r - 1, c - 1)))) if n else np.nan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--merged-mapping",
        default="data/processed/merged_pr_commit_mapping.csv",
        help="merged_pr_commit_mapping.csv (cols: pr_id, state, agent, pr_commit_type)",
    )
    parser.add_argument(
        "--unmerged-mapping",
        default="data/processed/unmerged_pr_commit_mapping.csv",
        help="unmerged_pr_commit_mapping.csv (same schema)",
    )
    parser.add_argument("--output-dir", default="results/rq1")
    args = parser.parse_args()

    merged   = read_table(args.merged_mapping)
    unmerged = read_table(args.unmerged_mapping)
    df = pd.concat([merged, unmerged], ignore_index=True)

    needed = ["pr_id", "state", "agent", "pr_commit_type"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns: {missing}")

    per_pr = (
        df[needed]
        .drop_duplicates(subset=["pr_id"])
        .dropna(subset=["pr_id", "state", "agent"])
        .copy()
    )
    per_pr["_state"] = per_pr["state"].astype(str).str.strip()
    per_pr["_agent"] = per_pr["agent"].astype(str).str.strip()
    per_pr["has_human"] = per_pr["pr_commit_type"] == "human-intervened"

    human_prs = per_pr[per_pr["has_human"]]
    contingency = pd.crosstab(human_prs["_agent"], human_prs["_state"])
    chi2, p, dof, expected = chi2_contingency(contingency.values)
    omnibus = pd.DataFrame([{
        "chi_square": chi2,
        "df": dof,
        "p_value": p,
        "cramers_v": cramers_v(contingency.values),
        "n_human_intervened_prs": int(contingency.values.sum()),
    }])

    rows = []
    agents = list(contingency.index)
    for a, b in combinations(agents, 2):
        sub = contingency.loc[[a, b]]
        stat, pval, dfree, _ = chi2_contingency(sub.values)
        rows.append({
            "agent_1": a,
            "agent_2": b,
            "chi_square": stat,
            "df": dfree,
            "p_value": pval,
        })
    pairwise = pd.DataFrame(rows)
    if not pairwise.empty:
        pairwise["p_holm"] = holm_adjust(pairwise["p_value"].values)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    contingency.to_csv(out / "human_intervened_pr_outcome_contingency.csv")
    omnibus.to_csv(out / "agent_outcome_chi_square.csv", index=False)
    pairwise.to_csv(out / "agent_pairwise_chi_square_holm.csv", index=False)


    print("\nOmnibus test")
    print(omnibus.to_string(index=False))
    if not pairwise.empty:
        print("\nPairwise tests")
        print(pairwise.to_string(index=False))


if __name__ == "__main__":
    main()
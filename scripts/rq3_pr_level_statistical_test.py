from __future__ import annotations
import argparse
from pathlib import Path
import math
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact


def odds_ratio_ci(a, b, c, d, alpha=0.05):
    # Table:
    #              category present   absent
    # merged              a             b
    # closed              c             d
    aa, bb, cc, dd = map(float, [a, b, c, d])
    if min(aa, bb, cc, dd) == 0:
        aa += 0.5
        bb += 0.5
        cc += 0.5
        dd += 0.5

    or_value = (aa * dd) / (bb * cc)
    se = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    z = 1.959963984540054
    lower = math.exp(math.log(or_value) - z * se)
    upper = math.exp(math.log(or_value) + z * se)
    return or_value, lower, upper


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="data/labelled/Manual_Labelling_final.csv")
    parser.add_argument("--pr-col", default="Pr_id")
    parser.add_argument("--state-col", default="Pr_state")
    parser.add_argument("--category-col", default="Final_label")
    parser.add_argument("--merged-value", default="merged")
    parser.add_argument("--closed-value", default="closed")
    parser.add_argument("--output-dir", default="results/rq3")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    needed = [args.pr_col, args.state_col, args.category_col]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns: {missing}")

    w = df.dropna(subset=needed).copy()
    w["_state"] = w[args.state_col].astype(str).str.strip().str.lower()
    merged = args.merged_value.lower()
    closed = args.closed_value.lower()
    w = w[w["_state"].isin([merged, closed])]

    # One row per PR-category presence.
    presence = (
        w[[args.pr_col, "_state", args.category_col]]
        .drop_duplicates()
        .assign(present=1)
    )

    pr_state = w[[args.pr_col, "_state"]].drop_duplicates()
    dup_state = pr_state.groupby(args.pr_col)["_state"].nunique()
    if (dup_state > 1).any():
        bad = dup_state[dup_state > 1].index.tolist()[:10]
        raise ValueError(f"Some PR IDs occur in multiple states, e.g. {bad}")

    n_merged = pr_state.loc[pr_state["_state"] == merged, args.pr_col].nunique()
    n_closed = pr_state.loc[pr_state["_state"] == closed, args.pr_col].nunique()

    rows = []
    for category in sorted(w[args.category_col].astype(str).unique()):
        merged_present = presence[
            (presence["_state"] == merged)
            & (presence[args.category_col].astype(str) == category)
        ][args.pr_col].nunique()
        closed_present = presence[
            (presence["_state"] == closed)
            & (presence[args.category_col].astype(str) == category)
        ][args.pr_col].nunique()

        a = merged_present
        b = n_merged - merged_present
        c = closed_present
        d = n_closed - closed_present

        fisher_or, p_value = fisher_exact([[a, b], [c, d]], alternative="two-sided")
        or_ci, lower, upper = odds_ratio_ci(a, b, c, d)

        rows.append({
            "category": category,
            "merged_present": a,
            "merged_total": n_merged,
            "merged_pct": 100 * a / n_merged if n_merged else np.nan,
            "closed_present": c,
            "closed_total": n_closed,
            "closed_pct": 100 * c / n_closed if n_closed else np.nan,
            "odds_ratio": fisher_or,
            "ci95_lower": lower,
            "ci95_upper": upper,
            "p_value_fisher": p_value,
        })

    result = pd.DataFrame(rows).sort_values("odds_ratio", ascending=False)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "pr_level_category_associations.csv", index=False)

    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
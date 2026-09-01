from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--state-col", default="Pr_state")
    parser.add_argument("--category-col", default="Final_label")
    parser.add_argument("--output-dir", default="results/rq3")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    needed = [args.state_col, args.category_col]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns: {missing}")

    w = df.dropna(subset=needed).copy()
    counts = (
        w.groupby([args.state_col, args.category_col])
        .size()
        .rename("commit_count")
        .reset_index()
    )
    totals = counts.groupby(args.state_col)["commit_count"].transform("sum")
    counts["within_outcome_pct"] = 100 * counts["commit_count"] / totals
    pivot_pct = counts.pivot(
        index=args.category_col,
        columns=args.state_col,
        values="within_outcome_pct",
    ).fillna(0)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pivot_pct.to_csv(out / "commit_category_percentages.csv")

    print(counts.sort_values([args.state_col, "commit_count"], ascending=[True, False]).to_string(index=False))


if __name__ == "__main__":
    main()
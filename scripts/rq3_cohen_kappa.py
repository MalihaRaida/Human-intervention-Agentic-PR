import argparse
from pathlib import Path
import pandas as pd
from sklearn.metrics import cohen_kappa_score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--human-col", default="Labeler 1")
    parser.add_argument("--model-col", default="Labeler 2")
    parser.add_argument("--state-col", default="Pr_state")
    parser.add_argument("--output-dir", default="results/rq3")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    needed = [args.human_col, args.model_col]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns: {missing}")

    valid = df.dropna(subset=needed).copy()
    rows = [{
        "group": "overall",
        "n": len(valid),
        "cohens_kappa": cohen_kappa_score(valid[args.human_col], valid[args.model_col]),
    }]

    if args.state_col in valid.columns:
        for state, g in valid.groupby(args.state_col):
            rows.append({
                "group": str(state),
                "n": len(g),
                "cohens_kappa": cohen_kappa_score(g[args.human_col], g[args.model_col]),
            })

    result = pd.DataFrame(rows)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.to_csv(out / "cohens_kappa.csv", index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
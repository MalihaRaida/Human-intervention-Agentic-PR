#!/usr/bin/env python3
"""
Preprocess the raw commits CSV.

Expected columns
----------------
[
    'sha', 'pr_id', 'author', 'committer', 'message',
    'commit_stats_total', 'commit_stats_additions', 'commit_stats_deletions',
    'filename', 'status', 'additions', 'deletions', 'changes', 'patch'
]

The script labels each commit row as Human or Agent by checking the
`author`, `committer`, and `message` fields for known coding-agent signatures.

Agent signatures used
---------------------
Devin       : devin-ai-integration / devin-ai-integration[bot] / devin
Copilot     : copilot
Cursor      : cursoragent
Claude Code : claude

All rows that do not match one of these signatures are labeled Human.

Outputs
-------
<input>_commits_with_authorship.csv
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = [
    "sha",
    "pr_id",
    "author",
    "committer",
    "message",
    "commit_stats_total",
    "commit_stats_additions",
    "commit_stats_deletions",
    "filename",
    "status",
    "additions",
    "deletions",
    "changes",
    "patch",
]

AGENT_SIGNATURES = {
    "Devin": [
        r"devin-ai-integration\s*\[bot\]",
        r"devin-ai-integration",
    ],
    "Copilot": [
        r"copilot",
    ],
    "Cursor": [
        r"cursoragent",
    ],
    "Claude": [
        r"claude",
    ],
}


def normalize(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def validate_schema(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "Input CSV does not match the expected commit schema. "
            f"Missing columns: {missing}"
        )


def classify_commit(author, committer, message):
    """
    Return:
        commit_author_type
    """
    fields = [
        ("author", normalize(author)),
        ("committer", normalize(committer)),
        ("message", normalize(message)),
    ]

    for field_name, text in fields:
        if not text:
            continue

        for agent, patterns in AGENT_SIGNATURES.items():
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    return "Agent"

    return "Human"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert raw commit CSV rows into Human/Agent commit labels."
    )
    parser.add_argument("input", help="Path to raw commits CSV")
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Directory for processed CSV files",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input, low_memory=False)
    validate_schema(df)

    labels = df.apply(
        lambda row: classify_commit(
            row["author"],
            row["committer"],
            row["message"],
        ),
        axis=1,
    )
    labels.name = "commit_author_type"

    result = pd.concat([df, labels], axis=1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(args.input).stem
    all_path = out_dir / f"{stem}_with_authorship.csv"

    result.to_csv(all_path, index=False)


    print(f"Total rows   : {len(result):,}")
    print("\nSaved:")
    print(f"  {all_path}")


if __name__ == "__main__":
    main()

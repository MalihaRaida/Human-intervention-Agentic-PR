# Human Intervention in Agentic Pull Requests

This repository contains the data-processing and analysis workflow for studying human contributions to pull requests (PRs) created with coding agents. It classifies commit authorship as `Agent` or `Human`, derives PR-level intervention categories, and produces results for three research questions.

## Requirements

- Python 3.9 or later
- Packages listed in `requirement.txt`

Install the dependencies from the repository root:

```powershell
python -m pip install -r requirement.txt
```

## Workflow

Run commands from the repository root. The processed CSV files currently included in `data/processed/` allow the analysis scripts to run without repeating preprocessing.

### 1. Label commit authorship

For each raw commit dataset, classify rows using author, committer, and commit-message signatures. Recognized agent signatures are Devin, Copilot, Cursor, and Claude; unmatched rows are treated as human-authored.

```powershell
python scripts/preprocess_commit_authorship.py data/processed/merged_pr_commits.csv
python scripts/preprocess_commit_authorship.py data/processed/unmerged_pr_commits.csv
```

This writes `*_with_authorship.csv` files containing `commit_author_type`.

### 2. Build PR-to-commit mappings

Combine PR metadata and labeled commits to categorize each PR as `agent-only`, `human-intervened`, `human-only`, or `no-commits` (excluded by default).

```powershell
python scripts/preprocessing_prs_to_commits.py data/processed/merged_pr.csv data/processed/merged_pr_commits_with_authorship.csv --output data/processed/merged_pr_commit_mapping.csv
python scripts/preprocessing_prs_to_commits.py data/processed/unmerged_pr.csv data/processed/unmerged_pr_commits_with_authorship.csv --output data/processed/unmerged_pr_commit_mapping.csv
```

### 3. Run RQ1 analyses

```powershell
python scripts/rq1_intervention_frequency.py
python scripts/rq1_stat_test.py
```

RQ1 summarizes PR composition by outcome and tests the association between coding agent and PR outcome among human-intervened PRs.

### 4. Run RQ2 analyses

Create PR-level and commit-level change summaries for each outcome dataset:

```powershell
python scripts/rq2_pr_level_change.py data/processed/merged_pr_commits_with_authorship.csv
python scripts/rq2_pr_level_change.py data/processed/unmerged_pr_commits_with_authorship.csv
python scripts/rq2_commit_level_change.py data/processed/merged_pr_commits_with_authorship.csv
python scripts/rq2_commit_level_change.py data/processed/unmerged_pr_commits_with_authorship.csv
```

Create PR-level plots:

```powershell
python scripts/rq2_boxplot_merged.py
python scripts/rq2_boxplot_unmerged.py
```

Create commit-level plots by explicitly selecting the commit-level summaries:

```powershell
python scripts/rq2_boxplot_merged.py --file-changes results/rq2_commit/merged_commit_level_file_changes.csv --line-changes results/rq2_commit/merged_commit_level_line_changes.csv
python scripts/rq2_boxplot_unmerged.py --file-changes results/rq2_commit/unmerged_commit_level_file_changes.csv --line-changes results/rq2_commit/unmerged_commit_level_line_changes.csv
```

### 5. Run RQ3 analyses

```powershell
python scripts/rq3_cohen_kappa.py data/labelled/Manual_Labelling_final.csv
python scripts/rq3_commit_category_distribution.py data/labelled/Manual_Labelling_final.csv
python scripts/rq3_pr_level_statistical_test.py
```

RQ3 measures inter-labeler agreement, reports the distribution of final commit categories by PR outcome, and tests category presence between merged and closed PRs.

## Repository Layout

```text
.
|-- README.md
|-- requirement.txt                    Python dependencies
|-- data/
|   |-- labelled/                      Manual labels and labeler agreement inputs
|   |   |-- Labeler 1.csv              First labeler's annotations
|   |   |-- Labeler 1 (closed).csv     First labeler's closed-PR annotations
|   |   |-- Labeler 2.csv              Second labeler's annotations
|   |   |-- Labeler 2 (closed).csv     Second labeler's closed-PR annotations
|   |   `-- Manual_Labelling_final.csv Final consolidated annotations
|   `-- processed/                     PR and commit datasets used by analyses
|       |-- merged_pr.csv              Metadata for merged PRs
|       |-- unmerged_pr.csv            Metadata for unmerged PRs
|       |-- *_pr_commits.csv           Raw file-level commit records
|       |-- *_commits_with_authorship.csv
|       |                             Commit records with Human/Agent labels
|       |-- *_pr_commits_agent.csv     Agent-authored commit subset
|       |-- *_pr_commits_human.csv     Human-authored commit subset
|       `-- *_pr_commit_mapping.csv    PR-level intervention category mapping
|-- figures/
|   `-- rq2/                           RQ2 PNG boxplots by outcome and aggregation level
|-- prompt/
|   `-- Prompt_labeling.txt            Prompt used for the labeling task
|-- results/
|   |-- rq1/                           Intervention summaries and chi-square test outputs
|   |-- rq2/                           PR-level file and line change summaries
|   |-- rq2_commit/                    Commit-level file and line change summaries
|   `-- rq3/                           Agreement, category distribution, and association results
`-- scripts/
	|-- preprocess_commit_authorship.py       Adds Human/Agent authorship labels
	|-- preprocessing_prs_to_commits.py       Builds PR-level intervention mappings
	|-- rq1_intervention_frequency.py         Computes intervention-frequency summaries
	|-- rq1_stat_test.py                      Runs chi-square and Holm-adjusted pairwise tests
	|-- rq2_pr_level_change.py                Aggregates file and line changes per PR
	|-- rq2_commit_level_change.py            Aggregates file and line changes per commit
	|-- rq2_boxplot_merged.py                 Plots change distributions for merged PRs
	|-- rq2_boxplot_unmerged.py               Plots change distributions for open and closed PRs
	|-- rq3_cohen_kappa.py                    Calculates Cohen's kappa between labelers
	|-- rq3_commit_category_distribution.py   Calculates category percentages by outcome
	`-- rq3_pr_level_statistical_test.py      Runs PR-level Fisher exact tests
```
# Upcoming Release

Generate summary of PRs that are including in the upcoming release.

## Triggers

This skill is activated by the following keywords:

- `/upcoming-release`

## Details

Generate summary of PRs that are including in the upcoming release.

## Steps
1. Run the `.github/scripts/find_prs_between_commits.py` script from the repository root directory. The **first SHA** should be the older commit (current release), and the **second SHA** should be the newer commit (what's being released).
2. Summarize what is part of these PRs. Present the results in markdown format, grouped by: Added Features, Fixed Bugs, and Other. Include the PR numbers in your summary.

## Output
Present the summary of PRs in a markdown format grouped by: Added Features, Fixed Bugs, and Other.
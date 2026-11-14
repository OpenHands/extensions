# Comment Cleanup

Removes low-value prose from source comments and README files without changing code:

1. Comments that restate the adjacent code are deleted.
2. Comments that narrate past changes or removed functionality are deleted, keeping any fact that is still true.
3. Verbose comments are condensed to the sentence that carries the reason.

Docstrings, doc comments, license headers, and tool directives are never touched.

## Usage

Ask for a cleanup and name the scope, for example "clean up the comments in all Python files under `src/`". Without a scope, the skill asks which files or directories to examine rather than reading the whole repository.

After editing, `scripts/verify_comment_only.py` (run from the repository root) fails if the uncommitted diff changes anything other than comments. Python files are compared by AST, which also catches docstring edits; other languages are compared after a string-aware comment strip. README diffs are listed for manual review.

## Details

See [SKILL.md](./SKILL.md) for the rules and workflow, and [`references/patterns.md`](references/patterns.md) for per-language examples and borderline cases.

To run the cleanup weekly and open one pull request per repository, use the [`github-comment-cleanup`](../github-comment-cleanup) automation.

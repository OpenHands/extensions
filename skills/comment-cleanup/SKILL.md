---
name: comment-cleanup
description: This skill should be used when the user asks to "clean up comments", "remove superfluous comments", "remove redundant comments", "trim verbose comments", "remove changelog comments from code", "clean up the README", or "run a comment cleanup" on a set of files or directories, or when a scheduled automation hands over a list of files for comment cleanup. Removes comments that restate adjacent code, deletes comments that narrate removed functionality or past PRs, and condenses verbose comments, while leaving code and docstrings untouched.
---

# Comment Cleanup

Remove low-value prose from source files and READMEs without changing behaviour. Three
patterns are in scope; everything else is left alone. The output is a comment-only diff.

## The three patterns

Apply one test to every comment: **does it tell a reader something they cannot get from
the code within a few lines of it?** If yes, keep it (shortened if needed). If no, delete it.

### Pattern 1 - Comment restates the adjacent code

The content is inferable from the few lines above and below. Delete it.

```python
# Get the content text from the message
content_text = message.get_content_text()
```

Typical signs: the comment paraphrases the function name, the variable name, or the
branch condition; it announces the next line ("# Loop over users", "// Return result");
it labels a block whose first line already says the same thing.

### Pattern 2 - Comment narrates history or removed functionality

The comment explains a past state, a change, or a PR. That belongs in the PR description
or version control. Delete the history; keep any present-tense fact a reader still needs.

```python
# Prior to merging PR-1234 we stored rectangle coordinates as min_x, min_y, max_x, max_y
# and you could simply reference rectangle.max_y. Now we store x, y, width, and height
# and calculate the max_y on the fly.
area = rectangle.get_max_y()
```

Here nothing survives: `get_max_y()` already says it is computed. If the comment had
carried a live constraint (for example "max_y is derived, so do not cache it across
resizes"), keep only that sentence.

Typical signs: "previously", "used to", "no longer", "now we", "after PR-...", "changed
from", "was renamed", "legacy behaviour was", dates, author names.

### Pattern 3 - Comment is verbose

The comment carries a real reason but is padded with narrative, anecdotes, repetition, or
detail the reader does not need. Compress it to the shortest wording that keeps the reason.

```python
# Back when I was in elementary school, the first shape I ever remember seeing was
# red triangle. ... Here, we generalize our shape using the douglas peucker algorithm
generalized = polygon.generalize(1.0)
```

becomes

```python
# Generalize the polygon for lighter transport and rendering
generalized = polygon.generalize(1.0)
```

The replacement states a purpose. Do that only when the surrounding code or its callers
show that purpose; never invent one. Otherwise keep the original's substance in fewer
words, for example `# Simplify the outline with Douglas-Peucker`.

For per-language examples, borderline cases, and README guidance, read
`references/patterns.md` before the first edit of a session.

## What never changes

- **Code.** Not a character outside comments. No reformatting, no reindenting, no import
  sorting, no "while I am here" fixes.
- **Docstrings and doc comments.** Python docstrings, JSDoc/TSDoc and Javadoc/KDoc
  `/** ... */`, Rust `///` and `//!`, C# and Swift `///`, Doxygen blocks, Go comments
  directly above a declaration, Ruby RDoc/YARD comments above a `def`/`class`, Elixir
  `@doc`/`@moduledoc`. Tools publish these where the code is not visible.
- **Machine-read comments.** Shebangs, encoding lines, license and copyright headers,
  `# noqa`, `# type: ignore`, `# pragma`, `// eslint-disable...`, `// @ts-...`, `//go:...`,
  `// nolint`, `#region`, `# fmt: off`, `# pylint:`, `// prettier-ignore`, coverage markers.
- **Comments that explain why.** Rationale, workarounds with a linked bug, ordering or
  thread-safety constraints, security notes, units, non-obvious invariants, warnings.
- **TODO/FIXME/HACK with an owner, ticket, or concrete next step.**
- **Commented-out code.** Out of scope; leave it for a human.
- **Generated, vendored, or third-party files.**

When unsure whether a comment earns its place, keep it. A missed deletion costs little;
a deleted invariant costs a bug.

## Choosing what to examine

Examine exactly the files the request names, and nothing else.

- **The request names no scope** ("clean up the comments"): ask which files or directories
  to examine before reading anything, for example "all Python files under `src/`", "the
  files changed in this PR", or "`README.md` and `docs/`". Do not default to the whole
  repository; a full pass is expensive and rarely what was meant.
- **The request gives a scope** ("all Python files under `src/`"): expand it to a concrete
  list with `git ls-files` (for example `git ls-files 'src/*.py'`, which also matches
  nested directories) and confirm the count before starting when it exceeds about 50
  files.
- **The request gives an explicit file list** (as the scheduled automation does): examine
  exactly those files, do not ask, and do not open other files except to read a definition
  a comment refers to.

Skip generated, vendored, and minified files even when they fall inside the scope.

## Workflow

1. Read `references/patterns.md` once per session before the first edit.
2. Read each file in full. Classify every non-doc comment as keep, delete (pattern 1 or
   2), or shorten (pattern 3).
3. Edit only the comment lines. When deleting a full-line comment, also remove a blank
   line that only existed to separate it; do not otherwise touch spacing.
4. In a git repository, run `python3 <skill-dir>/scripts/verify_comment_only.py` from the
   repo root. It fails on any uncommitted change outside comments (for Python it also
   catches docstring edits). Fix or revert (`git checkout -- <path>`) every failing file
   and re-run until it exits 0.
5. Read the full diff of every README the verifier lists under `REVIEW`, and revert any
   hunk that changes a command, link, code block, or meaning.
6. Report the number of comments removed or shortened per pattern, the files left
   unchanged, and any suspicious comment deliberately kept.

## Additional resources

- **`references/patterns.md`** - Detailed examples per language, borderline cases, and
  README rules. Read before editing.
- **`scripts/verify_comment_only.py`** - Proves an uncommitted diff only touches comments.
- **`scripts/comment_syntax.py`** - Comment syntax table used by the verifier. Extend it
  to support a new language.

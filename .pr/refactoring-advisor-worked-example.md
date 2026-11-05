# Worked example: `refactoring-advisor` applied to this repository

This file exists to answer the worked-example blocker raised in review
([2026-08-05](https://github.com/OpenHands/extensions/pull/424#pullrequestreview-4864356803),
[2026-09-24](https://github.com/OpenHands/extensions/pull/424#pullrequestreview-5298188662),
[2026-10-04](https://github.com/OpenHands/extensions/pull/424#pullrequestreview-5407883473)).
It is a PR artifact and will be removed by the `PR Artifacts` workflow after merge.

## Before / after

The skill is advisory by contract: it is required to produce no patches and to
modify no files, so the durable output is a **prioritized plan**, not a diff.
"Before" is the repository with no refactoring plan; "after" is the plan below,
whose every finding cites a path, symbol, and line range that a reviewer can open.

## What was run

| | |
|---|---|
| Skill | `skills/refactoring-advisor/` at this PR head |
| Target repository | `OpenHands/extensions` at `bf31953` (the `main` commit this branch is rebased onto) |
| Agent | `mini-code-agent-langgraph` 0.4.0 — a plain LangGraph tool-use loop, not a special harness |
| Model | `deepseek-chat` |
| Agent source | https://github.com/wusuiling-if/mini-code-agent-langgraph |
| Files read | exactly 4 skill files + 3 code files (`sync_extensions.py`, `check_deprecations.py`, `deprecation.py`) |
| Files written | none (`workspace_changes` was empty in the run record) |

### Command

```bash
mca run "$(cat task.txt)" \
  --cwd <checkout of OpenHands/extensions@bf31953> \
  --model deepseek-chat --provider deepseek \
  --max-steps 35 --check noop 'true' --allow-zero-tests --yolo --yes
```

### Task given to the agent

```text
Read these four files first: skills/refactoring-advisor/SKILL.md, skills/refactoring-advisor/references/discovery.md, skills/refactoring-advisor/references/smells-and-strategies.md, skills/refactoring-advisor/references/report-template.md.

Then audit ONLY these three code files, which form one pipeline:
- scripts/sync_extensions.py
- scripts/check_deprecations.py
- python/openhands_extensions/deprecation.py

Budget: read at most 7 files in total (the 4 skill files plus these 3 code files). Do not list or read anything else in the repository. Once those 7 files are read, stop exploring and write the report.

Rules:
- Read-only. Never create, modify, or delete a file.
- Cite exact file path, symbol, and line range for every finding.
- Every proposal must state an explicit dependency-injection decision.
- Your final message must BE the report in Markdown using the headings from references/report-template.md verbatim. No preamble, no code fence around it.
```

## Reproduction notes

- Two earlier attempts with a repository-wide scope hit the step limit before
  producing a report; the run above bounds the read budget explicitly, which is
  also what `references/discovery.md` prescribes for large repositories.
- The agent needed a verification command to satisfy the harness gate. A no-op
  check (`true` with `--allow-zero-tests`) was used because this skill is
  read-only; nothing was verified or submitted as a patch.
- The report is the agent's own output, unedited apart from removing one
  conversational sentence at the top.

## Spot-check of citations

Three citations were checked by hand against `bf31953`; all matched.

| Report claim | Actual file |
|---|---|
| `deprecation.py:36` `deprecated` | `def deprecated(` at line 36 |
| `deprecation.py:83` `warn_deprecated` | `def warn_deprecated(` at line 83 |
| `deprecation.py:108` `warn_cleanup` | `def warn_cleanup(` at line 108 |
| `check_deprecations.py:178` `_gather_decorators` | `def _gather_decorators(` at line 178 |
| `check_deprecations.py:219` `_gather_warn_calls` | `def _gather_warn_calls(` at line 219 |
| `check_deprecations.py:171` `_extract_kw` | `def _extract_kw(` at line 171 |
| `deprecation.py:127-128` silent `except ...: pass` | `except pkg_version.InvalidVersion:` / `pass` |

## Raw output

# Refactoring Assessment

## Executive Summary

The three files form a coherent pipeline: `python/openhands_extensions/deprecation.py` defines the runtime deprecation vocabulary (`deprecated`, `warn_deprecated`, `warn_cleanup`), `scripts/check_deprecations.py` statically re-derives that vocabulary from ASTs to enforce a two-minor-release runway, and `scripts/sync_extensions.py` is an unrelated-but-adjacent registry synchronizer that shares the same "scan directories, report problems, optionally write" shape. The dominant structural problem is that the deprecation contract is duplicated in three places — the runtime helpers, the AST recognizers, and the runway policy — with no shared source of truth, so the checker silently under-reports whenever the runtime API grows a parameter or a new call form. The second problem is that both scripts hard-wire their entire environment (repository root, package list, marketplace directory, README path, vendor list) as module-level constants and read the filesystem directly, which makes them untestable without a real checkout and forces `SystemExit` to serve as the error channel. The highest-value intervention is to extract a small, explicitly injected "deprecation contract" (names, keyword parameters, runway policy) plus a filesystem/clock port, then have both the runtime module and the checker consume it; this is a narrow, low-risk change that removes the duplication and unlocks fixture-based tests. Constraints: the runtime module must keep mirroring `openhands.sdk.utils.deprecation` for public API compatibility, and the checker's exit-code contract (1 on any overdue/invalid record) is consumed by CI and must not change.

## Findings

### F1 — Duplicated deprecation vocabulary across runtime and checker

- **Evidence:** `python/openhands_extensions/deprecation.py:36-54` (`deprecated`), `:83-105` (`warn_deprecated`), `:108-137` (`warn_cleanup`) define the accepted keyword names (`deprecated_in`, `removed_in`, `cleanup_by`, `current_version`, `details`, `stacklevel`). `scripts/check_deprecations.py:178-216` (`_gather_decorators`), `:219-274` (`_gather_warn_calls`), `:171-175` (`_extract_kw`) independently hard-code the same names as string literals, and `:234`/`:256`/`:198` hard-code the three function names.
- **Corroboration:** Adding a keyword to `warn_deprecated` requires a matching edit in `_gather_warn_calls`; missing it means the checker records `None` and `_ru

...[elided 11028 chars]...

wly reported coverage problem as a finding, not a regression.

### P6 — Make the runtime clock and version explicit (addresses F8, F9)

Thread an optional `today` callable and an optional version provider through `_should_warn`, `warn_deprecated`, and `warn_cleanup`, and replace the silent `except ... : pass` in `warn_cleanup` with a diagnostic that is surfaced rather than dropped.

- **Dependency-injection decision:** **Inject both, with defaults.** `today` defaults to `date.today` and the version provider defaults to the cached `_current_version`; both are keyword-only parameters so the public signatures remain source-compatible with the SDK mirror. The `@cache` on `_current_version` should move behind the provider so tests can supply an uncached one.
- **Risk:** medium. This is the only proposal that touches a public runtime API surface; the keyword-only defaults keep it backward compatible, but the SDK-mirroring constraint must be re-checked before merging.

## Prioritized Actions

1. **P1** — highest value per unit of risk; removes the duplication that makes the checker silently under-report, and is a prerequisite for P2 and P3.
2. **P2** — unblocks unit testing of every parsing helper and removes the `except SystemExit: raise` smell.
3. **P3** — makes the checker's policy testable against fixture trees; depends on P1 and P2.
4. **P4** — the largest mechanical change; do it after the checker work so the two scripts are not in flight simultaneously.
5. **P5** — small, follows naturally from P4's context object.
6. **P6** — do last and separately, because it is the only change that touches a public runtime API and must be reconciled with the SDK mirror.

## Notes and Assumptions

- All line ranges are 1-based and refer to the files as read; no file was modified.
- F7's claim that the coverage predicate and `_entry_type` disagree is an inference from reading the two predicates, not an observed runtime failure.
- F9's consequence for `warn_cleanup` is inferred from the `except ... : pass` at `:127-128`; no execution was performed.
- The `openhands.sdk.utils.deprecation` mirroring constraint is taken from the module docstring at `python/openhands_extensions/deprecation.py:1-6`; the SDK source itself was outside the read budget and was not inspected.
- `scripts/sync_extensions.py` is not part of the deprecation pipeline proper; it is included because it shares the scan/report/repair shape and the same ambient-state problem, and P4/P5 are scoped to it alone.

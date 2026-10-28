# Scenarios

## Classes and categories

`--class` takes `functional`, `non_functional`, `adversarial` (comma-separated;
`generate` defaults to `functional,adversarial`).

`--category` takes, comma-separated:

| Class          | Categories                                                                                                                                                      |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| functional     | `happy_path`, `negative`, `boundary`, `integration`, `state_context`                                                                                            |
| non_functional | `token_economy`, `quality`                                                                                                                                      |
| adversarial    | `prompt_injection`, `jailbreak`, `data_exfiltration`, `pii_leakage`, `harmful_content`, `hallucination`, `hijacking`, `policy_violation`, `technical_injection` |

`performance` and `reliability` are no longer categories: `generate` refuses
them, though existing scenario files that use them still load and run.

Every scenario also carries free-form tags; `run --tag <names>` selects on them.
Red-team scenarios also carry OWASP LLM, OWASP Agentic (ASI) and MITRE ATLAS
references.

## Generating

```bash
rook generate --json                                  # functional + adversarial planned, rook picks the count
rook generate --total 20 --class functional --json
rook generate --category prompt_injection,jailbreak --json
rook generate -- focus on the refund limits and the identity check
```

`generate` derives scenarios per feature and pins them; a second `generate`
only refreshes features whose pins are stale. `--force` re-derives everything.
It may emit text despite `--json`; check the exit code, then read
`rook scenarios list --json`. An unknown `--class` or `--category` makes it exit
1 before analysing anything, listing every valid value.

Each scenario's feature is the one it was assigned. If the model named a
different feature, `generate` warns and saves that scenario excluded; review it
in `rook scenarios list --json` and bring it back with
`rook scenarios include <id>` if it belongs in runs.

`rook sync` stops before uploading anything when a scenario names a feature its
agent does not carry, and lists each one with its agent, the missing feature and
a fix. Apply the listed fix and sync again; do not run against upstream until
sync succeeds.

## Listing and curating

```bash
rook scenarios list --json
rook scenarios exclude SC-004 SC-009 --json           # kept on disk, left out of runs
rook scenarios include SC-004 --json
rook scenarios delete SC-021 --json                   # permanent
```

IDs are separate arguments here, unlike `run --only SC-004,SC-009`. A
comma-joined string is one unknown ID: nothing changes, and the document still
says `ok: true` with the string under `unknown`. Check `changed` in the reply.

`list` recomputes `unrunnable` against the current profile. A scenario needing
multiple turns without an observed conversation handle, or token-economy
grading without reported usage, is skipped by `run` and counts toward the
assurance gap, not toward Fail. File and image requirements are not rejected
solely by their input kind: inspect what the profile script can actually send.
`generate` keeps a scenario it cannot make runnable instead of dropping it:
`executable: false` with a `skip_reason`. Reasons from rook's own validation
start with `coverage gap:`, `invalid scenario:` or `invalid red-team
scenario:`; the scenario checker writes plain sentences, often a precondition
the profile cannot establish. Do not match on the prefix to find them; read
`executable`. Attack patterns with no scenario for a feature are listed in the
agent's `coverage-gaps.yaml` and the report's coverage gaps. Report both as
gaps, not as failures.

A plain `generate` can plan no attacks for a small agent. When the user asked
for red-team coverage and none was written, run
`rook generate --class adversarial --json` and say so.

Some attack patterns are skipped until the profile has the hook they need,
and the skip reason names it: an `open` hook that seeds the fixture in
`$ROOK_STATE_DIR/attack-fixture.json`, a `collect` hook that reports the
observed control and outcome, or `open` and `close` hooks for a fresh session.

## Scoping a run

```bash
rook run --only SC-001,SC-002 --json
rook run --class adversarial --json
rook run --category pii_leakage --tag refunds --json
rook run --concurrency 3 --name "pre-release" --json
rook run --test --json                                # against the tree as it is; kept out of the timeline
rook run --phases prepare,open,execute,close --json   # run the agent now
rook run --run <id> --phases collect,judge --json     # collect evidence that lands later, judge then
rook run --resume <id> --json                         # carry finished work into a new run
```

Without `--only`, a run selects at most two scenarios per attack pattern; the
rest are skipped as `pattern <id> already has 2 candidates in this run`. Name
them with `--only` to run more.

`--only` takes one comma-separated argument; repeating the flag keeps only
the last occurrence, and a space-separated second id is read as instruction
text. Each scenario runs once; there is no repeat count.

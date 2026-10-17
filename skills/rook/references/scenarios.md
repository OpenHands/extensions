# Scenarios

## Classes and categories

`--class` takes `functional`, `non_functional`, `adversarial` (comma-separated;
`generate` defaults to `functional,adversarial`).

`--category` takes, comma-separated:

| Class          | Categories                                                                                                                               |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| functional     | `happy_path`, `negative`, `boundary`, `integration`, `state_context`                                                                     |
| non_functional | `performance`, `token_economy`, `reliability`, `quality`                                                                                 |
| adversarial    | `prompt_injection`, `jailbreak`, `data_exfiltration`, `pii_leakage`, `harmful_content`, `hallucination`, `hijacking`, `policy_violation` |

Every scenario also carries free-form tags; `run --tag <names>` selects on them.

## Generating

```bash
rook generate --json                                  # functional + adversarial, rook picks the count
rook generate --total 20 --class functional --json
rook generate --category prompt_injection,jailbreak --json
rook generate -- focus on the refund limits and the identity check
```

`generate` derives scenarios per feature and pins them; a second `generate`
only refreshes features whose pins are stale. `--force` re-derives everything.
It may emit text despite `--json`; check the exit code, then read
`rook scenarios list --json`.

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

`--only` takes one comma-separated argument; repeating the flag keeps only
the last occurrence, and a space-separated second id is read as instruction
text.

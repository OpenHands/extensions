# Kane CLI policy gates

Kane CLI 0.10.0 can judge a sealed `.evidence` pack against a policy and return a verdict you can gate on. A policy is a YAML file with a name and a list of gates; each gate compares one metric of the pack with a limit.

## Policy format

```yaml
policy: pr-gate
gates:
  - id: all-pass
    metric: pass_rate
    min: 1
    severity: blocking
    message: Every test must pass.
  - id: no-broken-tests
    metric: totals.broken
    equals: 0
    severity: blocking
    message: Every test must run to a verdict.
  - id: every-test-checks
    metric: metrics.tests_without_checks
    equals: 0
    severity: blocking
    message: Every test must assert something.
  - id: no-healed-tests
    metric: metrics.heal.healed_tests
    max: 0
    severity: warning
    message: A healed test means the UI moved under a recorded step.
```

- `policy` names the policy. The verdict file is named after it.
- Each gate has an `id`, a `metric`, one limit (`min`, `max` or `equals`), a `severity` (`blocking` or `warning`) and a `message`.
- A limit outside the metric's range, for example `min: 2` on `pass_rate` (range 0 to 1), is rejected.

## Metrics

`kane-cli policy metrics-list` prints every metric a gate can use, one JSON object per line with its type and range. They include:

| Metric | Meaning |
|--------|---------|
| `totals.tests`, `totals.passed`, `totals.failed`, `totals.skipped` | Test counts |
| `totals.broken` | Tests whose check could not be evaluated |
| `pass_rate` | Passed tests divided by tests that were not skipped, from 0 to 1 |
| `steps.total`, `steps.failed`, `steps.skipped` | Step counts |
| `run.duration_ms` | Run duration in milliseconds |
| `failures.count` | Failure records in the pack |
| `metrics.tests_without_checks` | Tests with no assertion |
| `metrics.heal.healed_tests` | Tests that adaptive heal repaired |

## Commands

```bash
kane-cli evidence lint-policy gate.yaml                 # check a policy against the format and metric catalog
kane-cli evidence verdict <pack> --policy gate.yaml     # judge one pack
kane-cli evidence verdict <pack> --policy gate.yaml --json
kane-cli policy metrics-list                            # metrics a gate can use
kane-cli policy list                                    # policies stored in Test Manager
kane-cli policy create gate.yaml                        # lint a policy and store it in Test Manager
```

- `<pack>` is an execution id, a sealed `.evidence` path, or `latest`. After `kane-cli run`, use the path printed on stderr (`evidence: view locally with kane-cli evidence serve <path>`). `latest` only looks in `.testmuai/evidence/`, where `testmd run` and `testrun run` put their packs.
- `--policy` can be repeated, and `--policy-id <id>` judges against the latest version of a policy stored in Test Manager.

## Exit codes of `evidence verdict`

| Code | Meaning |
|------|---------|
| `0` | Every blocking gate passed |
| `1` | A blocking gate failed |
| `2` | Nothing was judged: the policy does not fit the metric catalog, or no pack was found |
| `3` | The verdict errored |

The verdict is written next to the pack as `<pack>.verdicts/<policy-id>.verdict.json`. Its `result`, `failed_gates` and `warnings` fields say what happened; a failed `warning` gate shows in `warnings` without failing the verdict.

## Judging as part of a run

`testmd run`, `testrun run` and `evidence merge` take `--policy <file>` and `--policy-id <id>` directly and judge the pack they seal. On `testmd run` and `testrun run`, a failing verdict exits `1` and an errored one `3`.

```bash
kane-cli testmd run tests/checkout_test.md --agent --policy gate.yaml
```

Based on the `kane-cli` 0.10.0 command help, `kane-cli policy metrics-list` and the 0.10.0 release notes: https://github.com/LambdaTest/kane-cli/releases/tag/0.10.0

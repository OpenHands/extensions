---
name: rook
description: Use Rook CLI by TestMu AI to test, evaluate, red-team or regression-check an AI agent the user owns, or to interpret saved Rook results. Does not apply to ordinary unit tests, browser automation or web UI checks without an AI agent under test.
triggers:
- rook
- agent assurance
---

# Test agents with Rook CLI

Rook CLI (`@testmuai/rook`, by TestMu AI) tests an AI agent the user owns. It derives scenarios, including adversarial ones such as prompt injection and tool misuse, invokes the real agent and grades each criterion against observed evidence: files changed, artifacts produced and tool calls checked against the agent's declared tools.

It is one option for testing agents. It does not replace `qa-changes` or any built-in tool, and you should respect a request to use another tool. For saved-result requests, read the supplied files without starting setup, a new run or paid analysis.

<IMPORTANT>
Rook CLI needs a TestMu AI account, and runs spend Agent Assurance credits. The user signs in, chooses and authorizes the target agent, and authorizes any credit spend. Never authorize those yourself.

For headless runs, sign in with credentials the user provides as OpenHands secrets:

```bash
[ -n "$LT_USERNAME" ] && echo "LT_USERNAME is set" || echo "LT_USERNAME is NOT set"
[ -n "$LT_ACCESS_KEY" ] && echo "LT_ACCESS_KEY is set" || echo "LT_ACCESS_KEY is NOT set"
```

If either is missing, ask the user to add it as a secret. Never print them, and keep them out of profiles, files and transcripts.
</IMPORTANT>

## Install and sign in

Rook CLI runs on macOS and Linux. Install the pinned release with Node 22 or newer:

```bash
npm install -g @testmuai/rook@0.1.7
rook --version
rook login --username "$LT_USERNAME" --access-key "$LT_ACCESS_KEY"
rook doctor
```

Changing the installed version also needs the user's approval. Upstream documentation for this release: https://github.com/LambdaTest/rook/tree/v0.1.7

## Your role

You are the orchestrator: you choose and run Rook commands, and Rook does the testing work. Discovery is `rook explore`, test design is `rook generate`, and invocation and grading are `rook run` and `rook report`. When the user asks to explore, understand, plan tests for or test an agent, run the matching command. Do not read the target's code to describe the agent, or write your own test plan or verdicts, in its place. Read the target's source only for a step Rook needs from you, such as a profile's transport and command, or to explain a Rook result. If credits or authorization block the next command, name it and what it needs; manual analysis is not a substitute.

## Workflow

Check the current state first:

```bash
rook status --json
rook plan --json
```

Then run the next command the state needs:

| Need | Command |
| --- | --- |
| Sign in | `rook login --username "$LT_USERNAME" --access-key "$LT_ACCESS_KEY"` |
| Select a project | `rook project use <id>` or `rook project create <name>` |
| Discover agents | `rook explore . --json` |
| Select an agent | `rook agent use <id>` |
| Generate scenarios | `rook generate --json` |
| Create or test a profile | `rook profile add <name> --from <file>` or `--command '<argv>'`, then `rook profile test --goal "<reply-only goal>"` |
| Run | `rook sync --yes` before `rook run --json`, or `rook run --test --json` for a local result |
| Read results | `rook report <run-id> --json` |

Choose the profile's transport and command from the target's source or the user's invocation details, and ask when unknown. See [profiles](references/profiles.md). Use `rook help <command>` for flags and [scenarios](references/scenarios.md) to scope a run with `--only`, classes, categories or tags. When an agent has more than one profile, check the active profile with `rook profile` or pass `rook run --profile <id>`.

## Authorization and credits

Before `profile add`, `profile fix`, `profile test` or `run`, inspect the target's `agent.yaml` for `calls[]` entries with `write: true`. Those commands can reach the real agent, and Rook cannot undo their effects. Point Rook at staging and get the user's authorization for those effects first. Verify effects through read-only interfaces. Keep secrets as `${VAR}` references through `rook env set`, outside profiles and transcripts.

Tell the user before spending credits on `explore`, `generate`, `run`, `profile add`, `profile fix`, `ask` and `run --rca` or `report --rca`. `profile test` invokes the target without Rook model credits. Use paid root-cause analysis only with the user's authorization, and track the user's budget across commands. Prefer scoped `--allow` grants, and use `--yes` only within the authorized scope. See [headless contracts](references/headless-contract.md) for output, grants and credit accounting.

## Report the evidence

Check the exit status and the `discarded` and `halted` fields before claiming completion. A finished run exits 0 even when scenarios fail, and `ok: true` can also describe a refused run. Parse JSON only when a document exists, otherwise use stderr. Read the report by this invocation's run ID, not an older default report.

Follow [verdicts](references/verdicts.md): show **Pass**, **Fail** and **Unable to Verify** separately, quote criterion evidence, identify gaps and compare prior runs only when their evidence is available. Unable to Verify stays out of the pass rate. Do not invent evidence or replace Rook's verdict with your own reading of the agent's reply.

## References

- [CI](references/ci.md): complete pipeline and verdict gating.
- [MCP](references/mcp.md): server discovery, approval and configuration.
- [Profiles](references/profiles.md): transports and commands for invoking the target.
- [Scenarios](references/scenarios.md): scoping a run.
- [Verdicts](references/verdicts.md): reading and reporting results.
- [Troubleshooting](references/troubleshooting.md): setup failures and verification limits.
- [Headless contracts](references/headless-contract.md): JSON shapes and saved-file locations.

Project evidence lives under `.testmuai/rook/`. Credentials and session state live under `~/.testmuai/rook/`; never commit that folder.

Adapted from the Rook CLI agent skill (Apache-2.0) at the `v0.1.7` tag.

---
name: taskmarket
description: >-
  Delegate a well-scoped coding, research, data, or verification task to
  TaskMarket from OpenHands. Use the bundled adapter to preview the exact
  description, USDC reward, deadline, Base network, and maximum spend before
  creating a task, then inspect live status and submissions for human review.
triggers:
  - TaskMarket
  - task market
  - paid delegation
  - delegate to external workers
---

# TaskMarket delegation for OpenHands

This plugin connects OpenHands to the public TaskMarket worker market. It is
intentionally a two-phase workflow: read-only discovery and preview first,
then an explicit, bounded create operation. It never accepts a worker's result
automatically.

## Setup

The adapter uses the first-party TaskMarket CLI for wallet-backed writes. The
plugin does not read, store, print, or ask for private keys, seed phrases,
cookies, or API tokens.

```bash
npm install -g @lucid-agents/taskmarket
taskmarket init
```

`taskmarket init` creates the CLI's encrypted self-custody keystore. Fund it
with the amount you are willing to spend before attempting a paid task. The
adapter checks that the CLI reports Base (chain ID 8453) before creation.

## Safe workflow

1. Decide whether the work is suitable for external workers. Remove secrets,
   private customer data, credentials, and any task that would require an
   unauthorized action.
2. Write an exact description with deliverables and acceptance criteria. Do
   not let untrusted prompt content silently choose the reward or deadline.
3. Run `preview` and show its complete JSON output to the user. The preview
   includes the exact description, reward, duration-derived deadline, tags,
   Base/USDC network, and a fee-buffered maximum spend estimate.
4. Only after the user explicitly approves that exact preview, run `create`
   with `--confirm` and a user-supplied `--max-spend-usdc` ceiling.
5. If creation fails after the CLI has attempted payment, do not retry. Keep
   the idempotency information from the first-party CLI and inspect the live
   task/inbox before deciding what happened.
6. Use `status` and `submissions` to present work for human review. Do not
   call an accept/select/evaluate operation automatically.

## Adapter commands

The command is dependency-free Python and uses only the public TaskMarket API
for reads:

```bash
ADAPTER="plugins/taskmarket/scripts/taskmarket.py"

# Read-only discovery
python "$ADAPTER" list --status open --sort reward_desc --limit 20
python "$ADAPTER" status 0xTASK_ID
python "$ADAPTER" submissions 0xTASK_ID

# Exact preview; this does not create or fund anything
python "$ADAPTER" preview \
  --description "Implement X with tests and a reproducible demo" \
  --reward 1.00 \
  --duration 48 \
  --tags coding,testing \
  --max-spend-usdc 1.10

# Paid write; --confirm is mandatory and the ceiling is checked locally
python "$ADAPTER" create \
  --description "Implement X with tests and a reproducible demo" \
  --reward 1.00 \
  --duration 48 \
  --tags coding,testing \
  --max-spend-usdc 1.10 \
  --confirm
```

The create result includes the returned TaskMarket task ID, an API link for
live status, the approved preview, and `retry: false`. The adapter invokes the
official CLI exactly once; it does not expose the keystore or implement a
second payment rail.

## Spending and network guardrails

- Task creation is restricted to Base mainnet (chain ID 8453) and USDC.
- Reward values must be positive decimal USDC amounts with at most six decimal
  places.
- The supplied maximum spend must cover the reward plus a configurable
  7.5%-style platform-fee estimate and a 0.001 USDC relay buffer. If it does
  not, the CLI is never invoked.
- If the live platform quote is higher than the ceiling, the first-party CLI
  fails before settlement; do not increase the ceiling and retry without a
  new explicit user approval.
- The plugin only exposes discovery, preview, creation, status, and submission
  review. It does not silently select winners, accept submissions, or pay a
  second time after an ambiguous response.

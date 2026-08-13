# TaskMarket plugin

This OpenHands plugin provides a small, auditable adapter for the
[TaskMarket](https://taskmarket.dev/) worker market.

## What it adds

- Public task discovery through `https://api.taskmarket.dev/api/tasks`.
- Live task and submission inspection for human review.
- A deterministic preview containing the exact task text, USDC reward,
  duration-derived deadline, Base network, and maximum-spend estimate.
- A guarded create path that delegates payment signing to the official
  `@lucid-agents/taskmarket` CLI only after `--confirm` and a spend ceiling are
  supplied.

The adapter has no wallet implementation and never reads the TaskMarket
keystore. It also has no accept, evaluate, or retry command by design.

## Install the first-party CLI

```bash
npm install -g @lucid-agents/taskmarket
taskmarket init
```

The user is responsible for funding the CLI wallet and approving the exact
preview before using `create`.

## Examples

```bash
python plugins/taskmarket/scripts/taskmarket.py list --status open --limit 10

python plugins/taskmarket/scripts/taskmarket.py preview \
  --description "Produce a tested report with reproducible evidence" \
  --reward 0.50 \
  --duration 24 \
  --tags research,verification \
  --max-spend-usdc 0.55

python plugins/taskmarket/scripts/taskmarket.py create \
  --description "Produce a tested report with reproducible evidence" \
  --reward 0.50 \
  --duration 24 \
  --tags research,verification \
  --max-spend-usdc 0.55 \
  --confirm
```

For the full safety contract and OpenHands usage guidance, read
[`SKILL.md`](SKILL.md).

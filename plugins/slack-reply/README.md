# slack-reply

Reusable Python scripts for Slack-triggered OpenHands automations.

This plugin is consumed by the [`slack-channel-listener`](../../skills/slack-channel-listener) skill,
which copies the contents of `scripts/` into a [custom-automation](../../skills/openhands-automation/references/custom-automation.md)
tarball and uploads it. The scripts themselves are also usable directly if
you want to assemble your own automation by hand.

## Usage paths

| Trigger | Entrypoint | Comment |
|---|---|---|
| Slack Events API webhook | `agent_event.py` | One automation run per matching message. Near real-time. Requires the automation backend to be reachable from Slack. |
| Cron poll | `agent_poll.py` | One automation run per cron tick, handles any matching messages since the last marker. Works behind firewalls; uses message reactions as state. |

See `SKILL.md` for the full environment-variable contract.

## Local sanity check

```bash
# Inside the unpacked plugin directory
python -m py_compile scripts/*.py
```

There's no runtime test harness in this repo because the scripts depend on
`openhands-sdk` and a live Slack token; tests live alongside the consuming
skill (`skills/slack-channel-listener`) and are exercised via automation
dry-runs in CI.

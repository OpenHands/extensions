---
name: cortex-training-rl
description: >-
  Run reinforcement-learning post-training of a model inside the OpenHands
  agent harness on Snowflake Cortex Training for any Harbor training and eval
  task directories or SWE-smith code localization, and generate the reward
  convergence graph. Use when asked to launch, monitor, debug, stop, or plot an
  OpenHands or Harbor RL run on Cortex Training.
triggers:
- /cortex-training-rl
- cortex training
- cortex-training
- arctic platform
- arctic-platform
- codescout
- harbor
---

# OpenHands RL post-training on Cortex Training

The trainer and the sampler run on Cortex Training GPUs (`4 training + 4 sampling H200s`). Your machine runs a CPU-only driver that executes OpenHands rollouts against a local OpenAI-compatible proxy (`ChatCompletionsProxy`) and sends the exact sampled token IDs (`loss_mask = 1` on assistant turns, `0` on prompts and tool outputs) plus verifier rewards back to Cortex for a GSPO/GRPO update.

Two recipes ship in [Arctic Platform](https://github.com/Snowflake-AI-Research/Arctic-Platform):
1. **Harbor RL (`recipes/rl/harbor` + `arctic_platform/integrations/harbor`, [PR #294](https://github.com/Snowflake-AI-Research/Arctic-Platform/pull/294)):**
   Takes any Harbor training and eval task directories (`TRAIN_HARBOR_TASKS` and `EVAL_HARBOR_TASKS`, each task containing `instruction.md`, `environment/`, and `tests/test.sh`) and any target OpenHands agent (`HARBOR_SKILL`, `OPENHANDS_TOOLS`, `OPENHANDS_SYSTEM_PROMPT_FILE`, or `HARBOR_AGENT`). Each rollout is orchestrated by Harbor's `Trial` and scored by Harbor's `Verifier` (`tests/test.sh` $\to$ `/logs/verifier/reward.txt` or `reward.json`).
2. **Code localization (`recipes/rl/openhands/code_localization`):**
   Direct SWE-smith code localization (`file + module + function F1`, max `3.0`).

- Cortex Training guides: [`docs/integrations/openhands.md`](https://github.com/snowflakedb/cortex-training/blob/main/docs/integrations/openhands.md) · [`docs/integrations/bring-your-own-agent.md`](https://github.com/snowflakedb/cortex-training/blob/main/docs/integrations/bring-your-own-agent.md)
- Harbor recipe guide: [`recipes/rl/harbor/README.md`](https://github.com/Snowflake-AI-Research/Arctic-Platform/blob/main/recipes/rl/harbor/README.md). Its Snowflake sandbox environment (`HARBOR_ENV=snowflake`) ships in Arctic Platform.

## Rules

1. **Identify jobs by comment.** Set `ARCTIC_CORTEX_JOB_COMMENT` with your name; never cancel a job whose comment is not yours.
2. **One run per driver machine.** Concurrent runs collide on tmux sessions, ptys, and workspace disk.
3. **Never `kill -9` the driver.** Stop with `SIGTERM` or Ctrl-C so the launcher's exit trap cancels the Cortex GPU job.
4. **Keep credentials private.** Never print, log, or commit PATs or login configs. Don't `cat` `~/cortex-training-config.json` or `~/.snowflake/connections.toml`; check them with `jq 'keys'` or `grep -c '^\['`.
5. **Keep recipe hyperparameters intact.** Fix environment issues (`references/troubleshooting.md`) rather than changing batch size, context length, or learning rate.

## Workflow

### 1. Preflight

```bash
cortex-training login ~/cortex-training-config.json   # once per machine
# The launchers read the Cortex connection only from ARCTIC_CORTEX_*; login alone is not enough.
cfg=~/cortex-training-config.json
export ARCTIC_CORTEX_HOST=$(jq -r .host "$cfg") ARCTIC_CORTEX_DATABASE=$(jq -r .database "$cfg")
export ARCTIC_CORTEX_SCHEMA=$(jq -r .schema "$cfg") ARCTIC_CORTEX_PAT=$(jq -r .pat "$cfg")
cortex-training capacity                              # available_gpus must be at least 8
cortex-training list --status running                 # check for live jobs
pgrep -af 'run_qwen35_4b.sh|skyrl.train'              # live driver on this host?
tmux ls 2>/dev/null | grep -c '^openhands-'           # leaked rollout sessions
cat /proc/sys/kernel/pty/nr /proc/sys/kernel/pty/max  # ptys in use / limit
df -h "${OPENHANDS_WORKSPACE:-/tmp/testbed}"          # workspace disk
```

If no run is live and `openhands-*` tmux sessions remain, clear them before launching:

```bash
tmux ls -F '#{session_name}' 2>/dev/null | grep '^openhands-' | xargs -r -n1 tmux kill-session -t
```

### 2. Prepare data

Requires `uv`. Run everything below from the root of an `Arctic-Platform` checkout, with SkyRL at `skyrl-v0.3.0` next to it:

```bash
git clone https://github.com/Snowflake-AI-Research/Arctic-Platform && cd Arctic-Platform
git clone --branch skyrl-v0.3.0 --depth 1 https://github.com/NovaSky-AI/SkyRL
export SKYRL_HOME=$PWD/SkyRL
```

- **Any Harbor task set (`recipes/rl/harbor`):**
  Point `TRAIN_HARBOR_TASKS` and `EVAL_HARBOR_TASKS` at any directories of Harbor tasks (`instruction.md` + `tests/test.sh`). To export SWE-smith code localization into Harbor task directories (`train/` and `eval/`):
  ```bash
  uv run recipes/rl/harbor/prepare_data.py \
    --export-swe-smith-to ~/data/swe-smith-harbor-tasks \
    --out ~/data/harbor-rl
  ```
- **Direct SWE-smith code localization (`recipes/rl/openhands/code_localization`):**
  ```bash
  uv run recipes/rl/openhands/code_localization/prepare_data.py
  ```

### 3. Launch detached

Always launch on a dedicated tmux socket (`-L "$RUN_NAME"`) with `TMUX` and `TMUX_PANE` unset so `libtmux` inside OpenHands does not attach to the launcher's tmux server.

**Harbor RL (`recipes/rl/harbor/run_qwen35_4b.sh`):**

```bash
export RUN_NAME=qwen35-4b-harbor-rl-$(date +%m%d-%H%M)
export CKPT_DIR=$HOME/checkpoints/$RUN_NAME
export TRAIN_HARBOR_TASKS=$HOME/data/swe-smith-harbor-tasks/train
export EVAL_HARBOR_TASKS=$HOME/data/swe-smith-harbor-tasks/eval
export HARBOR_SKILL=/path/to/SKILL.md   # optional: ":"-separated SKILL.md paths
# Snowflake sandboxes (the default). base_image replays each task's Dockerfile on the sandbox catalog image.
# SWE-smith tasks clone from GitHub, so egress_eai must name an external access integration that allows github.com.
export HARBOR_ENV_KWARGS='{"base_image": "sandbox-base", "connection": "MY_CONN", "role": "MY_ROLE", "egress_eai": "MY_GITHUB_EAI"}'
export ARCTIC_CORTEX_JOB_COMMENT="<your name> harbor rl - ask before cancelling"
export LOGGER=console OPENHANDS_WORKSPACE=/path/with/space STARTUP_TIMEOUT=14400
mkdir -p "$CKPT_DIR"

tmux -L "$RUN_NAME" new-session -d -s train \
  "echo \$\$ > $CKPT_DIR/launcher.pid; exec env -u TMUX -u TMUX_PANE \
   bash recipes/rl/harbor/run_qwen35_4b.sh trainer.max_training_steps=100"
```

To evaluate during training, append `trainer.eval_before_train=true trainer.eval_interval=10` to the launcher command: the model is evaluated on `EVAL_HARBOR_TASKS` before the first step and every 10 steps after it, and each evaluation prints `eval/all/avg_score` in the log. The launcher runs no evaluation by default.

Before it provisions GPUs, the launcher runs the first training task once in its sandbox with an agent that does nothing. If the sandbox, the Dockerfile replay, or the verifier fails, it exits with the cause and no Cortex job is created; see [references/troubleshooting.md](references/troubleshooting.md).

Optional environment variables to target any OpenHands configuration or Harbor sandbox:
- `OPENHANDS_TOOLS`: comma-separated OpenHands tools (e.g. `terminal,task_tracker`). The Harbor recipe has no `file_editor`, because it would edit the driver's filesystem instead of the sandbox's.
- `OPENHANDS_SYSTEM_PROMPT_FILE`: custom system prompt template file.
- `HARBOR_AGENT`: a Harbor `BaseAgent` that runs on the driver (default `harbor_rl.agent:OpenHandsHarborAgent`, or your own `module:Class`). Agents Harbor installs inside the environment (`openhands-sdk`, `mini-swe-agent`, `claude-code`, ...) are refused, because task code there could read the rollout's API key.
- `HARBOR_ENV`: `snowflake` (default) or `host` for trusted tasks only, which also needs `HARBOR_ALLOW_HOST_EXEC=1`. These two were run end to end; Harbor's other environments are accepted but untested with this recipe.
- `HARBOR_ENV_KWARGS`: JSON object passed to the environment, like `harbor run --ek`. For `snowflake`: `base_image`, `connection`, `role`, `egress_eai`. Use a Snowflake connection that logs in without a browser (programmatic access token or key pair): the run logs in again every 20 minutes.

**Direct code localization (`recipes/rl/openhands/code_localization/run_qwen35_4b.sh`):**

```bash
export RUN_NAME=qwen35-4b-openhands-$(date +%m%d-%H%M)
export CKPT_DIR=$HOME/checkpoints/$RUN_NAME
export ARCTIC_CORTEX_JOB_COMMENT="<your name> openhands localization - ask before cancelling"
export LOGGER=console OPENHANDS_WORKSPACE=/path/with/space STARTUP_TIMEOUT=14400
mkdir -p "$CKPT_DIR"

tmux -L "$RUN_NAME" new-session -d -s train \
  "echo \$\$ > $CKPT_DIR/launcher.pid; exec env -u TMUX -u TMUX_PANE \
   bash recipes/rl/openhands/code_localization/run_qwen35_4b.sh trainer.max_training_steps=100"
```

### 4. Monitor and recreate the reward graph

A step is done when the log prints its `'reward/avg_raw_reward'`. `trajectories/step_<N>/` appears when the step's rollouts finish, before its update, so don't count steps from those directories:

```bash
sed 's/\x1b\[[0-9;]*m//g' "$CKPT_DIR/$RUN_NAME.log" | grep -oE "'reward/avg_raw_reward': '[0-9.]+'"
```

The run ends by itself after `trainer.max_training_steps`, and the launcher cancels its Cortex job; don't stop it to finish it.

The `references/` files sit next to this `SKILL.md`. Use [references/monitoring.md](references/monitoring.md) to check job state, print 10-step reward means, count `.error` files, and generate `$CKPT_DIR/reward_graph.svg` with its snippet, which needs only Python's standard library. Use [references/troubleshooting.md](references/troubleshooting.md) if steps finish in seconds or rewards drop to 0.

### 5. Stop and clean up

To end a run early:

```bash
kill -TERM "$(cat "$CKPT_DIR/launcher.pid")"
# The job is cancelled at once; the launcher takes up to 2 minutes more to stop its rollouts.
# Confirm the run's job is CANCELLED. Jobs are identified by their comment.
cortex-training list | jq -r --arg c "$ARCTIC_CORTEX_JOB_COMMENT" '.jobs[] | select(.comment == $c) | "\(.job_id) \(.status)"'
```

## Reference result (Qwen3.5-4B, 4+4 H200 GPUs)

SWE-smith code localization, reward out of `3.0`. The Harbor run used Snowflake sandboxes with `base_image` for 25 steps.

| Window | With Harbor (`recipes/rl/harbor`) | Without Harbor (`recipes/rl/openhands/code_localization`) | CodeScout Reference |
| --- | --- | --- | --- |
| **Steps 1–10 mean** | `0.59` | `0.39` | `0.76` |
| **Steps 11–20 mean** | `1.81` | `1.39` | — |
| **Steps 21–25 mean** | `2.39` (best step `2.54`) | — | — |
| **Steps 21–30 mean** | — | `2.28` | `~2.30` |
| **Steps 91–100 mean** | — | `2.28` | `2.34` |

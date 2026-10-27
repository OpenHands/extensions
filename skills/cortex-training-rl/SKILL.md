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
- Harbor Snowflake Sandbox provider (`--env snowflake`): [harbor-framework/harbor#3918](https://github.com/harbor-framework/harbor/pull/3918)

## Rules

1. **Identify jobs by comment.** Set `ARCTIC_CORTEX_JOB_COMMENT` with your name; never cancel a job whose comment is not yours.
2. **One run per driver machine.** Concurrent runs collide on tmux sessions, ptys, and workspace disk.
3. **Never `kill -9` the driver.** Stop with `SIGTERM` or Ctrl-C so the launcher's exit trap cancels the Cortex GPU job.
4. **Keep credentials private.** Never print, log, or commit PATs or login configs.
5. **Keep recipe hyperparameters intact.** Fix environment issues (`references/troubleshooting.md`) rather than changing batch size, context length, or learning rate.

## Workflow

### 1. Preflight

```bash
cortex-training login ~/cortex-training-config.json   # once per machine
cortex-training capacity --hardware H200              # need 8 free
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

Requires `uv`, SkyRL at `skyrl-v0.3.0` (`export SKYRL_HOME=/path/to/SkyRL`), and an `Arctic-Platform` checkout.

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
export ARCTIC_CORTEX_JOB_COMMENT="<your name> harbor rl - ask before cancelling"
export LOGGER=console OPENHANDS_WORKSPACE=/path/with/space STARTUP_TIMEOUT=14400
mkdir -p "$CKPT_DIR"

tmux -L "$RUN_NAME" new-session -d -s train \
  "echo \$\$ > $CKPT_DIR/launcher.pid; exec env -u TMUX -u TMUX_PANE \
   bash recipes/rl/harbor/run_qwen35_4b.sh trainer.max_training_steps=100"
```

Optional environment variables to target any OpenHands configuration or Harbor sandbox:
- `OPENHANDS_TOOLS`: comma-separated OpenHands tools (e.g. `terminal,file_editor,task_tracker`).
- `OPENHANDS_SYSTEM_PROMPT_FILE`: custom system prompt template file.
- `HARBOR_AGENT`: Harbor `BaseAgent` (default `harbor_rl.agent:OpenHandsHarborAgent`, or `openhands-sdk`, `openhands`, `module:Class`).
- `HARBOR_ENV`: Harbor `BaseEnvironment` (default `arctic_platform.integrations.harbor.env:HostEnvironment`, or `arctic_platform.integrations.harbor.snowflake_sandbox:SnowflakeSandboxEnvironment` / `snowflake`, `docker`, `modal`, `daytona`).

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

Use [references/monitoring.md](references/monitoring.md) to check job state, print 10-step reward means, count `.error` files, and generate `$CKPT_DIR/reward_graph.svg`. Use [references/troubleshooting.md](references/troubleshooting.md) if steps finish in seconds or rewards drop to 0.

### 5. Stop and clean up

```bash
kill -TERM "$(cat "$CKPT_DIR/launcher.pid")"
cortex-training get "$(cat "$CKPT_DIR/cortex_job_id")"  # confirm status is cancelled
```

## Reference result (Qwen3.5-4B, 4+4 H200 GPUs)

| Window | With Harbor (`recipes/rl/harbor`) | Without Harbor (`recipes/rl/openhands/code_localization`) | CodeScout Reference |
| --- | --- | --- | --- |
| **Steps 1–10 mean** | `0.35` (`0.78` at step 10) | `0.39` (`0.75` at step 10) | `0.76` |
| **Steps 11–20 mean** | `1.46` (`2.03` at step 16, `2.10` at step 19) | `1.39`–`1.54` (`2.17` at step 16) | — |
| **Steps 21–30 / 21–25** | Peak `2.13` (step 21), `2.10` (step 24), `0 / 1,600` errors | `2.28`–`2.32` | `~2.30` |
| **Steps 91–100 mean** | — | `2.28` (`2.25` at step 100) | `2.34` (`2.27` at step 100) |

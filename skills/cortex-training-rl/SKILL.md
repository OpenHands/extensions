---
name: cortex-training-rl
description: >-
  Run reinforcement-learning post-training of a model inside the OpenHands
  agent harness on Snowflake Cortex Training, using the Arctic Platform
  OpenHands recipes (CodeScout code localization and Harbor task directories
  such as Terminal-Bench 2.0). Use when asked to launch, monitor, debug, or
  stop an OpenHands or Harbor RL run on Cortex Training.
triggers:
- cortex training
- cortex-training
- arctic platform
- arctic-platform
- codescout
- harbor
---

# OpenHands RL post-training on Cortex Training

The trainer and the sampler run on Cortex Training GPUs. Your machine runs a
CPU-only driver that executes OpenHands conversations against the sampler and
sends the scored episodes back for a policy update.

Two ready-to-run OpenHands recipes ship in Arctic Platform:
1. **Harbor tasks (`recipes/rl/openhands/harbor`):** go directly from any
   [Harbor](https://github.com/laude-institute/harbor) task directory (such as
   Terminal-Bench 2.0, where each task has `instruction.md`, `environment/`, and
   `tests/test.sh`) to RL post-training of an OpenHands agent with
   `TerminalTool` and `HarborFinishTool`, graded by the task's `tests/test.sh`
   verifier.
2. **CodeScout code localization (`recipes/rl/openhands/code_localization`):**
   train Qwen3.5-4B to name the files, classes, and functions a bug touches,
   scored by F1 (maximum 3).

- Code localization recipe: [Arctic Platform `recipes/rl/openhands/code_localization`](https://github.com/Snowflake-AI-Research/Arctic-Platform/tree/main/recipes/rl/openhands/code_localization)
- Harbor tasks recipe: [Arctic Platform `recipes/rl/openhands/harbor`](https://github.com/Snowflake-AI-Research/Arctic-Platform/pull/294)
- Cortex Training guide: [`docs/integrations/openhands.md`](https://github.com/snowflakedb/cortex-training/blob/main/docs/integrations/openhands.md)
- Bring your own agent / Harbor tasks: [`docs/integrations/bring-your-own-agent.md`](https://github.com/snowflakedb/cortex-training/blob/main/docs/integrations/bring-your-own-agent.md)
- How the harness plugs into a trainer: <https://docs.openhands.dev/sdk/guides/train-rl>

A run holds 8 GPUs for hours and the job outlives the driver. Read the
rules below before running anything.

## Rules

1. **Cortex jobs are shared.** Every job on an account can report the same
   submitter. The `comment` is the only ownership signal. Always set
   `ARCTIC_CORTEX_JOB_COMMENT` to something with your name, and never cancel a
   job whose comment you did not set.
2. **One run per driver machine.** Rollouts from two runs share the tmux server,
   the pty pool, and the workspace disk. Check for a live run (step 1 below)
   before launching.
3. **A job keeps its GPUs until it is cancelled.** Killing the driver with
   `SIGKILL` skips the launcher's exit trap and leaves the job running. Stop
   with `SIGTERM` or Ctrl-C, then confirm that the job is cancelled.
4. **Credentials stay private.** Never print, log, or commit the PAT or the
   login config. Do not copy them to shared storage. Use only your own.
5. **Do not change hyperparameters to make a run "work".** The recipe's knobs
   reproduce the reference curve. Fix the environment instead.

## Workflow

### 1. Preflight

```bash
cortex-training login ~/cortex-training-config.json   # once per machine
cortex-training capacity --hardware H200              # need 8 free
cortex-training list --status running                 # look for your comment
pgrep -af 'run_qwen35_4b.sh|skyrl.train'              # a live run on this machine?
tmux ls 2>/dev/null | grep -c '^openhands-'           # leftover rollout sessions
cat /proc/sys/kernel/pty/nr /proc/sys/kernel/pty/max  # ptys in use / limit
df -h "${OPENHANDS_WORKSPACE:-/tmp/testbed}"          # workspace disk
```

Stop and report if a run is live or capacity is short. If no run is live
and `openhands-*` sessions remain, a killed run leaked them. Each holds a
pty. Clear them before launching:

```bash
tmux ls -F '#{session_name}' 2>/dev/null | grep '^openhands-' | xargs -r -n1 tmux kill-session -t
```

Put `OPENHANDS_WORKSPACE` on a disk with tens of GB free. Each in-flight
rollout holds one clone or trial directory of its task.

### 2. Install and data

Follow the recipe README: `uv`, SkyRL at tag `skyrl-v0.3.0` as `SKYRL_HOME`,
and the Arctic Platform checkout (`main`).

**Option A - Harbor tasks (Terminal-Bench 2.0 or custom Harbor tasks):**

Download a Harbor dataset (or point `HARBOR_TASKS_DIR` at any directory of
Harbor tasks containing `instruction.md` and `tests/test.sh`):

```bash
uvx harbor datasets download terminal-bench@2.0 -o ~/.cache/harbor/tasks/terminal-bench-2.0
uv run recipes/rl/openhands/harbor/prepare_data.py \
  --harbor-tasks-dir ~/.cache/harbor/tasks/terminal-bench-2.0 \
  --out ~/data/harbor-openhands
```

(Or simply export `HARBOR_TASKS_DIR=~/.cache/harbor/tasks/terminal-bench-2.0`
when launching `recipes/rl/openhands/harbor/run_qwen35_4b.sh`, which runs
`prepare_data.py` automatically.)

**Option B - CodeScout code localization (`SWE-smith`):**

From the Arctic Platform checkout, download the dataset and write
`train.parquet` and `validation.parquet` into `~/data/swe-smith-localization`
(or pass `--out DIR` and set `DATA_DIR=DIR`):

```bash
uv run recipes/rl/openhands/code_localization/prepare_data.py
```

The launcher refuses to start when any required input is missing and prints
what to fix.

### 3. Launch detached

The run takes hours, so it must survive the shell closing. Launch it in
detached tmux on a socket named after the run, with `TMUX` and `TMUX_PANE`
removed. OpenHands drives its terminal tool through `libtmux`, which follows
`TMUX` to whatever server the launcher sits in. If the variables leak, the
rollouts create and kill sessions on the launcher's own server.

**Launch Harbor tasks RL training (`recipes/rl/openhands/harbor/run_qwen35_4b.sh`):**

```bash
export RUN_NAME=qwen35-4b-openhands-harbor-$(date +%m%d-%H%M)
export CKPT_DIR=$HOME/checkpoints/$RUN_NAME
export HARBOR_TASKS_DIR=$HOME/.cache/harbor/tasks/terminal-bench-2.0
export ARCTIC_CORTEX_JOB_COMMENT="<your name> openhands harbor - ask before cancelling"
export LOGGER=console OPENHANDS_WORKSPACE=/path/with/space STARTUP_TIMEOUT=14400
mkdir -p "$CKPT_DIR"

tmux -L "$RUN_NAME" new-session -d -s train \
  "echo \$\$ > $CKPT_DIR/launcher.pid; exec env -u TMUX -u TMUX_PANE \
   bash recipes/rl/openhands/harbor/run_qwen35_4b.sh trainer.max_training_steps=50"
```

**Launch CodeScout code localization (`recipes/rl/openhands/code_localization/run_qwen35_4b.sh`):**

```bash
export RUN_NAME=qwen35-4b-openhands-$(date +%m%d-%H%M)   # unique: the job id file lives under it
export CKPT_DIR=$HOME/checkpoints/$RUN_NAME
export ARCTIC_CORTEX_JOB_COMMENT="<your name> openhands localization - ask before cancelling"
export LOGGER=console OPENHANDS_WORKSPACE=/path/with/space STARTUP_TIMEOUT=14400
mkdir -p "$CKPT_DIR"

tmux -L "$RUN_NAME" new-session -d -s train \
  "echo \$\$ > $CKPT_DIR/launcher.pid; exec env -u TMUX -u TMUX_PANE \
   bash recipes/rl/openhands/code_localization/run_qwen35_4b.sh trainer.max_training_steps=100"
```

Run this from the Arctic Platform checkout. A new tmux server copies the
current environment, but an existing one keeps the environment it started
with. That is why the socket is per run: a shared socket would launch with
stale variables. `STARTUP_TIMEOUT` (seconds) covers the wait for GPU
placement. The launcher writes `$CKPT_DIR/$RUN_NAME.log` itself.
`tmux -L "$RUN_NAME" attach` shows the live output.

### 4. Monitor

The log is `$CKPT_DIR/$RUN_NAME.log`, and the job id is in
`$CKPT_DIR/cortex_job_id`. Check the job, the per-step reward, and the
rollout errors as shown in [references/monitoring.md](references/monitoring.md).

Signs of a healthy run:

- The job is `running`.
- A new step lands every few minutes.
- On code localization, the 10-step mean of `reward/avg_raw_reward` rises from
  about 0.4 to about 2.3 by steps 21-30; on Harbor tasks, `reward/avg_raw_reward`
  (and `reward/test_passed`) tracks the fraction of rollouts passing `tests/test.sh`.
- `policy/grad_norm` stays under 1.

About 1% of rollouts failing with `ContextWindowExceeded` is expected at a
32768-token context. A whole batch of errors, a reward stuck at 0, or steps
that finish in seconds mean the rollouts are failing. Look the symptom up in
[references/troubleshooting.md](references/troubleshooting.md).

### 5. Stop and clean up

```bash
kill -TERM "$(cat "$CKPT_DIR/launcher.pid")"            # the launcher stops the driver, then cancels the job
cortex-training get "$(cat "$CKPT_DIR/cortex_job_id")"  # confirm status is cancelled
```

If the launcher is already gone and the job is still running, check that its
`comment` is yours, then run
`cortex-training cancel "$(cat "$CKPT_DIR/cortex_job_id")"`. Afterwards, check
again for leftover `openhands-*` tmux sessions and for clones under
`$OPENHANDS_WORKSPACE`, and remove them if no run is live.

## Custom controllers, compaction, and Tinker Cookbook Harbor RL

Both OpenHands recipes are built on `arctic_platform.integrations.harness`
([`ChatCompletionsProxy` and `HarnessGenerator`](https://github.com/Snowflake-AI-Research/Arctic-Platform/tree/main/arctic_platform/integrations/harness)),
which is harness-agnostic:

1. **Custom controller or Harbor environment (`arctic_platform.integrations.harness`):**
   - Implement the 3-method `HarnessAdapter` (`submit(request) -> rollout_id`,
     `get_status(rollout_id)`, `collect_output(rollout_id) -> artifacts`) and
     point your agent or Harbor runner (`harbor run` with `--env docker`,
     `--env modal`, or Snowflake Cortex Sandboxes) at
     `OPENAI_BASE_URL=request.base_url` and `OPENAI_API_KEY=request.api_key`.
   - Pass a standalone `Grader` callable `(episodes, artifacts, request) -> Grade(reward, reward_detail, exhausted=False)`
     into `HarnessGenerator`. Verification is decoupled from the rollout runner.
   - **Context compaction and subagents:** `ChatCompletionsProxy` splices the
     exact sampled token IDs across turns (`loss_mask = 1` on assistant turns,
     `0` on prompts and tool output). A request that does not extend the prior
     messages (such as a compacted history) starts a new chain. Set
     `generator.step_wise_trajectories=true` so every chain becomes a training
     row under the same `trajectory_id`. To avoid training on the LLM call that
     writes a compaction summary, send the summarization call to the un-routed
     `${proxy.base_url}/v1/chat/completions` endpoint; send it to
     `request.base_url` if you want the summary call itself trained on.
2. **Tinker Cookbook Harbor RL (`arctic_platform.integrations.tinker`):**
   - To run `tinker-cookbook` recipes (including `tinker_cookbook.recipes.harbor_rl.train`
     with a custom `SandboxFactory` such as Modal or `snowflake.sandbox.AsyncSandbox`)
     on Cortex Training without a local GPU driver, run
     `python -m arctic_platform.integrations.tinker.run --training-gpus 4 --sampling-gpus 4 <module> [args...]`.
     See [`docs/integrations/tinker.md`](https://github.com/snowflakedb/cortex-training/blob/main/docs/integrations/tinker.md).

## Reference result

- **Code localization (`recipes/rl/openhands/code_localization`):** On 4 training
  plus 4 sampling H200s, 100 steps of 8 prompts x 8 rollouts gave 10-step means
  of `reward/avg_raw_reward`: 0.39 for steps 1-10, 2.28 for steps 21-30, and
  2.28 for steps 91-100 (matching the CodeScout reference curve near 2.3).
- **Harbor tasks (`recipes/rl/openhands/harbor` on Terminal-Bench 2.0):** On 4
  training plus 4 sampling H200s with Qwen3.5-4B, running the OpenHands agent
  (`TerminalTool` + `HarborFinishTool`) over Harbor tasks with `tests/test.sh`
  pytest verification doubled `reward/avg_raw_reward` from 0.2500 at step 1 to
  0.5625 at step 4 and stabilized at 0.5000 across steps 7-10 (`pass@8 = 1.0`).
  In the Tinker Cookbook Harbor RL recipe (`tinker_cookbook.recipes.harbor_rl`),
  grader pass rate similarly climbed from 20.0% at step 0 to 75.0%.

---
name: cortex-training-rl
description: >-
  Run reinforcement-learning post-training of a model inside the OpenHands
  agent harness on Snowflake Cortex Training, using the Arctic Platform
  OpenHands and Harbor recipes (SkyRL GRPO, CodeScout code localization,
  Harbor tasks), and generate the step-by-step reward convergence graph. Use
  when asked to launch, monitor, debug, stop, or plot an OpenHands or Harbor
  RL run on Cortex Training.
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

Two ready-to-run recipes ship in Arctic Platform:
1. **Harbor RL (`recipes/rl/harbor` + `arctic_platform/integrations/harbor`):**
   go directly from any [Harbor](https://github.com/laude-institute/harbor)
   training and evaluation task directories (`TRAIN_HARBOR_TASKS` and
   `EVAL_HARBOR_TASKS`, where each task has `instruction.md`, `environment/`,
   and `tests/test.sh`) and an optional OpenHands skill (`HARBOR_SKILL`) to RL
   post-training on Cortex Training, orchestrated by Harbor's `Trial` and
   `Verifier`.
2. **CodeScout code localization (`recipes/rl/openhands/code_localization`):**
   train Qwen3.5-4B to name the files, classes, and functions a bug touches,
   scored by F1 (maximum 3).

- Code localization recipe: [Arctic Platform `recipes/rl/openhands/code_localization`](https://github.com/Snowflake-AI-Research/Arctic-Platform/tree/main/recipes/rl/openhands/code_localization)
- Harbor RL recipe & integration: [Arctic Platform `recipes/rl/harbor` (PR #294)](https://github.com/Snowflake-AI-Research/Arctic-Platform/pull/294)
- Snowflake Cortex Sandboxes provider for Harbor: [Harbor `--env snowflake` (PR #3918)](https://github.com/harbor-framework/harbor/pull/3918)
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

**Option A - Harbor RL (`recipes/rl/harbor`):**

Point `TRAIN_HARBOR_TASKS` and `EVAL_HARBOR_TASKS` at any directories of Harbor
tasks (each containing `instruction.md`, `environment/`, and `tests/test.sh`),
or export the SWE-smith code localization tasks into Harbor `train/` and
`eval/` directories:

```bash
uv run recipes/rl/harbor/prepare_data.py \
  --export-swe-smith-to ~/data/swe-smith-harbor-tasks \
  --out ~/data/harbor-rl
```

(Or simply export `TRAIN_HARBOR_TASKS` and `EVAL_HARBOR_TASKS` when launching
`recipes/rl/harbor/run_qwen35_4b.sh`, which runs `prepare_data.py` automatically.)

**Option B - CodeScout code localization (`recipes/rl/openhands/code_localization`):**

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

**Launch Harbor RL training (`recipes/rl/harbor/run_qwen35_4b.sh`):**

```bash
export RUN_NAME=qwen35-4b-harbor-rl-$(date +%m%d-%H%M)
export CKPT_DIR=$HOME/checkpoints/$RUN_NAME
export TRAIN_HARBOR_TASKS=$HOME/data/swe-smith-harbor-tasks/train
export EVAL_HARBOR_TASKS=$HOME/data/swe-smith-harbor-tasks/eval
export HARBOR_SKILL=/path/to/SKILL.md   # optional OpenHands skill
export ARCTIC_CORTEX_JOB_COMMENT="<your name> harbor localization - ask before cancelling"
export LOGGER=console OPENHANDS_WORKSPACE=/path/with/space STARTUP_TIMEOUT=14400
mkdir -p "$CKPT_DIR"

tmux -L "$RUN_NAME" new-session -d -s train \
  "echo \$\$ > $CKPT_DIR/launcher.pid; exec env -u TMUX -u TMUX_PANE \
   bash recipes/rl/harbor/run_qwen35_4b.sh trainer.max_training_steps=100"
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

### 4. Monitor and recreate the reward graph

The log is `$CKPT_DIR/$RUN_NAME.log`, and the job id is in
`$CKPT_DIR/cortex_job_id`. Check the job, the per-step reward, the rollout
errors, and generate the reward convergence plot (per-step trace, 5-step
rolling mean, 10-step window means, and the CodeScout reference bars at `0.758`,
`2.30`, and `2.342`) as shown in [references/monitoring.md](references/monitoring.md).

Signs of a healthy run:

- The job is `running`.
- A new step lands every few minutes.
- On code localization (both with and without Harbor), the 10-step mean of
  `reward/avg_raw_reward` rises from about 0.35-0.40 in steps 1-10 to about
  1.4-1.5 in steps 11-20 and reaches the ~2.1-2.3 plateau by steps 21-30.
- `policy/grad_norm` stays bounded (~0.4-2.0).

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

## Harbor integration (`arctic_platform.integrations.harbor`) and custom harnesses

Both recipes are built on `arctic_platform.integrations.harness`
([`ChatCompletionsProxy` and `HarnessGenerator`](https://github.com/Snowflake-AI-Research/Arctic-Platform/tree/main/arctic_platform/integrations/harness)):

1. **Harbor Trial & Verifier integration (`arctic_platform.integrations.harbor`):**
   - `HarborTrialAdapter` (`arctic_platform/integrations/harbor/adapter.py`)
     implements the 3-method `HarnessAdapter` (`submit`, `get_status`,
     `collect_output`) by running Harbor's `Trial.create(trial_cfg)` and
     `trial.run()` pointed at `request.base_url` and `request.api_key`, and
     `grade_harbor` reads the task's `Verifier` output (`tests/test.sh` ->
     `/logs/verifier/reward.txt` or `reward.json`).
   - Swap the Harbor agent, OpenHands toolset/prompt, or sandbox environment via:
     - `HARBOR_AGENT`: any Harbor `BaseAgent` (default:
       `harbor_rl.agent:OpenHandsHarborAgent`, or Harbor's built-in
       `openhands-sdk`, `openhands`, `mini-swe-agent`, `swe-agent`, or any custom
       `module:AgentClass`).
     - `OPENHANDS_TOOLS` (e.g. `terminal,file_editor,task_tracker`),
       `OPENHANDS_SYSTEM_PROMPT_FILE`, and `HARBOR_SKILL` (one or more
       `:`-separated `SKILL.md` paths or directories) to customize the target
       OpenHands agent without writing a new class.
     - `HARBOR_ENV`: any Harbor `BaseEnvironment` (default:
       `arctic_platform.integrations.harbor.env:HostEnvironment`, or
       `arctic_platform.integrations.harbor.snowflake_sandbox:SnowflakeSandboxEnvironment`
       / `snowflake`, `docker`, `modal`, `daytona`).
2. **Custom controller and context compaction (`arctic_platform.integrations.harness`):**
   - `ChatCompletionsProxy` splices the exact sampled token IDs across turns
     (`loss_mask = 1` on assistant turns, `0` on prompts and tool output). A
     request that does not extend the prior messages (such as a compacted
     history) starts a new chain. Set `generator.step_wise_trajectories=true`
     so every chain becomes a training row under the same `trajectory_id`. To
     avoid training on the LLM call that writes a compaction summary, send the
     summarization call to the un-routed `${proxy.base_url}/v1/chat/completions`
     endpoint; send it to `request.base_url` if you want the summary call itself
     trained on.
3. **Tinker Cookbook Harbor RL (`arctic_platform.integrations.tinker`):**
   - To run `tinker-cookbook` recipes (including `tinker_cookbook.recipes.harbor_rl.train`
     with a custom `SandboxFactory` such as Modal or `snowflake.sandbox.AsyncSandbox`)
     on Cortex Training without a local GPU driver, run
     `python -m arctic_platform.integrations.tinker.run --training-gpus 4 --sampling-gpus 4 <module> [args...]`.
     See [`docs/integrations/tinker.md`](https://github.com/snowflakedb/cortex-training/blob/main/docs/integrations/tinker.md).

## Reference result

- **Code localization without Harbor (`recipes/rl/openhands/code_localization`):**
  On 4 training plus 4 sampling H200s, 100 steps of 8 prompts x 8 rollouts gave
  10-step means of `reward/avg_raw_reward`: 0.39 for steps 1-10, 1.39 for steps
  11-20, 2.28 for steps 21-30, and 2.28 for steps 91-100 (matching the CodeScout
  reference curve near 2.3).
- **Code localization with Harbor (`recipes/rl/harbor`):**
  Running the exact same SWE-smith code localization task through Harbor's `Trial`
  and `Verifier` (`tests/test.sh` F1 grading) on 4 training plus 4 sampling H200s
  matched the non-Harbor curve step-for-step across 25 steps (1,600 Harbor trials on
  200 unique tasks, 0 errors): 10-step mean of 0.35 for steps 1-10 (0.78 at step 10),
  1.46 for steps 11-20 (2.03 at step 16, 2.10 at step 19), and climbing to 2.13 at
  step 21 and 2.10 at step 24 (`pass@8 = 0.88-1.00`).

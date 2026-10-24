---
name: cortex-training-rl
description: >-
  Run reinforcement-learning post-training of a model inside the OpenHands
  agent harness or a custom Harbor controller on Snowflake Cortex Training,
  using the Arctic Platform OpenHands recipe and harness endpoint (SkyRL GRPO,
  CodeScout code localization, Harbor tasks). Use when asked to launch,
  monitor, debug, or stop an OpenHands or Harbor RL run on Cortex Training.
triggers:
- cortex training
- cortex-training
- arctic platform
- arctic-platform
- codescout
---

# OpenHands RL post-training on Cortex Training

The trainer and the sampler run on Cortex Training GPUs. Your machine runs a
CPU-only driver that executes OpenHands conversations against the sampler and
sends the scored episodes back for a policy update. The reference task is
CodeScout code localization: Qwen3.5-4B learns to name the files, classes, and
functions a bug touches, scored by F1 (maximum 3).

- Recipe: [Arctic Platform `recipes/rl/openhands/code_localization`](https://github.com/Snowflake-AI-Research/Arctic-Platform/tree/main/recipes/rl/openhands/code_localization)
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
rollout holds one clone of its task repository.

### 2. Install and data

Follow the recipe README: `uv`, SkyRL at tag `skyrl-v0.3.0` as `SKYRL_HOME`,
and the Arctic Platform checkout (`main`). From the Arctic Platform checkout,
download the dataset and write `train.parquet` and `validation.parquet` into
`~/data/swe-smith-localization` (or pass `--out DIR` and set `DATA_DIR=DIR`):

```bash
uv run recipes/rl/openhands/code_localization/prepare_data.py
```

The launcher refuses to start when any of these is missing and prints what to
fix.

### 3. Launch detached

The run takes hours, so it must survive the shell closing. Launch it in
detached tmux on a socket named after the run, with `TMUX` and `TMUX_PANE`
removed. OpenHands drives its terminal tool through `libtmux`, which follows
`TMUX` to whatever server the launcher sits in. If the variables leak, the
rollouts create and kill sessions on the launcher's own server.

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
- The 10-step mean of `reward/avg_raw_reward` rises from about 0.4 to about
  2.3 by steps 21-30.
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

## Custom Harbor tasks, controllers, and other Cortex Training paths

The OpenHands recipe is built on `arctic_platform.integrations.harness`
([`ChatCompletionsProxy` and `HarnessGenerator`](https://github.com/Snowflake-AI-Research/Arctic-Platform/tree/main/arctic_platform/integrations/harness)),
which is harness-agnostic:

1. **Custom controller or Harbor tasks (`arctic_platform.integrations.harness`):**
   - Implement the 3-method `HarnessAdapter` (`submit(request) -> rollout_id`,
     `get_status(rollout_id)`, `collect_output(rollout_id) -> artifacts`) in
     place of `OpenHandsAdapter`, and point your agent or Harbor runner (`harbor run`
     with `--env docker`, `--env modal`, or Snowflake Cortex Sandboxes via
     `harbor_snowflake_sandbox:SnowflakeSandboxEnvironment`) at
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

On 4 training plus 4 sampling H200s, 100 steps of 8 prompts x 8 rollouts gave
these 10-step means of `reward/avg_raw_reward`: 0.39 for steps 1-10, 2.28 for
steps 21-30, and 2.28 for steps 91-100. The CodeScout reference curve sits
near 2.3 from step 21 on.

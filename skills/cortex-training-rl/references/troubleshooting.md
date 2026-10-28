# Troubleshooting an OpenHands RL run on Cortex Training

Each entry below is a failure seen on real runs. Find the cause with
[monitoring.md](monitoring.md) first, then match the symptom. Before you
cancel or relaunch anything, check that the job's `comment` is yours.

## `LibTmuxException: new-session: create window failed: fork failed: No space left on device`

Every rollout in a step fails with this, even with free disk space.

**Cause:** the machine ran out of ptys, not disk. Each OpenHands terminal is a
tmux session named `openhands-<id>` and holds a pty. A driver that was
killed, or whose worker processes were orphaned, leaves its sessions behind.
Thousands of leftover sessions exhaust `/proc/sys/kernel/pty/max`.

**Fix:** stop the run as described in the skill. Once no run is live, clear
the leftovers and check that the count has dropped:

```bash
tmux ls -F '#{session_name}' 2>/dev/null | grep '^openhands-' | xargs -r -n1 tmux kill-session -t
cat /proc/sys/kernel/pty/nr /proc/sys/kernel/pty/max
```

Check that no driver processes from the old run survived
(`pgrep -af 'skyrl.train|openhands_localization'`), then relaunch.

## `fatal: fetch-pack: invalid index-pack output` or `fatal: error writing to <workspace>/...`

Most rollouts in a step fail while cloning, and `df` shows the
`OPENHANDS_WORKSPACE` disk at or near 100%.

**Cause:** every rollout clones its task repository under
`$OPENHANDS_WORKSPACE/<id>/`. The current recipe deletes each clone when its
conversation ends. A run killed mid-step, or an older revision of the recipe,
leaves clones behind, and a few hundred steps of them fill a large disk.

**Fix:** free space without touching in-flight rollouts. A rollout lasts well
under an hour, so directories older than that are leftovers:

```bash
find "$OPENHANDS_WORKSPACE" -mindepth 1 -maxdepth 1 -type d -mmin +60 -exec rm -rf {} +
df -h "$OPENHANDS_WORKSPACE"
```

A step that failed this way contributes little to the update, and a run can
continue past it. Restart only if the reward stays down afterwards.

## The run dies as soon as the first rollouts start

The launcher's tmux session exits, or your own tmux sessions disappear, the
moment step 1 begins.

**Cause:** the launcher ran inside tmux with `TMUX` and `TMUX_PANE` set.
OpenHands drives its terminal tool through `libtmux`, which follows `TMUX` to
the launcher's tmux server and creates and kills sessions there.

**Fix:** cancel the job if it is still alive, then launch on a dedicated
socket with `env -u TMUX -u TMUX_PANE`, as shown in the skill.

## Closing the shell or the SSH session stops the run

**Cause:** the launcher was a child of the interactive shell.

**Fix:** launch inside a detached tmux session, as shown in the skill. Then
check whether the old job is still `running` and cancel it.

## The driver is gone, but the job is still `running`

**Cause:** the launcher cancels the job from its exit trap. `SIGKILL`, an OOM
kill, or a machine reboot skips that trap. The job keeps its 8 GPUs until it is
cancelled.

**Fix:**

```bash
cortex-training get "$(cat "$CKPT_DIR/cortex_job_id")"     # confirm the comment is yours
cortex-training cancel "$(cat "$CKPT_DIR/cortex_job_id")"
```

Always stop a run with Ctrl-C or `SIGTERM`, never `kill -9`. To stop a run
from a script, cancel the job first and then signal the launcher's process
group.

## Launching a second run broke the first

**Cause:** two runs on one machine share the tmux server, the pty pool, and the
workspace disk. Two runs with the same `RUN_NAME` also share
`$CKPT_DIR/cortex_job_id`, so the first job's id is overwritten and its
release path is lost.

**Fix:** run one job per driver machine, give every run a unique `RUN_NAME`,
and run `cortex-training list --status running` before each launch. If the
first job's id file was overwritten, find the job by its `comment` in that
listing.

## The job stays `pending` or `placing`, and the launcher exits with a startup timeout

**Cause:** the account has fewer than 8 free GPUs of the requested hardware.
The launcher waits `STARTUP_TIMEOUT` seconds (default 3600) and then
cancels its own job.

**Fix:** run `cortex-training capacity --hardware H200`. Then wait for capacity
or raise `STARTUP_TIMEOUT`. Do not cancel other people's jobs to make room.

## The launcher refuses to start

The script checks its inputs before creating a job and prints the fix:
- `uv` is missing.
- `SKYRL_HOME` is unset or lacks `integrations/arctic_rl`.
- A parquet file is missing.
- There is no Cortex login.
- The batch would exceed the 128 MiB response cap.
- A cached wheel shadows the checkout.

Follow the message. Do not shrink the batch or the context to get past the
response-cap check, because that changes the experiment.

## A few `ContextWindowExceeded` errors every step

This is expected. Some conversations outgrow the 32768-token context before
the agent submits. Those rollouts drop out of the loss. Investigate only if
they become most of a batch.

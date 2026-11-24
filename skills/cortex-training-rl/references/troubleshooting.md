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

## The Harbor launcher exits with `ERROR: task <name> failed on SnowflakeSandboxEnvironment`

The launcher ran the first training task in a sandbox before provisioning GPUs,
and it failed. No Cortex job was created. The lines after the error name the
cause:
- `GitHub egress is not configured for this sandbox`: the task clones from
  GitHub, and `egress_eai` is missing or doesn't allow `github.com`. Ask your
  account administrator for an external access integration that does.
- `Dockerfile RUN failed` on `apt-get`: `sandbox-base` is Chainguard Linux,
  which has `apk` and no `apt-get`. Make the step work there, for example by
  skipping packages the image already has (Python 3.11, pip, git).
- `... is not supported` (for example `COPY --from (multi-stage) is not supported`):
  replay handles one `FROM` stage. It refuses `RUN` flags, `COPY --from`, `ADD`
  from a URL or of an archive, and `SHELL`.
- `ImageMirrorError` (often `HTTP 444: source IP address not allowed`): with
  `image_repo`, the registry rejected a push from this machine's network. Use
  `base_image`, or run the driver from a network the registry accepts.

## Every Harbor rollout of a step errors in the middle of a run

Each rollout leaves a `.error` file instead of a `.json` under
`$CKPT_DIR/trajectories/step_N/train/`. After three reruns spread over 7
minutes, the run stops with `Every train rollout at step N errored in 4 attempts`.

**Cause:** the sandboxes failed for longer than the reruns cover, for example
during a sandbox service outage. The first error in the message says why.

**Fix:** relaunch once the cause is gone. The launcher's first-task check
tells you within a minute whether sandboxes work again.

## Snowflake rollouts fail with `SandboxRateLimitError` or `Your session has expired`

A growing share of each step's rollouts are `.error` files showing
`SandboxRateLimitError: rate-limited after 4 retries`, or
`create returned no container id: {'code': '390112', 'message': 'Your session has expired. ...'}`
starting about an hour into the run.

**Cause:** Snowflake allows 100 live sandboxes per owner, and suspended ones
count. Sandboxes left behind by a killed run, or by other work on the same
connection, use up that quota. Arctic Platform revisions before the session
renewal fix also let the shared session expire after about an hour, and leaked a
sandbox whenever a create failed partway.

**Fix:** update Arctic Platform. Then, when no other run uses the connection,
terminate what earlier runs left behind:

```bash
uv run --extra harbor python -c "
from snowflake.sandbox import Sandbox
for s in Sandbox.list(connection='MY_CONN'):
    if s.status in ('ready', 'pending') and (s.name or '').startswith('harbor-rl-'):
        s.terminate()"
```

Sandboxes from older revisions have generated names. Find them by their
`harbor_session` tag or creation time in `Sandbox.list()` before terminating.

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
cortex-training list | jq -r --arg c "$ARCTIC_CORTEX_JOB_COMMENT" \
  '.jobs[] | select(.comment == $c) | "\(.job_id) \(.status)"'
cortex-training cancel <job_id>   # only a job whose comment is yours
```

Always stop a run with Ctrl-C or `SIGTERM`, never `kill -9`. To stop a run
from a script, cancel the job first and then signal the launcher's process
group.

## Launching a second run broke the first

**Cause:** two runs on one machine share the tmux server, the pty pool, and the
workspace disk. Two runs with the same `RUN_NAME` also write to the same
`$CKPT_DIR`.

**Fix:** run one job per driver machine, give every run a unique `RUN_NAME`
and `ARCTIC_CORTEX_JOB_COMMENT`, and run `cortex-training list --status running`
before each launch.

## The job stays `pending` or `placing`, and the launcher exits with a startup timeout

**Cause:** the account has fewer than 8 free GPUs of the requested hardware.
The launcher waits `STARTUP_TIMEOUT` seconds (default 3600) and then
cancels its own job.

**Fix:** run `cortex-training capacity` and compare `available_gpus` with 8. Then wait for capacity
or raise `STARTUP_TIMEOUT`. Do not cancel other people's jobs to make room.

## The launcher refuses to start

The script checks its inputs before creating a job and prints the fix:
- `uv` is missing.
- `SKYRL_HOME` is unset or lacks `integrations/arctic_rl`.
- A parquet file is missing.
- `ARCTIC_CORTEX_HOST`, `_DATABASE`, `_SCHEMA`, or `_PAT` is not exported. `cortex-training login` alone is not enough.
- `HARBOR_ENV=snowflake` has no `base_image` (or `image_repo`, or sandbox-path `prebuilt_image`).
- The first training task fails in its sandbox (see `ERROR: task <name> failed on SnowflakeSandboxEnvironment` above).
- The batch would exceed the 128 MiB response cap.
- A cached wheel shadows the checkout.

Follow the message. Do not shrink the batch or the context to get past the
response-cap check, because that changes the experiment.

## A few `ContextWindowExceeded` errors every step

This is expected. Some conversations outgrow the 32768-token context before
the agent submits. Those rollouts drop out of the loss. Investigate only if
they become most of a batch.

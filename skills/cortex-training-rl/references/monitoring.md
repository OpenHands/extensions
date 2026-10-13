# Monitoring an OpenHands RL run on Cortex Training

All paths assume the `RUN_NAME` and `CKPT_DIR` you launched with.

## Job state

```bash
cortex-training get "$(cat "$CKPT_DIR/cortex_job_id")"
```

States are `pending` and `placing` (waiting for GPUs), `initializing`
(loading the model), `running`, and the terminal states `cancelled`,
`terminated`, and `failed`. A `failed` job carries a `reason`.

## Per-step reward

The log is colored, so strip ANSI codes first. Every step prints one metrics
dictionary that contains `'reward/avg_raw_reward': '<value>'`.

```bash
sed 's/\x1b\[[0-9;]*m//g' "$CKPT_DIR/$RUN_NAME.log" \
  | grep -oE "'reward/avg_raw_reward': '[0-9.]+'" | grep -oE "[0-9.]+" \
  | awk '{s += $1; n++; if (n % 10 == 0) { printf "steps %d-%d: mean %.3f\n", n - 9, n, s / 10; s = 0 }}
         END { print n " steps, last " $1 }'
```

Use 10-step means. Single steps are noisy because each batch holds only 8
prompts. The reference run gave 10-step means of 0.39, 1.39, 2.28, 2.39, 2.42,
2.51, 2.46, 2.29, 2.34, and 2.28.

The same dictionary carries `'policy/grad_norm'` (should stay under 1) and
`'timing/generate'` (seconds spent running rollouts in that step). If
`timing/generate` drops to a few seconds while the reward drops to 0, the
rollouts are failing before the model is called.

## Rollout errors

Each failed rollout leaves a traceback at
`$CKPT_DIR/trajectories/step_<N>/train/<instance>_<k>.error`, next to the
`.json` files of the rollouts that succeeded. Count the causes by step:

```bash
for d in "$CKPT_DIR"/trajectories/step_*/train; do
  n=$(ls "$d"/*.error 2>/dev/null | wc -l)
  [ "$n" -gt 0 ] && echo "$(basename "$(dirname "$d")"): $n errors"
done
for p in ContextWindowExceeded "No space left on device" "fetch-pack: invalid index-pack" LibTmuxException; do
  printf '%5d  %s\n' "$(grep -lE "$p" "$CKPT_DIR"/trajectories/step_*/train/*.error 2>/dev/null | wc -l)" "$p"
done
```

The second loop counts files, one per failed rollout. A batch is 64
rollouts. Up to about 10 `ContextWindowExceeded` errors in one step are
normal. The reference run lost 83 of 6400 rollouts that way and no more than
11 in a single step. Any other cause, or a step where most rollouts fail, goes
to [troubleshooting.md](troubleshooting.md).

The agent's own tool output can contain the word `Traceback`, because the
agent runs code in the task repository. Read the `.error` files, not
`Traceback` matches in the log.

## Machine health during a run

```bash
cat /proc/sys/kernel/pty/nr                 # ptys in use; should track in-flight rollouts
tmux ls 2>/dev/null | grep -c '^openhands-' # one session per in-flight rollout
df -h "$OPENHANDS_WORKSPACE"                # clones are removed when each rollout ends
```

A pty count or session count that keeps climbing across steps, or a
workspace that keeps filling up, means rollouts are leaking resources. Fix
it before it fails a whole batch.

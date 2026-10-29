# Monitoring an OpenHands RL run and recreating the reward graph

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
prompts. The reference run without Harbor gave 10-step means of 0.39, 1.39,
2.28, 2.39, 2.42, 2.51, 2.46, 2.29, 2.34, and 2.28; the Harbor run gave 0.35
for steps 1-10, 1.46 for steps 11-20, and reached 2.13 at step 21 and 2.10 at
step 24.

The same dictionary carries `'policy/grad_norm'` (should stay under 1-2) and
`'timing/generate'` (seconds spent running rollouts in that step). If
`timing/generate` drops to a few seconds while the reward drops to 0, the
rollouts are failing before the model is called.

## Recreate the reward graph (with and without Harbor)

Run this self-contained Python snippet to parse one or more training logs (e.g.,
without Harbor `recipes/rl/openhands/code_localization` and with Harbor
`recipes/rl/harbor`), print the 10-step summary table, and write a standalone
SVG/HTML reward graph (`$CKPT_DIR/reward_graph.svg` and
`$CKPT_DIR/reward_graph.html`) showing the per-step trace, 5-step rolling mean,
and the CodeScout reference bars (`0.758` on steps 1-10, `2.30` on steps 21-30,
`2.342` on steps 91-100):

```bash
python3 - "$CKPT_DIR/$RUN_NAME.log" "$CKPT_DIR/reward_graph.svg" <<'PY'
import pathlib, re, sys

log_path = pathlib.Path(sys.argv[1])
out_svg = pathlib.Path(sys.argv[2])
clean = re.sub(r"\x1b\[[0-9;]*m", "", log_path.read_text(errors="ignore"))
rewards = [float(x) for x in re.findall(r"'reward/avg_raw_reward':\s*'([0-9.]+)'", clean)]
if not rewards:
    raise SystemExit(f"No steps found in {log_path}")

mean5 = [sum(rewards[max(0, i - 4):i + 1]) / len(rewards[max(0, i - 4):i + 1]) for i in range(len(rewards))]
for start in range(0, len(rewards), 10):
    chunk = rewards[start:start + 10]
    print(f"steps {start + 1:3d}-{start + len(chunk):3d}: mean {sum(chunk) / len(chunk):.4f} (max {max(chunk):.4f})")

W, H, padL, padR, padT, padB = 860, 360, 48, 28, 28, 42
plotW, plotH = W - padL - padR, H - padT - padB
max_step = max(len(rewards), 25)
y_max = 3.0 if max(rewards) > 1.0 else 1.0
y_ticks = (0, 1, 2, 3) if y_max == 3.0 else (0.0, 0.25, 0.5, 0.75, 1.0)
x = lambda s: padL + ((s - 1) / max(max_step - 1, 1)) * plotW
y = lambda v: padT + (1.0 - min(max(v, 0.0), y_max) / y_max) * plotH
pts = lambda arr: " ".join(f"{x(i + 1):.1f},{y(v):.1f}" for i, v in enumerate(arr))

ref_lines = (
    [
        f'<line x1="{x(1):.1f}" x2="{x(min(10, max_step)):.1f}" y1="{y(0.758):.1f}" y2="{y(0.758):.1f}" stroke="#e06c75" stroke-width="4" stroke-linecap="round"/>',
        f'<line x1="{x(min(21, max_step)):.1f}" x2="{x(min(30, max_step)):.1f}" y1="{y(2.3):.1f}" y2="{y(2.3):.1f}" stroke="#e06c75" stroke-width="4" stroke-linecap="round"/>',
    ]
    if y_max == 3.0
    else []
)
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="background:#0f1115;font-family:sans-serif">',
    *[f'<line x1="{padL}" x2="{W-padR}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#262930"/><text x="{padL-8}" y="{y(v)+4:.1f}" fill="#9ca3af" font-size="11" text-anchor="end">{v}</text>' for v in y_ticks],
    *ref_lines,
    f'<polyline fill="none" stroke="#61afef" stroke-opacity="0.4" stroke-width="1.2" points="{pts(rewards)}"/>',
    f'<polyline fill="none" stroke="#61afef" stroke-width="2.8" points="{pts(mean5)}"/>',
    *[f'<circle cx="{x(i+1):.1f}" cy="{y(v):.1f}" r="3" fill="#61afef"/>' for i, v in enumerate(rewards)],
    "</svg>",
]
out_svg.write_text("\n".join(svg), encoding="utf-8")
print(f"Wrote {out_svg} ({len(rewards)} steps, last={rewards[-1]:.4f}, 5-step mean={mean5[-1]:.4f})")
PY
```

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

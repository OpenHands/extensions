# cortex-training-rl

Runs reinforcement-learning post-training of a model inside the OpenHands
harness on Snowflake Cortex Training, using the Arctic Platform OpenHands
recipes:
- **Harbor tasks (`recipes/rl/openhands/harbor`):** go directly from any Harbor
  task directory (such as Terminal-Bench 2.0) to RL post-training of an
  OpenHands agent graded by `tests/test.sh`.
- **CodeScout code localization (`recipes/rl/openhands/code_localization`):**
  train Qwen3.5-4B on SWE-smith code localization scored by F1.

The skill covers:
- a preflight of capacity, live runs, ptys, and disk
- preparing data from a Harbor tasks directory or SWE-smith
- a detached launch that survives the shell closing
- reward and rollout-error monitoring
- a clean stop that releases the GPUs

The [troubleshooting reference](references/troubleshooting.md) lists the
failures seen on real runs with their fixes.

See: [SKILL.md](./SKILL.md)

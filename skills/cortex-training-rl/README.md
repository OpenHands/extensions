# cortex-training-rl

Runs reinforcement-learning post-training of a model inside the OpenHands
harness or a custom Harbor controller on Snowflake Cortex Training, using the
Arctic Platform OpenHands recipe and harness endpoint. The reference task is
CodeScout code localization with Qwen3.5-4B.

The skill covers:
- a preflight of capacity, live runs, ptys, and disk
- a detached launch that survives the shell closing
- reward and rollout-error monitoring
- a clean stop that releases the GPUs
- wiring custom Harbor tasks, controllers, context compaction, and `tinker-cookbook` recipes on Cortex Training

The [troubleshooting reference](references/troubleshooting.md) lists the
failures seen on real runs with their fixes.

See: [SKILL.md](./SKILL.md)

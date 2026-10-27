# cortex-training-rl

Runs reinforcement-learning post-training of a model inside the OpenHands
harness on Snowflake Cortex Training, using the Arctic Platform OpenHands and
Harbor recipes:
- **Harbor RL (`recipes/rl/harbor` + `arctic_platform/integrations/harbor`):**
  go directly from any Harbor training and evaluation task directories
  (`TRAIN_HARBOR_TASKS` and `EVAL_HARBOR_TASKS`) and an optional OpenHands
  skill (`HARBOR_SKILL`) to RL post-training on Cortex Training, orchestrated
  by Harbor's `Trial` and `Verifier` (`tests/test.sh`).
- **CodeScout code localization (`recipes/rl/openhands/code_localization`):**
  train Qwen3.5-4B on SWE-smith code localization scored by F1.

The skill covers:
- a preflight of capacity, live runs, ptys, and disk
- preparing data from Harbor task directories (`TRAIN_HARBOR_TASKS` / `EVAL_HARBOR_TASKS`) or SWE-smith
- a detached launch that survives the shell closing
- reward and rollout-error monitoring plus recreating the reward convergence graph (`reward_graph.svg`)
- a clean stop that releases the GPUs

The [troubleshooting reference](references/troubleshooting.md) lists the
failures seen on real runs with their fixes.

See: [SKILL.md](./SKILL.md)

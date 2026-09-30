# GitHub stale CI pull request closer

This extension runs a deterministic scheduled maintenance pass over configured
GitHub repositories. It warns after seven days of continuously failing required
CI and closes after another seven days without author follow-up. Optional checks
do not affect the decision, and no LLM slot is used.

Conversation and review automation state are unaffected. Warning and closure
comments carry stable markers so retries remain idempotent.

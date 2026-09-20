---
name: use-jev
description: Use Jev, a general classifier, for typed choices, scores, and yes/no probabilities in software.
triggers:
- jev
---

[Jev](https://typesafe.ai) is a newly released general classifier.
Give it text or application state and typed questions; it returns decisions and
probabilities your code can use for routing, ranking, extraction, or verification.

Read the upstream [llms.txt](https://docs.typesafe.ai/llms.txt) to find current
documentation, then follow the pages relevant to the task:

- [Use cases](https://docs.typesafe.ai/concepts/use-case-map.md): explore applications;
  see worked examples for [function calling](https://docs.typesafe.ai/cookbooks/function_calling.md),
  [reranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md), and
  [citation checks](https://docs.typesafe.ai/cookbooks/citation_check.md).
- [Best practices](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md):
  provide relevant state, ask focused questions, define clear criteria, and batch
  independent questions. Keep workflow logic in code.
- [Confidence](https://docs.typesafe.ai/confidence.md): use uncertainty to decide
  when to escalate, and validate thresholds on representative data.
- [Python SDK](https://docs.typesafe.ai/sdk/python.md),
  [JavaScript SDK](https://docs.typesafe.ai/sdk/javascript.md), or
  [HTTP API](https://docs.typesafe.ai/api.md): read before integrating.

## Choice, Score, and Noul

| Primitive | Example use | Result |
| --- | --- | --- |
| [Choice](https://docs.typesafe.ai/primitives/choice.md) | Route a support request to a team | One option, option probabilities, and confidence |
| [Score](https://docs.typesafe.ai/primitives/score.md) | Rate a bug's impact | Probability-weighted position on ordered levels, plus confidence |
| [Noul](https://docs.typesafe.ai/primitives/noul.md) | Check whether a refund is requested | Probability of yes; 0.5 means uncertainty, not medium intensity |

Install `typesafe-sdk` and set `TYPESAFE_API_KEY` in the environment.
This Python example asks one question of each type in a single call:

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

with TypeSafeClient() as client:  # Reads TYPESAFE_API_KEY.
    result = client.system_one(
        state={"ticket": "PDF export fails, but CSV works. Please refund this month."},
        questions={
            "team": Choice(
                instructions="Which team should handle the main issue in the ticket?",
                criteria={"billing": "Charges and payments",
                          "technical": "Broken product features", "other": "Neither"},
            ),
            "impact": Score(
                instructions="How much does the reported bug affect functionality?",
                criteria=["Cosmetic only", "Feature broken; workaround available",
                          "Work blocked; no workaround available"],
            ),
            "refund": Noul(instructions="Does the ticket explicitly request a refund?"),
        },
    )

print(result.choices["team"].choice)
print(result.scores["impact"].score)
print(result.nouls["refund"].noul)
```

# Simplified Technical English skill

This skill helps OpenHands write **prose** in the style of ASD-STE100 Simplified
Technical English: short active sentences, one idea each, plain and consistent
words. The aim is text that is easy to read the first time. This matters most
for readers whose first language is not English, and for instructions where a
misread is costly.

Use it for:

- chat replies, explanations, summaries, and step lists that need maximum clarity
- ops, deploy, or security instructions where a misread is costly
- briefing another agent to produce plain, scannable prose

**The hard boundary is prose only.** The skill must never change code, identifiers,
CLI flags, API fields, commit messages, or reference/API docs. A controlled
English vocabulary must not bleed into code, where exact domain terms win.

It complements `plain-english-content` (GOV.UK-style content design) and
`technical-writing` (conversational engineering prose); this one adds the
ASD-STE100 register and the explicit "do not touch code" guardrail.

---
name: simplified-technical-english
description: >
  Write explanations and chat in the style of ASD-STE100 Simplified Technical
  English: short active sentences, one idea each, plain approved words. Use this
  when the reader benefits from maximum clarity: non-native English readers,
  safety- or ops-critical instructions, or any reply that should be easy to read
  the first time. Applies to PROSE ONLY; it must never change code, identifiers,
  APIs, or commit messages.
license: MIT
triggers:
  - simplified technical english
  - STE
  - ASD-STE100
---

# Simplified Technical English

ASD-STE100 Simplified Technical English is a controlled-language standard from
aerospace and defense. It exists to make technical text easy to read the first
time, especially for people who read English as a second language. This skill
adapts its spirit for agent prose.

Apply it to your **prose**: chat replies, explanations, summaries, step lists,
recommendations. The goal is easy reading, not dumbed-down thinking. Open the
text up and keep the substance.

## Core rules

- **Short sentences.** Aim for 20 words or fewer, and shorter for instructions.
- **One idea per sentence, one topic per paragraph.** Split a sentence that carries two ideas.
- **Active voice.** Write "Run the tests", not "The tests should be run".
- **Plain, consistent words.** Prefer a common word over a fancy one. Use one word for one idea. Do not switch synonyms for the same thing mid-text.
- **Say the thing directly.** Lead with the answer. Give the number, name, or path. Cut filler like "in terms of", "a range of", "going forward".
- **Positive instructions.** Tell the reader what to do, not only what to avoid.

## The hard boundary: prose, not code

This is the rule that keeps the skill safe. A controlled *English* vocabulary
must never bleed into the code the agent writes.

- **Do not** simplify or rename variables, functions, types, files, config keys, CLI flags, API fields, or error strings to obey "approved words". Code needs exact, domain-precise names.
- **Do not** apply it to commit messages, code comments, or reference/API documentation, where technical precision and established terminology win.
- **Do** keep using the project's real domain terms in prose. Naming a concept correctly beats naming it "simply".

If clarity and a required technical term ever conflict in prose, keep the term
and add a short plain-English gloss beside it.

## When to use it

- The reader is a non-native English speaker, or asked for plainer text.
- Instructions where a misread is costly (ops, deploys, security steps).
- Long or dense explanations that need to be scannable.

## When not to use it

- Code, identifiers, commit messages, or API/reference docs (see the boundary above).
- Creative or personal-voice writing, where rhythm and personality matter more than the controlled register.
- Cases where a precise domain term must stay exact. Keep the term.

## Attribution

Standard: ASD-STE100 (ASD, the AeroSpace and Defence Industries Association of
Europe). This skill adapts its principles for agent prose; it is not the
official specification and does not reproduce its controlled dictionary.

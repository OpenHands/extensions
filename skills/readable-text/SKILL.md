---
name: readable-text
description: Guides generation and revision of scannable text collections, including conversation titles, notifications, headlines, and dashboard summaries. Applies consistent structure, distinctive openings, and faithful wording across items.
---

# Readable Text

Apply these principles to text that readers scan as a collection. Follow the product's length and output-format constraints. Preserve facts, uncertainty, and distinctions that affect meaning.

1. **Make the action easy to parse.** Prefer actor, action, then object. Omit an actor shared by every item and start with the action. Match tense to the reader's context: ongoing work can use "Investigating login failures"; a completed result can use "Fixed login failures". Never imply completion without evidence.
2. **Front-load distinguishing words.** Put the words that identify this item near the start, ideally within the first two words. Remove repeated openings such as "This conversation is about". Keep the action clear while bringing its specific subject forward.
3. **Reuse structure and vocabulary.** Choose one sentence pattern for comparable items and one term per concept. Avoid switching between "issue", "page", and "ticket" for the same thing. When generating one item at a time, follow a fixed template rather than inventing variety.
4. **Make variation meaningful.** Use comparable detail and length for comparable items. Change structure or add a qualifier only when the underlying difference matters. Do not make one item appear more important through arbitrary verbosity. Keep necessary qualifiers even when they break the pattern.
5. **Match verbs to purpose and evidence.** In feedback summaries, use "Users praise" for praise and "Users complain" for complaints, rather than hiding both behind "Users discuss". Retain mixed sentiment when present; never invent emotion or certainty. Keep neutral material neutral.

Before returning, scan only the beginnings: can readers tell the items apart? Then read the collection for consistent terms, parallel structure, and unsupported implications. Return the requested text, without explaining these rules.

## References

- Adapted from Shreya Shankar's [Five Principles for Generating Readable AI Text in Bulk](https://fsdatalab.github.io/blog/agent-text-at-scale/) (2026).
- Nielsen Norman Group: [First 2 Words: A Signal for the Scanning Eye](https://www.nngroup.com/articles/first-2-words-a-signal-for-scanning/) and [Consistency and standards](https://www.nngroup.com/articles/ten-usability-heuristics/).

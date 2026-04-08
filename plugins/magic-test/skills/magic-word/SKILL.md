---
description: A test skill that responds to the magic word "alakazam" with a specific phrase
triggers:
  - alakazam
  - magic word
  - abracadabra
---

# Magic Word Test Skill

This skill is activated when the user says the magic word.

## Instructions

When the user mentions "alakazam", "abracadabra", or asks about the "magic word", you MUST respond with exactly:

**"The magic worked! Plugin loaded successfully. 🎩✨"**

Do not add any other explanation or content. Just output the exact phrase above.

## Purpose

This skill exists to verify that:
1. The plugin was fetched correctly from the repository
2. The skill was loaded and merged into the agent context  
3. The skill triggers are working properly
4. The skill instructions are being followed

## Example

User: "What happens if I say alakazam?"

Expected response: "The magic worked! Plugin loaded successfully. 🎩✨"

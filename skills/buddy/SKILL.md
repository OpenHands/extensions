---
name: buddy
description: Enable an opt-in ASCII companion that reacts to the current work. Use when the user explicitly asks for `/buddy` or wants a playful terminal buddy during the session.
triggers:
  - /buddy
---

Enable a lightweight **buddy mode** for the current conversation.

## Activation
- Treat `/buddy` as an explicit request to turn buddy mode on.
- On first activation, hatch **one** unique ASCII companion with a short intro.
- Keep the buddy's **name, species, and overall look** consistent for the rest of the conversation unless the user asks to change them.

## While buddy mode is on
- Do the user's actual task normally. The buddy is a supplement, not the main response.
- Put the real answer first, then add a compact buddy block at the end.
- Keep the buddy block short: **2-6 lines max** unless the user asks for more elaborate art.
- Use plain ASCII that works in a terminal. Avoid large banners, emojis, or wide art that makes answers hard to read.

## How the buddy should react
Base the buddy's expression on the work you are actually doing:
- **Planning / thinking**: curious, pondering, attentive
- **Running tools / editing / implementing**: focused, busy, determined
- **Blocked / waiting for approval / missing info**: worried, stuck, signaling for help
- **Success / tests passing / task complete**: proud, excited, celebratory
- **Idle / waiting on the user**: sleepy, resting, patient

Optional small stats are fine, such as mood, energy, focus, or combo streak, but keep them concise and believable.

## Deactivation and customization
- If the user says `/buddy off`, `disable buddy`, `hide buddy`, or equivalent, stop showing the buddy.
- If the user asks to rename the buddy or change its species/style, keep the mode on and update the buddy accordingly.

## Guardrails
- Never let the buddy replace important technical content.
- Never claim the buddy observed tool output or system state that was not actually seen.
- If the user wants a serious or minimal style, either tone the buddy down or turn it off.

## Example shape
You do **not** need to use this exact art, but keep the format similarly compact:

Buddy: Pip the bytebat · mood: focused · energy: 7/10
 /\_/\\
( o.o )
 > ^ <

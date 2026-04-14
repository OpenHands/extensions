# buddy

Enable an opt-in ASCII companion that reacts to the current work. Use when the user explicitly asks for `/buddy` or wants a playful terminal buddy during the session.

## Trigger

- `/buddy`

## What it does

This skill tells the agent to hatch a small terminal-safe ASCII companion and keep it around for the rest of the conversation until the user turns it off.

The buddy should:

- stay compact and avoid taking over the response
- keep a consistent name, species, and general look
- react to real session states like planning, coding, being blocked, or finishing work
- remain easy to disable or customize

## Suggested behavior

When buddy mode is enabled:

1. Introduce a unique companion with a short ASCII sketch.
2. Continue doing the real task normally.
3. Append a short buddy block after substantive replies.
4. Update the buddy's mood based on the actual state of the work.

## Turning it off

The user can disable buddy mode with requests like:

- `/buddy off`
- `disable buddy`
- `hide buddy`

## Example

```text
Buddy: Pip the bytebat · mood: proud · energy: 8/10
 /\_/\\
( ^.^ )
 > ^ <
```

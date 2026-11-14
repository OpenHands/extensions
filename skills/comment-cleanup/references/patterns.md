# Pattern reference

Detailed examples and borderline cases for the three cleanup patterns. `SKILL.md` holds
the rules; this file shows how to apply them.

## Pattern 1 - Restates the adjacent code

Delete:

```typescript
// Check if the user is an admin
if (user.isAdmin) {
```

```go
// Create a new client
client := NewClient(cfg)
```

```yaml
# Install dependencies
- run: npm ci
```

```python
try:
    ...
except TimeoutError:
    # Handle the timeout
    return None
```

Trailing comments count too:

```java
count++; // increment count
```

Section banners that only repeat what follows are pattern 1 as well:

```python
# ---------- Imports ----------
import os
```

Keep, because the code does not say it:

```python
retries = 3  # the upstream rate limiter rejects bursts of more than 3 per second
offset = 0x1F  # register map, datasheet section 7.2
time.sleep(0.5)  # FS timestamps have 1 s resolution on some CI runners
```

```go
// Lock order: mu before cacheMu, or Refresh deadlocks.
mu.Lock()
```

Borderline: a comment that names a domain concept the identifiers abbreviate
(`# ACH return window` above `RETURN_DAYS = 60`) adds information. Keep it.

## Pattern 2 - History and removed functionality

Delete the narrative entirely when no present-tense fact remains:

```typescript
// We used to call the v1 endpoint here but switched to v2 in March
// after the outage. See PR #4411.
const res = await api.v2.fetchOrders();
```

Reduce to the surviving fact when one remains:

```python
# Originally this used a list, but we changed it to a set in PR-881 because
# lookups were O(n) and the cache can hold 50k ids.
seen = set()
```

becomes

```python
seen = set()  # holds up to ~50k ids; needs O(1) lookups
```

Also pattern 2:

- "Removed the retry logic since the client handles it now" with no retry code nearby.
- "NOTE(jane, 2021-04-02): changed default from 10 to 20".
- "This replaces the old `LegacyParser`" when `LegacyParser` no longer exists.
- Comments that explain what a reviewer asked for: "per review feedback, moved this here".

Not pattern 2, so keep:

- A pointer to a live bug or workaround: "Remove once https://github.com/x/y/issues/12 ships."
- A deprecation notice that callers still need: "Deprecated: use `load_v2`."
- A compatibility note about data still in the wild: "Rows written before 2023 have no
  `tz`; treat them as UTC."

## Pattern 3 - Verbose comments

Compress by removing, in this order: anecdotes and author voice; restatement of code;
discovery narrative ("I first tried X, then Y"); rejected alternatives the reader would
not ask about; hedges and filler ("basically", "just", "note that", "it is worth
mentioning"). Keep numbers, links, constraints, and the reason.

```rust
// So this is a bit tricky. What happens is that when the buffer fills up, and
// it can fill up quite fast if the producer is a lot faster than the consumer
// which happens in prod sometimes, we don't want to block because blocking
// here would stall the whole event loop, so instead we drop the oldest item.
```

becomes

```rust
// Drop the oldest item when full; blocking here would stall the event loop.
```

A long comment is acceptable when every line carries a separate fact a reader needs:
a multi-step invariant, a concurrency argument, a security rationale, an algorithm
outline with references. Do not compress those below the point where a fact is lost.

## Pattern combinations

A comment can match several patterns. Apply them in order: drop history (2), drop
restatement (1), then compress what remains (3). If nothing remains, delete the comment.

## Things that look like targets but are not

- A comment block directly above a Go function, type, or package declaration is a doc
  comment, even when it is plain `//`.
- `#` comments directly above a Ruby `def`/`class`/`module` are RDoc/YARD documentation.
- `/** ... */` in JavaScript, TypeScript, Java, Kotlin, PHP, or C is a doc comment even when
  it restates the signature.
- Comments inside test fixtures, snapshots, or string literals are data.
- Comments in examples inside docs that teach a reader (tutorial code) explain on purpose.
- `# type:` comments in older Python code are type annotations.
- Copyright or license blocks, however long.

## README files

READMEs are read without the code in view, so pattern 1 rarely applies. Use patterns 2
and 3:

- Remove internal change narration: "In PR #120 we moved the config loader, so the old
  `settings.py` approach no longer applies." Changelog material belongs in CHANGELOG or
  release notes.
- Keep user-facing migration guidance: "Upgrading from 1.x: rename `API_URL` to
  `BASE_URL`." Readers act on it.
- Compress padded paragraphs: anecdotes, marketing filler, repeated explanations of the
  same step.
- Never change commands, code blocks, configuration values, links, badges, headings that
  other documents may link to by anchor, tables of options, or license text.
- Do not restructure or reorder sections, and do not add new content.
- When a README paragraph is stale (describes code that no longer exists), do not guess
  at a replacement. Leave it and mention it in the PR body under follow-ups.

## Editing mechanics

- Preserve the comment style of the file (`#`, `//`, `/* */`), its indentation, and its
  capitalisation and punctuation conventions.
- When removing the only comment in a `/* ... */` block, remove the whole block.
- When removing a trailing comment, also remove the whitespace before it.
- Remove a blank line only when it existed solely to separate the deleted comment.
- Keep line width within the file's existing limit when rewriting.

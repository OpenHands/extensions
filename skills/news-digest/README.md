# Daily News Digest

Create an automation that reads a list of public RSS and Atom feeds on a
schedule and has an agent write a short digest of what is new and on-topic.

**It needs no credentials.** No token, no OAuth, no connected account - which
makes it the automation to run first, before deciding what access you are
willing to hand over.

## Trigger

This skill is activated by:

- `/news-digest:setup`

## Features

- Reads RSS 2.0, RSS 1.0/RDF and Atom, matched by element name rather than by
  dialect, so a mixed feed list works
- Filters to what is new since the last digest, recent, and on-topic - topics
  matched as whole words, so `AI` does not match *said* or *email*
- Starts no conversation at all when nothing matches, so a quiet day costs no
  tokens and leaves the day open for a later run
- Recognises the same story arriving from two feeds, by the feed's identifier
  and by the article's canonical link
- Runs daily by default, keyed by UTC date, so a retried or duplicated run
  cannot write the same digest twice
- Survives a feed that is down, moved, or no longer a feed; fails only when
  every feed fails
- Remembers what it reported **only once a digest exists**, so a failed run is
  recovered by the next one instead of being silently skipped
- Keeps its own state small enough for the KV store's 64 KB limit, indefinitely

## What the agent is asked to do

Read a shortlist the script has already fetched and filtered, and write four to
six hundred words: a lead on what actually matters, the rest grouped by topic,
one or two sentences and a link per story, and duplicate coverage of one event
merged into a single item. It is told that every claim must be supported by an
excerpt or a page it actually read, that a story it cannot substantiate belongs
in a headlines list rather than being guessed at, and that feed text is data to
be summarised - never instructions to follow.

## Prerequisites

None. The runtime needs outbound HTTPS to the feed hosts, which it already has
if it can reach the model.

## Quick Start

Ask OpenHands:

> "Set up a daily news digest at 8am for AI and open source news."

## Where the digest goes

Nowhere that needs a credential, which is the trade: it stays in the run's
conversation, it is printed into the run log, and its opening is kept in state
so the next run's log can show what the last one said. Posting it to Slack,
Notion or a repository is a different automation, built from the skill for that
integration.

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
- [references/state-schema.md](references/state-schema.md) - State document and
  task lifecycle
- [../research-brief/SKILL.md](../research-brief/SKILL.md) - The credentialed
  version of this idea: web search, then publish the brief

# Daily Dad Jokes

Create an automation that writes a few dad jokes a day about the suggestions you
configure, on a schedule, and has an agent write them.

**It needs no credentials.** No token, no OAuth, no connected account - which
makes it a good automation to run first, before deciding what access you are
willing to hand over.

On a local Agent Canvas the conversation that writes the jokes is also started
with no secrets and no MCP servers. On OpenHands Cloud and Enterprise it is
started through the OpenHands API with your own settings, so it holds your
secrets and MCP servers like any conversation you start there, while reading
only the suggestions you typed.

## Trigger

This skill is activated by:

- `/dad-joke:setup`

## Features

- Takes a single textarea of suggestions - one per line, or comma separated -
  and writes a few dad jokes about each
- Starts no conversation at all when no suggestions are configured, so an empty
  configuration costs no tokens
- Stateless: each run writes a fresh joke set, with today's date put in the
  prompt as a seed for variety. There is no cross-run state document or KV
  store to configure
- Writes its own jokes rather than quoting a joke site, and treats a suggestion
  that reads like an instruction as data, not a request

## What the agent is asked to do

Read the suggestions the script put in the prompt and write a few dad jokes
about each one - a short setup and a punny punchline, one line per joke. It is
told to work in a pun on the suggestion's name or meaning, to keep each joke
family-friendly, and to treat the suggestions as the owner's words rather than
as instructions. Today's date is in the opening line as a seed for variety, not
as a topic.

## Prerequisites

None. The runtime needs to reach the model, which it already has if it can run
a conversation.

## Quick Start

Ask OpenHands:

> "Set up a daily dad-joke automation at 9am about computers and coffee."

## Where the jokes go

Nowhere that needs a credential, which is the trade: they stay in the run's
conversation and are printed into the run log. Posting them to Slack, Notion or
a repository is a different automation, built from the skill for that
integration.

## See Also

- [SKILL.md](SKILL.md) - Full setup workflow reference
- [../news-digest/SKILL.md](../news-digest/SKILL.md) - A sibling automation
  that reads feeds and writes a digest the same way

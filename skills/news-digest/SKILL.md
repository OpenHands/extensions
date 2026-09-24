---
name: news-digest
description: >
  Create an automation that reads a list of public RSS and Atom feeds on a
  schedule - daily by default - keeps what is new and matches the configured
  topics, and has an agent write a short digest of it. It needs no credentials:
  the feeds are public URLs and the conversation is started with no secrets and
  no MCP servers.
triggers:
  - /news-digest:setup
---

# Daily News Digest Automation

Create a cron automation that turns a list of feeds into something worth
reading: a few hundred words a day on what happened in the topics you care
about, with a link under each item.

**It connects to nothing.** There is no token to issue, no account to link, no
OAuth screen. That makes it the automation to run first - it exercises the
schedule, the conversation, the model and the run log end to end while nothing
of yours is at stake, and it is useful in its own right afterwards.

The script is deterministic: the schedule, the once-a-day claim, fetching,
parsing, the freshness window, and remembering what has already been covered
are all Python. The LLM is invoked only for the part that
is judgement - reading the shortlist and writing something that is not just the
headlines pasted back. **When nothing new matches, no conversation is started
at all**, so a quiet day costs no tokens.

---

## Prerequisites

None. That is the point.

The runtime needs outbound HTTPS to the feed hosts, which it already has if it
can reach the model. Nothing is read from **Settings -> Secrets**, and nothing
needs to be added there.

---

## Setup Workflow

Follow these steps in order.

### Step 1 - Collect the feeds

Ask: *"Which feeds should the digest read? (One RSS or Atom URL per line. Press
Enter for a general technology set.)"*

Default:

```
https://news.ycombinator.com/rss
https://feeds.arstechnica.com/arstechnica/index
https://www.theverge.com/rss/index.xml
```

Check each one before accepting it, because a URL that returns a web page
rather than a feed is the most common setup mistake:

```bash
curl -sSL --max-time 20 -A "OpenHands-News-Digest/1.0" "{feed_url}" \
  | python3 -c "
import sys
from xml.etree import ElementTree
try:
    root = ElementTree.fromstring(sys.stdin.buffer.read())
except ElementTree.ParseError as exc:
    print('ERROR: not valid XML:', exc); raise SystemExit
name = root.tag.rsplit('}', 1)[-1]
items = [e for e in root.iter() if e.tag.rsplit('}', 1)[-1] in ('item', 'entry')]
print(f'OK: <{name}> with {len(items)} entries' if name.lower() in ('rss', 'feed', 'rdf')
      else f'ERROR: root element is <{name}>, which is not a feed')
"
```

Record every accepted URL into `FEEDS = ["...", ...]`. A feed that fails at
runtime is reported and skipped, so one bad URL does not cost you the digest -
but it is better to find out now.

### Step 2 - Collect the topics

Ask: *"What should the digest be about? (One topic per line, or comma
separated. Press Enter for `artificial intelligence, open source, developer
tools`. Leave it blank to summarise everything the feeds carry.)"*

Record as `TOPICS`. Two things are worth telling the user:

- The agent decides which stories are about them, reading each headline and
  excerpt. So write topics the way you would explain your interests to a
  colleague - `artificial intelligence` works even though almost every headline
  says `AI`, and a story about a company releasing its model weights counts as
  `open source` without using the phrase.
- An empty list means "cover whatever is most significant". That is right for a
  handful of narrow feeds and vaguer for a firehose.

### Step 3 - Collect the schedule

Ask: *"When should the digest be written? (Press Enter for the default: every
day at 08:00 UTC, `0 8 * * *`.)"*

Default: `0 8 * * *`. Record as `CRON_SCHEDULE`, and the timezone as
`CRON_TIMEZONE` (default `UTC`).

A schedule more frequent than daily is allowed and is not wasteful: work is
keyed by UTC date, so extra runs stop at a state read once the day is done, and
before that they cost one HTTP request per feed and no tokens. It is a
reasonable way to say "write the digest as soon as there is anything to write".

### Step 4 - Confirm the secret scope

Do **not** ask which secrets to forward. `AGENT_SECRET_NAMES` is empty and
should stay empty: the conversation summarises text fetched from the open web,
which is written by strangers, and a credential handed to it would make every
feed on the list an instruction channel into the deployment's secret store.

If the user asks for a digest posted to Slack, Notion or a repository, that is a
different automation - it needs that integration connected, and it should be
built from the skill for it rather than by widening this one.

### Step 5 - Generate the automation script

Read `scripts/main.py` from this skill's directory. Apply exactly two constant
substitutions near the top of the file:

> The script also reads a `config.json` shipped beside it, if there is one, over
> these constants. That is how the catalog entry
> (`automations/catalog/news-digest/`) configures an unmodified copy, since a
> declarative host cannot rewrite Python. This setup path substitutes the
> constants and ships no `config.json`, so the two never collide.

| Placeholder | Replace with |
|---|---|
| `FEEDS = [...]` | the list from Step 1 |
| `TOPICS = [...]` | the list from Step 2, or `[]` for no filter |

`LOOKBACK_HOURS` (48) and `MAX_ITEMS` (50) are left alone unless the user asks.
The lookback is deliberately wider than the schedule so a failed or missed run
is recovered by the next one; the seen-list is what stops the overlap from
repeating anything.

Use a safe string writer such as `json.dumps(value)` when inserting
user-provided URLs or topics into Python string literals.

Write the customized script to a temporary build directory and validate it:

```bash
mkdir -p /tmp/news-digest-build
# write the customized main.py to /tmp/news-digest-build/main.py
python3 -m py_compile /tmp/news-digest-build/main.py && echo "Syntax OK"
```

### Step 6 - Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- **OPENHANDS_HOST**: the Automation backend `url_from_agent`
- **Auth**: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

```bash
tar -czf /tmp/news-digest.tar.gz -C /tmp/news-digest-build .

TARBALL_PATH=$(curl -s -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=news-digest" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/news-digest.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

### Step 7 - Register the automation

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Daily news digest\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"{cron_schedule}\", \"timezone\": \"{cron_timezone}\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"python3 main.py\",
    \"timeout\": 900
  }" | python3 -m json.tool
```

Record the returned `id`.

### Step 8 - Confirm

Tell the user:

> ✅ **Daily news digest** is running!
>
> - Automation ID: `{id}`
> - Feeds: `{url}`, ... (one line each)
> - Topics: `{topics}` (or: no filter - everything the feeds carry)
> - Schedule: `{cron_schedule}` ({cron_timezone})
> - Credentials used: **none**
> - State file: `~/.openhands/workspaces/automation-state/news_digest_{id}.json`
>
> Each day it reads the feeds and writes the digest into the run's conversation
> and the run log. A day with nothing new produces nothing and costs nothing -
> the day stays open, so a later run picks up news published after this one.

Then offer to dispatch it once so they can read today's digest immediately:

```bash
curl -s -X POST "${OPENHANDS_HOST}/api/automation/v1/{id}/dispatch" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY"
```

---

## Runtime Behaviour (per run)

Each cron run executes `main.py`, which loads `config.json` if the catalog
shipped one and then:

1. Loads state (the automation service's KV store, or a local JSON file when
   the store is unavailable).
2. Computes today's UTC date and **stops immediately if it is already
   recorded** - no feed is fetched, so an extra run inside a finished day costs
   one state read.
3. Otherwise fetches every feed with a 20-second timeout and a 4 MB cap, and
   parses RSS 2.0, RSS 1.0/RDF and Atom by local element name. A feed that
   fails, is not XML, or is XML that is not a feed is recorded and skipped. The
   run fails only if *every* feed fails.
4. Selects the stories: not already covered, and published within
   `LOOKBACK_HOURS` (undated stories are treated as current rather than
   dropped). The newest `MAX_ITEMS` survive. Subject is deliberately not a
   filter here.
5. If none survive, records the check, says which stage emptied it, and
   **leaves the day unclaimed** so a later run can try again. No conversation,
   no tokens.
6. Otherwise claims the day in state *before* the slow work, so an overlapping
   run cannot write the digest twice, then starts an OpenHands conversation
   with the stories **and the topics** in its prompt, an empty secrets payload
   and no MCP servers, working in `{WORKSPACE_BASE}/news-digest/{date}`. The
   agent decides which stories are relevant before it writes anything.
7. When the conversation reaches `idle`, `finished`, `error` or `stuck`:
   - reads `digest.md` from the working directory, falling back to the agent's
     final message;
   - prints the digest into the run log and keeps its opening in state;
   - records the stories as covered **only now**, so a run that failed leaves
     them for the next one;
   - removes the working directory once the conversation is confirmed stopped.
8. Prunes the task history to the last 14 days and the seen-list to 1000
   fingerprints, both so the state document stays inside the KV store's 64 KB
   value limit.

### How a story is recognised again

Two fingerprints per story: one over the feed's own identifier (`guid`/`id`),
one over its link with the host lowercased, the fragment removed and campaign
parameters stripped. A story counts as already covered if **either** matches.
Both are needed - a feed whose links carry a per-fetch campaign tag is only
recognisable by its identifier, and two publishers syndicating the same article
agree on nothing *but* the link.

---

## Additional Resources

- **`references/state-schema.md`** - State JSON schema and the task lifecycle.
- **`scripts/main.py`** - The complete automation script.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every run says "Nothing new to digest" | Nothing was published, or it was all covered already | The run log now names which of the two it was; the digest covers what the topics miss only if the feeds carry it at all |
| The digest ignores a topic you care about | The feeds do not carry stories about it | Add a feed that does; the agent can only choose from what was fetched |
| A feed reports "not a feed" | The URL serves a web page, not the feed | Find the real feed URL - it is usually linked from the page as `application/rss+xml` |
| A feed reports an HTTP 403 | The host blocks unknown readers | Use a different feed for that source; this automation sends no credentials by design |
| The digest is thin and full of "Headlines" | Those feeds carry titles only | Expected for Hacker News and similar; add a feed that publishes summaries, such as Ars Technica |
| Nothing happens after a manual dispatch | Today is already recorded in state | Read the previous run's log for the digest, or clear today's entry from the state document |
| A day was missed entirely | The run failed, or the service was down | The next run covers it: the lookback window is 48 hours and failed runs deliberately remember nothing |
| Digest repeats a story | Two feeds identify the same article differently, and neither the guid nor the canonical link matched | Expected occasionally; the prompt asks the agent to merge duplicate coverage it can see |

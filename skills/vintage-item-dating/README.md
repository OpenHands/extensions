# vintage-item-dating

Date and price a second-hand garment from photos of its labels.

## Why this exists

Dating clothing looks like a lookup task and is not. For most brands there is no authoritative label database, the published "how to spot vintage" guides often repeat each other word for word, and the era written in a resale listing title is a search keyword rather than a date.

This skill replaces a confident guess with an evidence board the user can read themselves.

## What it does

- Lists the photos actually needed, in priority order, before any analysis
- Reads the care and composition labels field by field, including care-symbol ordering
- Builds a label comparison board from live listings, with the user's own label pinned next to dated examples
- Measures how unreliable seller-stated decades are, rather than asserting it
- Flags rules that look authoritative but fail in practice, such as inferring a date from wordmark letter case
- Triangulates price from distributions, separating asking prices from completed sales

## When it triggers

Questions like "how old is this jacket", "is this real vintage", "what is this thrift find worth", or any request to read a care label, neck tag, or brand tag.

## Output

A comparison board, an evidence table split into established and contested, and a price range with its basis - plus an explicit list of what could not be determined and the one photo or source that would resolve the most.

## Extra reading

`references/marketplace-access.md` covers which resale and label sources are reachable from an automated browser, how to tell a User-Agent block from an IP block from a rate limit, and what to do in each case.

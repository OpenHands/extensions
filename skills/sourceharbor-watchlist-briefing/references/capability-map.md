# SourceHarbor Capability Map

This skill focuses on the SourceHarbor surfaces that help answer one operator question from one watchlist.

## Most relevant MCP capability groups

- `sourceharbor.health.get`: check runtime health before trusting the rest
- `sourceharbor.retrieval.search`: retrieve grounded evidence when the briefing is incomplete
- `sourceharbor.jobs.get` and `sourceharbor.jobs.compare`: inspect recent processing results
- `sourceharbor.artifacts.get`: fetch saved artifacts that back a claim
- `sourceharbor.reports.daily_send`: summarize the latest report-style output
- `sourceharbor.workflows.run`: only when the operator explicitly wants a governed workflow rerun
- `sourceharbor.subscriptions.manage` and `sourceharbor.notifications.manage`: useful only when the question is about source/watchlist configuration rather than story content

## Best default order

1. health
2. watchlist / briefing payload
3. retrieval or ask-style evidence lookup
4. jobs or artifacts only if the answer needs proof of what changed

---
name: ticket-to-code-change
description: >
  Set up a ticket-to-code-change automation using Jira or Linear as the issue
  tracker and GitHub, GitLab, or Bitbucket as the source-control provider.
  Watches for implementation-ready tickets, starts an OpenHands conversation
  to implement and test the request, opens a pull or merge request, and links
  the result back to the ticket.
triggers:
  - /ticket-to-code-change:setup
---

# Ticket to code change

Create an automation that turns implementation-ready tickets into tested pull
requests or merge requests.

## Information to collect

Ask the user for:

1. The issue tracker: Jira Cloud or Linear.
2. The source-control provider: GitHub, GitLab, or Bitbucket Cloud.
3. The project or team to watch and the label or workflow state that means
   "implementation ready".
4. How a ticket identifies its target repository and base branch.
5. The polling schedule or issue event to use.
6. The ticket state to set when work starts and when the change request opens.
7. Whether linked dependencies must be completed before dispatch.

## Setup workflow

1. Verify that both required integrations are connected and can read the
   selected project and repository.
2. Prefer an issue event trigger when the deployment can receive events;
   otherwise use cron polling with durable issue-ID deduplication.
3. Limit each run to a small configurable number of new tickets. On initial
   deployment, establish a baseline instead of dispatching the entire backlog.
4. Build a prompt that includes the full ticket, acceptance criteria,
   dependency status, repository, base branch, and provider-specific request
   terminology. Require the agent to run the repository's tests before opening
   the pull request or merge request.
5. Create the automation through the Automation backend described in
   `<RUNTIME_SERVICES>`. Use its prompt-preset endpoint and authenticate with
   the runtime-provided automation API key.
6. Configure the automation to post the OpenHands conversation URL immediately
   and the resulting pull-request or merge-request URL back to the ticket.

Do not dispatch tickets with unresolved dependencies or without an unambiguous
target repository; comment on the ticket with the missing information instead.

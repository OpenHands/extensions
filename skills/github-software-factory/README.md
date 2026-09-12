# Software factory

Four automations turn ready GitHub issues into independently tested and reviewed
pull requests. A deterministic watchdog can merge accepted changes. Each scheduled
run gets its own conversation, workspace, and session credential. The same bundle
and workflow sources run in local or Docker workspaces; provisioning and cleanup
are responsibilities of the execution backend. Conversation
history and acceptance reports survive runtime release.

| Role | GitHub operations |
| --- | --- |
| Triage | Read backlog, comment, create readiness labels, update issue labels/body |
| Developer | Read repository, comment, publish `factory/issue-N` branches, open PRs against `main` |
| Reviewer | Read repository, comment on the exact commit, write the two factory status contexts |
| Watchdog | Read repository and request a guarded merge |

The gateway holds the GitHub credential; bundles hold separate random role tokens.
No role can write arbitrary branches, force push, delete the repository, administer
settings, or directly invoke GitHub's merge endpoint. An empty repository is
initialized by the developer wrapper with one empty `.gitkeep`, giving the first
application PR a base. GitHub disallows self-approval when roles share an installation
identity, so independent review is a COMMENT review plus explicit acceptance status.

The guarded merge checks the current PR head, current base ancestry, mergeability,
two passing factory statuses, and other commit/check-run results. A changed head,
stale base, missing evidence, pending check, or failure prevents merging. All merge
requests include the reviewed SHA to prevent a head-update race.

## Deploy

Use Agent Server Docker runtime with selected-credential handoff and runtime release
(SDK PRs #3403, #4998, #5005, #5008) and Automation Service Docker dispatch support
(automation issue #448). Keep these development versions isolated from an existing
Canvas installation. Run a single Automation Service process; its Docker admission
limit is per service. Set `AUTOMATION_AGENT_PROFILE` to the saved profile UUID
and `AUTOMATION_CONVERSATION_MAX_CONCURRENT_RUNS=2`. Start with 2.5 GiB memory, 1.5 CPUs,
and 256 processes per sandbox, adjusting for host capacity. The worker environment needs git, Node 22, Chromium, and a Python interpreter
with `openhands-sdk` installed. Put that interpreter first on the worker PATH
(for the Agent Server image, `/agent-server/.venv/bin`). Apply the same dependency
setup to local workers; the entrypoint stays `python3 main.py` in both modes. The developer/reviewer profiles need terminal and file editing. Triage needs only
file editing to produce its structured decision. Give the deterministic watchdog
a profile with no model key, no MCP servers, and an empty tools list. Map automation
UUIDs to these profile UUIDs using the host setting
`AUTOMATION_AGENT_PROFILE_OVERRIDES` (a JSON object).

On the trusted control plane, authenticate `gh` using a credential restricted to
the target repository (contents, issues, pull requests, and commit statuses; checks
read access). Write a private mode-0600 JSON file with four cryptographically random
tokens keyed `triage`, `developer`, `reviewer`, and `watchdog`. Start:

```sh
FACTORY_REPOSITORY=owner/repository \
FACTORY_CONTROL_FILE=/private/factory-role-tokens.json \
FACTORY_BIND=172.17.0.1 python3 ../openhands-automation/scripts/github_factory_gateway.py
```

The bind address must be reachable from the Docker network and restricted to that
network. Default port is 19102. For each role, write a private `config.json`:

```json
{
  "role": "triage",
  "repository": "owner/repository",
  "broker": "http://172.17.0.1:19102",
  "token": "the-token-for-this-role"
}
```

Build the bundle from the registry checkout with:

```sh
python3 scripts/build_bundle.py /private/config.json /private/factory.tar.gz
```

The builder includes the canonical issue-to-PR and PR-reviewer scripts, the
QA Changes prompt and skills, and a source hash manifest. The recipe calls those
existing workflow definitions rather than maintaining alternative implementation,
review, or QA prompts. Only the repository transport and blocking execution
interface are supplied by the recipe; neither depends on workspace kind. GitHub
reviews use the existing native review format and inline findings. Full test
logs stay in workspace evidence, with a compact command summary on GitHub.

Upload using `POST /api/automation/v1/uploads`, then create a raw automation with
`POST /api/automation/v1`, the returned `tarball_path`, entrypoint `python3 main.py`,
`keep_alive: false`, and a cron trigger. Start with three-minute polls when sharing two worker slots: a long developer or
reviewer occupies one slot while the other must start and retire the idle role
polls. Watch queue age as well as container memory, and lengthen the interval
if idle polls accumulate. Use a longer interval for a quiet repository. Allow 3000 seconds for development, 9000 for sequential independent tests, code
review and functional QA, and 600 seconds for triage/watchdog. Configure the service
maximum run duration to accommodate that timeout. Do not put control-plane credentials in
bundle configuration. The backend supplies the selected runtime's session key.

Inspect run history and issue/PR comments to follow progress. Acceptance reports
include the exact commit, links to the newly published canonical review and QA
reports, and independent npm command output. Missing, stale, partial, or ambiguous
review evidence cannot satisfy acceptance.
Reports also live under the conversation workspace's `evidence` directory. The
reviewer rejects modifications to tracked files during review.

## Limits

Private and public repositories use exact-commit archives through the scoped gateway;
workers receive neither a GitHub token nor a credential-bearing git remote. Archives
are limited to 25 MB and extracted with Python's data filter.

This recipe currently serializes work to one open PR per repository, reads up to
100 open issues/PRs, publishes files up to 4 MB, and rejects symlinks. It uses a `main` branch and npm test contracts. Arbitrary build systems, and multiple concurrent implementation branches need
additional adapters. A PR with a stale base is blocked, requiring a development
follow-up before merge. Issue and repository content is untrusted input; role grants
limit damage if an agent follows injected instructions, but code executed by a role
shares that role's sandbox and can access its role token. Deploy separate untrusted
CI workers if that threat model requires stronger credential separation.

## Recovery

An agent that reaches its per-run step limit gets at most two automatic
continuations within the original wall-clock deadline. Authentication and other
errors fail without this retry. If a developer exhausts the budget or stops early,
the wrapper first ensures the agent has stopped, then publishes any preserved
changes as a checkpoint PR. Independent review still gates acceptance, and rejected
checkpoints return to a fresh development run instead of losing progress. For operational replay after an older bundle has
already failed, reprovision that conversation's retained Docker runtime and rerun
the fixed developer bundle with `resume_issue` set to its issue number. It verifies
the checkpoint repository and reuses the existing checkout and local baseline;
do not start a simultaneous fresh implementation. The failed original run remains
in history, and the replay has its own bash-command evidence in the same conversation.

### SDK Client Dependency

Runtime control uses the public `openhands.sdk.client.AgentServerClient` from
[software-agent-sdk #5010](https://github.com/OpenHands/software-agent-sdk/pull/5010).
Use an SDK build containing that change until its release is available. The
bundle owns workflow policy; the SDK owns Agent Server routes, authentication,
and runtime scope. The same bundle executes in local and Docker workspaces.

### Profile-selected gateway grants

Bundle configuration contains `token_env`, the name of one saved profile secret,
instead of a credential value. For example, the reviewer profile selects only
`FACTORY_REVIEWER_GRANT`; its entrypoint is
`env FACTORY_REVIEWER_GRANT="$FACTORY_REVIEWER_GRANT" python3 main.py`.
The SDK scoped shell service injects the named secret from that conversation's
registry. This requires the profile/shell delivery integration in SDK issue #5014.
The entrypoint and bundle are identical in local and Docker workspaces.

At first use, the gateway adapter materializes that one grant into a mode-0600
`.factory-gateway-token` file in the run workspace so subsequent canonical agent
tool calls can use it. The uploaded bundle contains only the name; missing grants
fail instead of falling back to `GITHUB_TOKEN`. Repository code running in the
same sandbox can access its role's grant, whose operations remain gateway-limited.
The trusted gateway separately uses the role-specific upstream GitHub credential
configured in the gateway reference. Do not place upstream GitHub tokens in
profiles or worker bundles.


The factory composes the issue-to-PR and reviewer prompt builders shipped in the
same extensions revision. These internal helpers are an explicit integration
contract covered by the factory prompt tests; changes to them must update those
tests and the bundle together. The issue-to-PR builder supports coordinator-owned
publication so factory prompts do not contain direct push/PR-creation commands.
The dispatcher sets WORKSPACE_BASE to the unpack directory in both runtime modes;
config.json and the gh adapter's parent directory therefore share that root.

Use `python3 main.py --token-env FACTORY_ROLE_GRANT` as the entrypoint, with the
actual name from `config.json` substituted. Naming the secret lets the SDK inject
it from the selected profile without shell expansion; the CLI rejects a name that
does not match the bundle. The same command works in local and Docker workspaces.

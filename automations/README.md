# Automations

`catalog/<id>.json` is the single hand-authored source of truth for one automation. It carries the card
metadata Agent Canvas renders today and, optionally, a nested `setup` block: the extension-owned
configuration experience for that automation.

```
catalog/*.json         one automation per file - card metadata plus an optional `setup` block
catalog.schema.json    the contract, JSON Schema draft 2020-12
catalog-index.js       generated from catalog/ - do not edit by hand
index.js               the stable API for Node.js and bundlers
index.d.ts             the public TypeScript shape
```

Adding or changing an automation should require changing exactly one JSON file in `catalog/`. Run
`npm run build:automations` afterwards to regenerate `catalog-index.js`, which statically imports each
individual JSON file for the JS package.

```js
import {
  AUTOMATION_CATALOG,
  listAutomationCatalog,
  getAutomationCatalogEntry,
} from "@openhands/extensions/automations";
```

All three return independent copies. Each entry references required integrations by ID; those IDs must
match entries in `integrations/catalog/*.json`.

## The `setup` block

`setup` defines **the configuration experience for one automation**: how it is discovered, what must be
connected first, what the user is asked, how a draft is validated, what request is sent, and which
analytics stages are emitted. It never defines what the automation *does* at runtime - that is the preset,
owned by `OpenHands/automation`.

It is optional. Three of eight entries carry one today.

The split it exists to serve:

| Repo | Owns |
| --- | --- |
| `OpenHands/extensions` | All per-automation information: identifiers, routes, copy, fields, validation semantics, request mappings, analytics |
| `OpenHands/agent-canvas` | Only the domain-neutral registry, renderer, workflow orchestration, and constrained action bridge |
| `OpenHands/automation` | Capabilities, authoritative preflight validation, creation APIs, runtime semantics |

`setup` never repeats `id`, `name`, `category`, or `description` - the entry already carries them, and one
record cannot drift from another. `setup.version` selects how the block is interpreted; a future format
ships a new constant.

### Format constraints

A setup block is data that instructs another repo to make HTTP calls and render copy, so the schema is the
trust boundary. It enforces:

- **No code.** There is no key that accepts JavaScript, and no free-form value that is executed.
- **No markup.** Every user-visible copy field rejects HTML. Request-body strings do not, because they are
  never rendered - that is what lets an event filter carry expression syntax.
- **No arbitrary requests.** `submit.action` is a closed enum of allowlisted capabilities, and every path
  is service-relative (`^/v1/`). The deployment base path is resolved by the host.
- **No credentials.** `requires.secrets[]` names a credential and closes the object, so there is nowhere to
  put a value. The host observes readiness only.
- **No supplied regex.** `constraints.format` names a host-implemented check from a closed set, so an entry
  cannot hand the host a pathological pattern.

Placeholders are namespaced and the schema rejects any other namespace: `{{form.*}}`, `{{automation.*}}`
(the entry itself), `{{response.*}}`, `{{capabilities.*}}`, and `{{submit.payload}}`. There is deliberately
no secrets namespace.

### The three archetypes

| Entry | Archetype | Trigger | Submits |
| --- | --- | --- | --- |
| `github-pr-reviewer` | Direct scheduled | `cron` | `POST /v1/preset/prompt` |
| `github-repo-monitor` | Direct GitHub-event | `event` on `github` with a JMESPath filter | `POST /v1/preset/prompt` |
| `incident-retrospective-drafter` | Assisted conversation | decided during the conversation | `conversation.start` |

The assisted archetype has no `validation.preflight` and no create request, because at the end of its flow
no automation exists yet. The agent creates it during the conversation, and the service validates it there.
That is the defining property of the archetype, not an omission.

### Two generations in one entry

`prompt` and `exampleImplementation` describe the **current** path: Agent Canvas sends the slash command to
an agent, which builds the automation. `setup` describes the **declarative** path that replaces it.

They can differ in more than wording. `github-repo-monitor`'s skill polls GitHub on a cron and states that
a webhook variant is out of scope, while its `setup` block creates the webhook form the service already
supports. Both statements are accurate about their own generation. Retiring `prompt` for entries that ship
a `setup` block belongs to whoever promotes this to production.

### Stage order

Stages 1 and 9 are host responsibilities. A stage in between runs if and only if its key is present, which
is why there is no `workflow` block listing them:

```
1. Load and validate the entry ........ host        <- catalog.schema.json
2. Capabilities check ................. host        -> GET  /v1/capabilities      (setup.capabilities)
3. Prerequisite check ................. host                                      (setup.requires.integrations)
4. Credential readiness ............... host                                      (setup.requires.secrets)
5. Render form and validate locally ... host                                      (setup.form.fields)
6. Preflight validation ............... host        -> POST /v1/validate          (setup.validation.preflight)
7. Review screen ...................... host                                      (setup.review)
8. Map values and execute the action .. host        -> setup.submit.action        (setup.submit)
9. Show the outcome ................... host                                      (setup.submit.onSuccess/onError)
```

## Contract fixtures

The fixtures are independent test vectors, not part of the runtime catalog. They live in
`tests/fixtures/automations/*.json` and are not required for every automation. Downstream contract tests
reach them through an explicit testing subpath:

```js
import scenarios from "@openhands/extensions/testing/automations/github-pr-reviewer.json";
```

`tests/fixtures/automations/<automation-id>.json` pairs the values a user types with the exact request that
must result. That pairing is the contract: form shape and API shape genuinely differ, the create endpoint
is declared `extra="forbid"`, and a mapping mistake is a 422 discovered only at creation time.

Each scenario carries whichever blocks apply: `formValues`, `integrationState`, `localValidation`,
`preflight`, `create`, `conversation`, `expectedFieldErrors`, `expectedReviewSummary`,
`expectedNavigation`. `capabilities.json` holds three deployment shapes so the unsupported paths have
coverage too.

`tests/test_automation_setup.py` runs every catalog entry against the schema and every fixture's form
values through its entry's mapping. Beyond that, every request body here has been checked against the live
Pydantic models in `OpenHands/automation`:

- each `201` body validates against `CreatePromptAutomationRequest`
- each `422` body reproduces the error detail the service actually returns, including the `loc` path
- each response `trigger` matches what `model_dump()` stores, so defaults such as `timezone` are present
- each event filter compiles under `validate_filter()`

Two findings came out of that check and are baked into the entries:

- **`repos[].provider` is required** for short `owner/repo` URLs. Without it the create request is a hard
  422, not a silently dropped field. Recorded as the `short-repo-url-without-provider-is-rejected` scenario.
- **A trigger phrase containing an apostrophe breaks the event filter**, because it is interpolated into a
  JMESPath string literal. Hence `constraints.format: "safeExpressionLiteral"` on that field, and the
  `quote-in-trigger-phrase-blocked-locally` scenario.

## Endpoints these fixtures assume

| Endpoint | Status |
| --- | --- |
| `POST /v1/preset/prompt` | Exists |
| `GET /v1/capabilities` | Does not exist. Defining it is OpenHands/automation#262 |
| `POST /v1/validate` | Does not exist. Defining it is OpenHands/automation#262 |

The two proposed paths follow the service's existing `/v1` router prefix. They appear only in
`setup.capabilities.discovery.path` and `setup.validation.preflight.path`, so settling on a different path
is a one-line change per entry.

## Deviations from the project reference document

The shape sketched in the project reference document is marked as a proposal, and hands several open
questions to this work. What changed and why:

| Proposed | Decision |
| --- | --- |
| A separate manifest file per automation | Merged into the catalog entry as `setup`, so there is one hand-authored record per automation and nothing to keep in sync. |
| `workflow.steps` | Removed. It restated which keys were present, creating a second source of truth that could contradict the file. |
| `form.intent: "seed"` | Removed. Derivable from `setup.mode: "assisted"`. |
| `validation.mode: "localOnly"` | Removed. Expressed by omitting `validation.preflight`. |
| `triggerKindsAnyOf` | Removed. Two near-identical keys invite mistakes. The assisted entry constrains no trigger kind and requires the `conversationDispatch` feature instead. |
| `submit.handoff` | Removed. Nothing consumes it, and the contract it gestured at does not exist yet. See the open questions below. |
| `{{form.filledCount}}` | Removed. It overloaded the `form` namespace with a computed value that names no field. |
| `errorMap` values | Widened to a string or an array of strings, so a payload path built from several fields maps back to all of them. |
| `submit.endpoint.path` | Constrained to `^/v1/`, so an entry cannot express a request to an arbitrary host. |
| `submit.message` | Capped at 2000 characters, so seed messages cannot grow back into the giant runtime prompts that recommended automation cards were already fixed to stop sending. |
| Analytics properties | snake_case, matching the properties Agent Canvas already emits (`automation_id`, `automation_name`). |

## Open questions

Recorded rather than resolved, because they need an owner outside this contract:

- **Localization.** Entries carry literal copy, because the ownership split assigns copy to this repo.
  Agent Canvas ships 15 languages. Shipping i18n keys instead would move the copy back into Canvas, so the
  gap is real and unsolved.
- **Distribution.** Agent Canvas pins `@openhands/extensions`, so changing an entry still needs a version
  bump and a dependency update. Delivering "change automation UI without a Canvas release" needs runtime
  loading.
- **Readiness-only credentials.** Agent Canvas currently collects secret values. Observing only a boolean
  needs a different mechanism, not a rename.
- **Assisted-setup completion.** The assisted flow ends at a conversation, so the host cannot emit a
  completion event. Until something reports back, the ratio of direct to assisted setup is not measurable.
- **Edit and delete routes.** Only the `new` route is modelled here.
- **Types from the schema.** `index.d.ts` is hand-written and mirrors `catalog.schema.json`. Generating it
  would remove that second source of truth.

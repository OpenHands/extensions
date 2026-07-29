# Automations

`catalog/<id>/` is one automation. Its `manifest.json` is the single hand-authored source of truth: the
card metadata Agent Canvas renders today and, optionally, a nested `setup` block, the extension-owned
configuration experience for that automation. Anything else an automation ships, such as a script that is
uploaded to the automations service as a `.tar.gz`, belongs in the same directory.

```
catalog/<id>/manifest.json   one automation per directory - card metadata plus an optional `setup` block
catalog.schema.json          the contract, JSON Schema draft 2020-12
catalog-index.js             generated from catalog/ - do not edit by hand
index.js                     the stable API for Node.js and bundlers
index.d.ts                   the public TypeScript shape
```

Adding or changing an automation should require changing exactly one JSON file. Run
`npm run build:automations` afterwards to regenerate `catalog-index.js`, which statically imports each
individual manifest for the JS package.

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

`setup` defines **the configuration experience for one automation**: what must be available before it can
be offered, what the user is asked, how a draft is validated, what request is sent, and which analytics
stages are emitted. It never defines what the automation *does* at runtime - that is the preset, owned by
`OpenHands/automation`.

It is optional. Three of eight entries carry one today.

The split it exists to serve:

| Repo | Owns |
| --- | --- |
| `OpenHands/extensions` | All per-automation information: copy, fields, validation semantics, request mappings, analytics |
| `OpenHands/agent-canvas` | Only the domain-neutral registry, renderer, workflow orchestration, and constrained action bridge |
| `OpenHands/automation` | Capabilities, authoritative preflight validation, creation APIs, runtime semantics |

`setup` never repeats `id`, `name`, `category`, or `description` - the entry already carries them, and one
record cannot drift from another. The same rule governs everything else in the block: nothing is stated
that the host can derive.

| Derived, so not declared | Where it comes from |
| --- | --- |
| The setup route | `/automations/new/<id>` |
| The capabilities endpoint | The host queries it for every automation, so it is not per-entry |
| The trigger kinds a deployment must support | The keys of `form.triggers` |
| The schedule limits and timezone list a form must respect | The `cron` and `timezone` field types |
| What to show when a requirement is unmet | `requires.integrations[].message` plus `required` |

`setup.version` selects how the block is interpreted; a future format ships a new constant.

### Triggers and args

`form` separates the two things a user is configuring:

- **`form.triggers`** decides *when* the automation runs. It is keyed by trigger kind (`cron` or `event`),
  and each key holds the inputs that kind needs. `github-pr-reviewer` asks for a schedule and a timezone;
  `github-repo-monitor` asks which GitHub event to answer and which phrase to match.
- **`form.args`** is everything else: the arguments to the automation itself, such as the repository to
  clone and the tone of the review.

An assisted entry declares no triggers, because the trigger is settled during the conversation.

### Format constraints

A setup block is data that instructs another repo to make HTTP calls and render copy, so the schema is the
trust boundary. It enforces:

- **No code.** There is no key that accepts JavaScript, and no free-form value that is executed.
- **No markup.** Every user-visible copy field rejects HTML. Request-body strings do not, because they are
  never rendered - that is what lets an event filter carry expression syntax.
- **No arbitrary requests.** `submit.action` is a closed enum of allowlisted capabilities, and every path
  is service-relative (`^/v1/`). The deployment base path is resolved by the host.
- **No credentials.** There is no key for a credential at all. An automation names the integrations it
  needs; the credential comes from the connection the user already made.
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

Stages 1 and 7 are host responsibilities. A stage in between runs if and only if its key is present, which
is why there is no `workflow` block listing them:

```
1. Load and validate the entry ........ host        <- catalog.schema.json
2. Availability check ................. host        -> GET  /v1/capabilities      (setup.requires)
3. Render form and validate locally ... host                                      (setup.form)
4. Preflight validation ............... host        -> POST /v1/validate          (setup.validation.preflight)
5. Review screen ...................... host                                      (setup.review)
6. Map values and execute the action .. host        -> setup.submit.action        (setup.submit)
7. Show the outcome ................... host                                      (setup.submit.onSuccess/onError)
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

The two proposed paths follow the service's existing `/v1` router prefix. The capabilities path is the
host's, and the preflight path appears only in `setup.validation.preflight.path`, so settling on a
different path is a one-line change per entry.

## Deviations from the project reference document

The shape sketched in the project reference document is marked as a proposal, and hands several open
questions to this work. What changed and why:

| Proposed | Decision |
| --- | --- |
| A separate manifest file per automation | Merged into the catalog entry as `setup`, so there is one hand-authored record per automation and nothing to keep in sync. |
| `routes` | Removed. The only route is `/automations/new/<id>`, which the id already gives. |
| `capabilities` | Removed. The discovery call is the same for every automation, and the block's only entry-specific content was a feature list, now `requires.features`. |
| `capabilities.bindings` | Removed. It existed to say that a schedule field respects the deployment's minimum interval and a timezone field offers the deployment's timezones. The `cron` and `timezone` field types say that on their own. |
| `requires.secrets` | Removed. An automation that needs GitHub declares the GitHub integration; the credential comes with the connection rather than being asked for twice. |
| `requires.onUnmet` / `onWarn` | Removed. What to do about an unmet requirement follows from `required`, and the copy follows from the integration's `message`. |
| `enforcement: "block" \| "warn"` | Replaced by `required: true \| false`. Two values, so a boolean says it, and `required` is already the word used for form fields. |
| `reason` / `help` / `message` | Unified on `message`. Three words for one thing. |
| `form.fields` | Split into `form.triggers` and `form.args`, so what decides *when* an automation runs is separate from what it is told to do. |
| `workflow.steps` | Removed. It restated which keys were present, creating a second source of truth that could contradict the file. |
| `form.intent: "seed"` | Removed. Derivable from `setup.mode: "assisted"`. |
| `validation.mode: "localOnly"` | Removed. Expressed by omitting `validation.preflight`. |
| `triggerKindsAnyOf` | Removed. The keys of `form.triggers` are the trigger kinds, so nothing restates them. |
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
- **Integration credentials at runtime.** Dropping `requires.secrets` assumes a created automation can use
  the credential behind a connected integration. Whether the automations service receives it, and how, is
  not settled here.
- **Assisted-setup completion.** The assisted flow ends at a conversation, so the host cannot emit a
  completion event. Until something reports back, the ratio of direct to assisted setup is not measurable.
- **Edit and delete routes.** Only the `new` route is modelled here.
- **Types from the schema.** `index.d.ts` is hand-written and mirrors `catalog.schema.json`. Generating it
  would remove that second source of truth.

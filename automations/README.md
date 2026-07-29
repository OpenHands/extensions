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

All three return independent copies.

## The governing rule

**A manifest states only what varies between automations, and states each of those things once.**
Anything that can be worked out from another field is absent, and the host generates it. That is what keeps
two records of the same fact from drifting apart, and it is why the file is as short as it is.

| Not declared | Where it comes from |
| --- | --- |
| The command the card launches | The `triggers:` frontmatter of the skill named by `skill`, which the skills catalog already exposes |
| The setup route | `/automations/new/<id>` |
| The integrations the card lists | `requires.integrations`, which every entry carries |
| The capabilities endpoint | The host queries it for every automation |
| The trigger kinds a deployment must support | The keys of `setup.form.triggers` |
| Schedule limits and the timezone list | The `cron` and `timezone` field types |
| Local validation rules | The `required` flag and `constraints` on each field |
| The preflight call | `POST /v1/validate` with the entry id, the create endpoint, and the rendered payload |
| The created automation's name | The entry's `name`, plus the repository that was picked |
| `repos` in the create request | The repo-picker field, its declared `provider`, and a field named `ref` if there is one |
| `trigger` in the create request | The key under `form.triggers`, and the fields under it named after trigger properties |
| Which input a rejected payload path belongs to | Rebuilding that body with each field standing in for its own value |
| The review screen | The fields and their labels |
| The create endpoint | `POST /v1/preset/prompt` |
| Where a success navigates | The created automation, or the started conversation |
| The analytics stages | The same stages for every automation |

`tests/test_automation_setup.py` derives the preflight body and the payload-path mapping from the entry and
checks them against the recorded fixtures, so these deletions stay honest rather than becoming assumptions.

## What an entry carries

```jsonc
{
  "id": "github-pr-reviewer",
  "name": "GitHub Code Review Agent",
  "category": "Code review",
  "description": "...",
  "requires": {
    "integrations": { "github": { "message": "Used to read pull requests and post review comments." } },
    "features": ["repoClone", "presetPrompt"]
  },
  "popularityRank": 100,
  "estimatedSetupMinutes": 4,
  "exampleImplementation": "...",
  "setup": {
    "version": "1.0",
    "mode": "direct",
    "form": {
      "triggers": { "cron": { "schedule": {...}, "timezone": {...} } },
      "args": { "repository": {...}, "triggerLabel": {...}, "reviewTone": {...} }
    },
    "prompt": "Review pull requests labeled '{{form.triggerLabel}}' in {{form.repository}}. ..."
  }
}
```

`requires` sits on the entry, not inside `setup`, because a card lists the integrations it needs whether or
not it ships a setup flow. Integrations are keyed by id, and each id must match an entry in
`integrations/catalog/*.json`. Every one carries a `message` saying what it is for, so an integration is
never listed with nothing attached. `required` defaults to true; state `false` only for an integration
setup can proceed without.

`skill` names the `skills/` directory that builds this automation today, and defaults to `id`, so only the
three entries whose names differ from their skill state it. The command that launches that skill is **not**
repeated here: it lives once, in the skill's own `triggers:` frontmatter, and the skills catalog exposes it.
That way a skill can rename its trigger without leaving a stale copy behind in this catalog.

`setup` is optional. Three of eight entries carry one today. It never repeats `id`, `name`, `category`, or
`description`. `setup.version` selects how the block is interpreted; a future format ships a new constant.

### Triggers and args

`form` separates the two things a user is configuring, and both are keyed by field name:

- **`form.triggers`** decides *when* the automation runs, keyed by trigger kind (`cron` or `event`).
  `github-pr-reviewer` asks for a schedule and a timezone; `github-repo-monitor` asks which GitHub event to
  answer and which phrase to match.
- **`form.args`** is everything else: the arguments to the automation itself, such as the repository to
  clone and the tone of the review.

An assisted entry declares no triggers, because the trigger is settled during the conversation.

### What the form produces

- **`mode: "direct"`** declares a `prompt`: what the automation is told to do. The rest of the create
  request restates the form, so it is not written out. An event trigger also declares a `filter`, because
  composing form values into a JMESPath expression is the one part of an event trigger that cannot be read
  off the form.
- **`mode: "assisted"`** declares a `message`: setup context handed to an agent conversation that finishes
  the job. The command that opens that conversation comes from the skill, so it is not repeated here.

A form field is named after the property it fills. `schedule` and `timezone` under `triggers.cron` become
`trigger.schedule` and `trigger.timezone`; `on` under `triggers.event` becomes `trigger.on`; a field named
`ref` becomes `repos[].ref`. Any other field under a trigger kind, such as a phrase to match, is an input
to `filter` rather than a trigger property.

### Format constraints

A setup block is data that instructs another repo to render copy and build a request, so the schema is the
trust boundary. It enforces:

- **No code.** There is no key that accepts JavaScript, and no free-form value that is executed.
- **No markup.** Every user-visible copy field rejects HTML. Payload strings do not, because they are never
  rendered - that is what lets an event filter carry expression syntax.
- **No arbitrary requests.** An entry supplies a request *body*. It does not name a host, a path, or a
  method, so it cannot express a request to anywhere the host did not choose.
- **No credentials.** There is no key for a credential at all. An automation names the integrations it
  needs; the credential comes from the connection the user already made.
- **No supplied regex.** `constraints.format` names a host-implemented check from a closed set, so an entry
  cannot hand the host a pathological pattern.

Placeholders are namespaced and the schema rejects any other namespace: `{{form.*}}` for what the user
entered and `{{automation.*}}` for the entry itself. There is deliberately no secrets namespace.

### The three archetypes

| Entry | Archetype | Trigger | Produces |
| --- | --- | --- | --- |
| `github-pr-reviewer` | Direct scheduled | `cron` | a create payload |
| `github-repo-monitor` | Direct GitHub-event | `event` on `github` with a JMESPath filter | a create payload |
| `incident-retrospective-drafter` | Assisted conversation | decided during the conversation | a seed message |

The assisted archetype has no payload and no preflight, because at the end of its flow no automation exists
yet. The agent creates it during the conversation, and the service validates it there. That is the defining
property of the archetype, not an omission.

### Two generations in one entry

`skill` and `exampleImplementation` describe the **current** path: Agent Canvas launches that skill, and the
agent builds the automation. `setup` describes the **declarative** path that replaces it.

They can differ in more than wording. `github-repo-monitor`'s skill polls GitHub on a cron and states that
a webhook variant is out of scope, while its `setup` block creates the webhook form the service already
supports. Both statements are accurate about their own generation. Retiring the skill path for entries that
ship a `setup` block belongs to whoever promotes this to production.

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
`preflight`, `create`, `conversation`, `expectedFieldErrors`, `expectedPrerequisiteOutcome`.
`capabilities.json` holds three deployment shapes so the unsupported paths have coverage too.

Beyond the derivation checks, every request body here has been verified against the live Pydantic models in
`OpenHands/automation`:

- each `201` body validates against `CreatePromptAutomationRequest`
- each `422` body reproduces the error detail the service actually returns, including the `loc` path
- each response `trigger` matches what `model_dump()` stores, so defaults such as `timezone` are present
- each event filter compiles, because `EventTrigger` validates it on construction

Two findings came out of that check and are baked into the entries:

- **`repos[].provider` is required** for short `owner/repo` URLs. Without it the create request is a hard
  422, not a silently dropped field. Recorded as the `short-repo-url-without-provider-is-rejected` scenario.
- **A trigger phrase containing an apostrophe breaks the event filter**, because it is interpolated into a
  JMESPath string literal. Hence `constraints.format: "safeExpressionLiteral"` on that field, and the
  `quote-in-trigger-phrase-blocked-locally` scenario.

## Endpoints the host calls

| Endpoint | Status |
| --- | --- |
| `POST /v1/preset/prompt` | Exists |
| `GET /v1/capabilities` | Does not exist. Defining it is OpenHands/automation#262 |
| `POST /v1/validate` | Does not exist. Defining it is OpenHands/automation#262 |

None of these appear in a manifest. They are the host's, which is why settling on different paths changes
no catalog entry at all.

## Deviations from the project reference document

The shape sketched in the project reference document is marked as a proposal, and hands several open
questions to this work. What changed and why:

| Proposed | Decision |
| --- | --- |
| A separate manifest file per automation | Merged into the catalog entry as `setup`, so there is one hand-authored record per automation and nothing to keep in sync. |
| `prompt` | Removed. It duplicated the slash command already declared in the skill's `triggers:` frontmatter. The entry names the `skill` instead, defaulting to `id`, and the command is looked up from the skills catalog. |
| `requiredIntegrationIds` | Removed. It duplicated the integration ids in `requires`, which now sits on the entry so every automation carries them once. |
| `routes` | Removed. The only route is `/automations/new/<id>`. |
| `capabilities` | Removed. The discovery call is the same for every automation, and the block's only entry-specific content was a feature list, now `requires.features`. |
| `capabilities.bindings` | Removed. The `cron` and `timezone` field types tell the host to resolve the deployment's limits on their own. |
| `requires.secrets` | Removed. An automation that needs GitHub declares the GitHub integration; the credential comes with the connection rather than being asked for twice. |
| `requires.onUnmet` / `onWarn` | Removed. What to do about an unmet requirement follows from `required`, and the copy follows from the integration's `message`. |
| `enforcement: "block" \| "warn"` | Replaced by `required`, which defaults to true and is stated only when false. |
| `reason` / `help` / `message` | Unified on `message`. Three words for one thing. |
| `form.fields` | Split into `form.triggers` and `form.args`, and both keyed by field name so the name is the key rather than a repeated property. |
| `validation` | Removed. The preflight call has the same shape for every automation, and the payload-path mapping is recovered by walking `payload`. |
| `review` | Removed. The confirmation screen is the declared fields and their labels. |
| `submit` | Reduced to the parts that vary: `prompt` and, for an event trigger, `filter` for direct; `message` for assisted. The action, endpoint, success navigation, and error handling are identical everywhere. |
| `submit.payload` | Removed. `name`, `repos` and `trigger` all restated the form, so they are rebuilt from it. What is left is the prompt and the event filter. |
| `analytics` | Removed. The same stages fire for every automation, so they belong in shared host code. |
| `workflow.steps` | Removed. It restated which keys were present, creating a second source of truth that could contradict the file. |
| `form.intent: "seed"` | Removed. Derivable from `setup.mode: "assisted"`. |
| `triggerKindsAnyOf` | Removed. The keys of `form.triggers` are the trigger kinds. |
| `{{form.filledCount}}` | Removed. It overloaded the `form` namespace with a computed value that names no field. |
| `submit.message` | Kept as `setup.message`, capped at 2000 characters, so seed messages cannot grow back into the giant runtime prompts that recommended automation cards were already fixed to stop sending. |

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
- **Grouped review rows.** The review screen is now one row per field. The hand-written summaries grouped
  related fields onto one line, which reads better; if that matters, it is a host concern, not an entry's.
- **Assisted-setup completion.** The assisted flow ends at a conversation, so the host cannot emit a
  completion event. Until something reports back, the ratio of direct to assisted setup is not measurable.
- **Edit and delete routes.** Only the `new` route is modelled here.
- **Types from the schema.** `index.d.ts` is hand-written and mirrors `catalog.schema.json`. Generating it
  would remove that second source of truth.

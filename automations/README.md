# Automations

`catalog/<id>/` is one automation. Its `manifest.json` is the single hand-authored source of truth: the
card metadata Agent Canvas renders today and, optionally, a nested `setup` block, the extension-owned
configuration experience for that automation. It is the only file there. A script an automation uploads as
a `.tar.gz` is not copied into this directory: `setup.bundle.files` names where it already lives, so a
script shipped by both a skill and the catalog has one copy rather than two.

```
catalog/<id>/manifest.json   one automation per directory - card metadata plus an optional `setup` block
catalog.schema.json          the contract, JSON Schema draft 2020-12
catalog-index.js             generated from catalog/ - do not edit by hand
interface.json               the production Automation interface manifest - domain-level, not per-entry
interface.schema.json        its contract, JSON Schema draft 2020-12
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
| The trigger variants a deployment can offer | The keys of `setup.form.triggers`; an entry with multiple keys is usable when at least one variant is supported |
| Schedule limits, timezone list, event choices, and model profiles | The `cron`, `timezone`, `event-source`, `event-type`, and `llm-profile` field types |
| Local validation rules | The `required` flag and `constraints` on each field, applied to the selected trigger variant |
| The preflight call | `POST /v1/validate` with the entry id, the create endpoint, and the rendered payload |
| The created automation's name | A form field named `name`, or the entry's `name` plus the repository that was picked |
| `repos` in the create request | The repo-picker field, its declared `provider`, and a non-empty field named `ref` if there is one |
| `model` and `timeout` in the create request | Same-named form fields when they have values |
| `trigger` in the create request | The selected key under `form.triggers`, and the fields under it named after trigger properties |
| Which input a rejected payload path belongs to | Rebuilding that body with each field standing in for its own value |
| The review screen | The fields and their labels |
| The create endpoint | `POST /v1/preset/prompt`, `POST /v1/preset/plugin`, or `POST /v1` for an uploaded or bundled tarball |
| The files a bundle packs | `setup.bundle.files`, read from this repository at build time |
| Where a success navigates | The created automation, or the started conversation |
| The analytics stages | The same stages for every automation |

`tests/test_automation_setup.py` derives the preflight body and the payload-path mapping from the entry and
checks them against the recorded fixtures, so these deletions stay honest rather than becoming assumptions.

## What an entry carries

```jsonc
{
  "id": "github-pr-reviewer",
  "name": "GitHub code review",
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

`setup` is optional. Entries that carry one never repeat `id`, `name`, `category`, or `description`.
`setup.version` selects how the block is interpreted; a future format ships a new constant.

### Triggers and args

`form` separates the two things a user is configuring, and both are keyed by field name:

- **`form.triggers`** decides *when* the automation runs, keyed by trigger kind (`cron` or `event`).
  If an entry declares more than one key, the host renders those keys as selectable variants and validates
  only the selected variant's fields before building the payload.
- **`form.args`** is everything else that is common to every creation path, such as the automation name,
  model profile, or timeout.
- **`setup.actions`** is optional and declares user-selectable creation paths for one card. The host renders
  the common form plus the selected action's `args`, checks that action's `features`, and creates through
  the endpoint implied by the action key: `prompt` -> `/v1/preset/prompt`, `plugin` -> `/v1/preset/plugin`,
  and `upload` -> `/v1/uploads` followed by `/v1`.

An assisted entry declares no triggers, because the trigger is settled during the conversation.

### What the form produces

- **`mode: "direct"`** declares exactly one creation archetype: a `prompt`, a repository-shipped `bundle`,
  or `actions`. A prompt creates through `/v1/preset/prompt`. A bundle is packed and uploaded by the host,
  then creates through `/v1`. An actions block lets the user choose between prompt, plugin, and uploaded
  tarball paths in one card. The rest of the create request restates the form, so it is not written out. A
  form field named `name`, `model`, or `timeout` fills the matching top-level create property. An event
  trigger may also declare a `filter`, because composing form values into a JMESPath expression is the one
  part of an event trigger that cannot always be read off the form.
- **`mode: "assisted"`** declares a `message`: setup context handed to an agent conversation that finishes
  the job. The command that opens that conversation comes from the skill, so it is not repeated here.

A direct entry may also declare a `message`. It is the seed for the fallback conversation the host offers
when the deployment cannot run the direct path - a deployment whose capabilities lack every declared trigger
variant or required features. The same 2000-character cap applies, and because the fallback fires before the
form is trustworthy, a direct `message` should not reference `{{form.*}}`.

A `repo-picker` may declare `multiple: true`, and then it collects several
repositories and its value is a list. A placeholder that is the *whole* value
resolves to that list rather than to text, which is what lets `"repos":
"{{form.repositories}}"` produce an array; the same placeholder inside a
sentence still reads as text. On the preset path the list becomes one `repos[]`
entry per repository. The created automation is named after the single
repository when there is one and after the count when there are several, since a
list of names does not fit a name.

A form field is named after the property it fills. `schedule` and `timezone` under `triggers.cron` become
`trigger.schedule` and `trigger.timezone`; `source` and `on` under `triggers.event` become `trigger.source`
and `trigger.on`; a field named `ref` becomes `repos[].ref` when it has a value. Any other field under a
trigger kind, such as a phrase to match, is an input to `filter` rather than a trigger property.

### Entries that ship a script

`mode: "direct"` produces exactly one of `prompt`, `bundle`, or `actions`. A
prompt is the right shape when the automation *is* the judgement: the agent
reads the prompt and does the work. A bundle is the right shape when most of
what the automation does is deterministic machinery - polling, dedupe, state,
fixed API calls - and the agent is needed only for the part that genuinely needs judgement.
`github-pr-reviewer` is the first: its script owns discovery, label-event
dedupe, per-repo state and the review checkout, and starts a conversation only
once a pull request actually needs reviewing.

```jsonc
"bundle": {
  "version": "1.0.0",                 // provenance; bump when the files or config shape change
  "entrypoint": "python3 main.py",    // run inside the extracted tarball
  "timeout": 600,                     // when the service default is not enough
  "files": {                          // packed path -> where it lives in this repo
    "main.py": "skills/github-pr-reviewer/scripts/main.py"
  },
  "config": {                         // rendered from the form, packed as config.json
    "repos": "{{form.repositories}}", // a whole-value placeholder, so this is a list
    "trigger_label": "{{form.triggerLabel}}",
    "review_tone": "{{form.reviewTone}}"
  }
}
```

The host packs those files plus the rendered `config.json`, `POST`s the archive
to `uploads`, and creates from the `oh-internal://` path that comes back. What it
sends is otherwise the same restatement of the form as the preset path, plus the
`template` provenance that makes enabling an entry twice return the automation
that already exists rather than a duplicate (`OpenHands/automation#344`).

Two things follow from the archetype rather than being stated:

- **`files` names paths, not contents.** The reviewer script is shipped by both
  its skill and this catalog, and a second copy would drift. `npm run
  build:automations` inlines the contents into `automations/bundle-index.js`,
  which is what `getAutomationBundleFiles(id)` returns - a host packing the
  archive has the published package, not this repository.
- **`config` is the bundle's `prompt`.** Everything else in the create request is
  read off the form; only the entry knows which key of its own script each field
  fills. The script reads that file over its own defaults, so the agent-driven
  skill path, which substitutes the same values as constants, keeps working
  unchanged.

A bundle declares `requires.features: ["customTarball"]`: a deployment that
cannot run a client-supplied tarball cannot run the entry, whatever trigger kinds
it offers. It never declares `repos` - the raw create endpoint has no such field,
and a bundle fetches what it needs itself. In an `actions` entry, creation-path
features move down to each action (`presetPrompt`, `presetPlugin`, or
`customTarball`) so a deployment can offer the supported choices without needing
every creation path.

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

### The archetypes

| Entry | Archetype | Trigger | Produces |
| --- | --- | --- | --- |
| `github-pr-reviewer` | Direct scheduled, script bundle | `cron` | an upload, then a create payload |
| `github-repo-monitor` | Direct scheduled | `cron` | a create payload |
| `qa-changes` | Direct event | `event` | a create payload |
| `custom-automation` | Direct custom action with prompt, plugin, or upload variants | `cron` or `event` | a create payload, or an upload then create payload |
| `incident-retrospective-drafter` | Assisted conversation | decided during the conversation | a seed message |

An entry can declare both `cron` and `event` under `setup.form.triggers`. The host treats those keys as
selectable variants and creates the payload from the selected one; a deployment that only supports one of
the variants can still offer that supported path.

The assisted archetype has no payload and no preflight, because at the end of its flow no automation exists
yet. The agent creates it during the conversation, and the service validates it there. That is the defining
property of the archetype, not an omission.

### Two generations in one entry

`skill` and `exampleImplementation` describe the **current** path: Agent Canvas launches that skill, and the
agent builds the automation. `setup` describes the **declarative** path that replaces it.

They can differ in more than wording. `github-repo-monitor`'s skill polls GitHub on a cron, and its `setup`
block declares the same polled `cron` form, so the two generations agree. (It once declared an `event`
form; when the deployment stopped receiving webhooks it was converted to this polling one.) Retiring the
skill path for entries that ship a `setup` block belongs to whoever promotes this to production.

## The interface manifest (`interface.json`)

The catalog states what varies per automation. `interface.json` states the domain-level facts of the
production Automation interface - the things that vary between *domains* (automations today, another
extension surface tomorrow) rather than between entries, so each is stated once rather than eight times.
Agent Canvas keeps its rendering components and reads every automation-specific datum from this file,
falling back to its built-in defaults when the manifest is absent or fails admission:

- **`routes`** - the list, setup, detail, and templates routes. The host must have a registration serving
  each declared shape, so admission verifies they match what it mounted; the manifest is the single source
  for link construction.
- **`navigation`** - the sidebar entry, the command-menu entry, and `subPages`: the ordered sub-page
  navigation rendered inside the Automation interface, each item naming a `pages` entry with a label and
  an icon slug from the host's closed icon map.
- **`pages`** - page-identity copy: the list title and subtitle, the detail back label, the edit-dialog
  title, the templates title and description. Generic chrome - buttons, toasts, empty states, validation
  sentences - stays host copy, rendered through the host's translations.
- **`pages.list.overview` / `filters` / `sort` / `insights`** - the list page's dashboard composition.
  Every value here names something the host implements from a closed set, and the manifest picks and
  captions it: `overview.tiles[].metric` names a host-computed value (`automations`, `needs-attention`,
  `total-runs`, `average-duration`), filter option values name host predicates (`status`: enabled /
  latest-run-failed / disabled; `trigger`: `event` matches event-triggered automations, `schedule`
  everything else), `sort` values name host comparators, and `insights` captions the host's run-health
  states and per-automation stats. The health precedence, the run sampling, the value formatting, the
  relative-time rendering, and the filtered-empty state with its reset button are the host's - a manifest
  cannot redefine them, only relabel what appears. Tile `detail` copy is plain substitution over the
  metric's placeholder namespace (only the `automations` metric exposes `{{active}}`); `zeroDetail`
  replaces `detail` while the value is zero.
- **`docsUrl`** - the automations documentation link, prefix-pinned to docs.openhands.dev by schema.
- **`attributes`** - the input surface of an existing Automation: which attributes can be set after
  creation, keyed by the runtime-model property the host sends (`name`, `prompt`, `model`, `timeout`,
  `schedule`), with labels, help, and numeric bounds. How a client offers them - Agent Canvas renders an
  edit dialog - is the client's choice, not stated here. `schedule` is a semantic type: the host owns the
  frequency/weekday/time composite it renders, as it owns the setup form's `cron` type.
- **`importExport`** - the export file envelope (`kind`, `version`, filename suffix) and the two facts an
  import cannot derive from the file: the provider inferred for short repository URLs, and the placeholder
  event source that keeps a half-imported automation inert until its real trigger is applied.
- **`endpoints`** - service-relative paths the host calls. Relative paths only: the base path, methods,
  headers, and auth remain the host's, so this cannot express a request to anywhere the host did not
  choose. `{id}` marks where the host substitutes the automation id.
- **`featuredAutomationIds`** / **`responderIntegrationIds`** - the catalog entries the list page surfaces
  as proven, and the integrations whose automations get the responder deployment-choice dialog.

`interface.schema.json` is the authoritative contract, under the same trust rules as the catalog: no
markup in copy, no free-form URLs, closed key sets, no credentials. This narrowly reverses the `routes`
and `submit` deletions recorded below **at the domain level only** - per-entry data still follows the
deletion table.

Changing a route or endpoint here still requires a host release that serves the declared shape, so the
Distribution open question applies unchanged. The contract fixtures pin `/v1/preset/prompt` as the create
endpoint; changing `endpoints.createPrompt` must regenerate them in the same release.

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

Each scenario carries whichever blocks apply: `formValues`, `selectedTrigger`, `integrationState`,
`localValidation`, `preflight`, `create`, `conversation`, `expectedFieldErrors`,
`expectedPrerequisiteOutcome`. `selectedTrigger` is required when an entry declares multiple trigger
variants and the scenario records a create or preflight payload. `capabilities.json` holds deployment
shapes so the unsupported paths have coverage too.

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
| `POST /v1/uploads` | Exists |
| `POST /v1` | Exists; accepts `template` provenance from OpenHands/automation#344 |
| `GET /v1/capabilities` | Exists (OpenHands/automation#270) |
| `POST /v1/validate` | Exists (OpenHands/automation#270) |

None of these appear in a catalog entry. Their service-relative paths are stated once, in
`interface.json`'s `endpoints` block, which is why settling on different paths changes no catalog entry at
all.

## Deviations from the project reference document

The shape sketched in the project reference document is marked as a proposal, and hands several open
questions to this work. What changed and why:

| Proposed | Decision |
| --- | --- |
| A separate manifest file per automation | Merged into the catalog entry as `setup`, so there is one hand-authored record per automation and nothing to keep in sync. |
| `prompt` | Removed. It duplicated the slash command already declared in the skill's `triggers:` frontmatter. The entry names the `skill` instead, defaulting to `id`, and the command is looked up from the skills catalog. |
| `requiredIntegrationIds` | Removed. It duplicated the integration ids in `requires`, which now sits on the entry so every automation carries them once. |
| `routes` | Removed from entries. The route table is a domain-level fact, stated once in `interface.json`. |
| `capabilities` | Removed. The discovery call is the same for every automation, and the block's only entry-specific content was a feature list, now `requires.features`. |
| `capabilities.bindings` | Removed. The `cron` and `timezone` field types tell the host to resolve the deployment's limits on their own. |
| `requires.secrets` | Removed. An automation that needs GitHub declares the GitHub integration; the credential comes with the connection rather than being asked for twice. |
| `requires.onUnmet` / `onWarn` | Removed. What to do about an unmet requirement follows from `required`, and the copy follows from the integration's `message`. |
| `enforcement: "block" \| "warn"` | Replaced by `required`, which defaults to true and is stated only when false. |
| `reason` / `help` / `message` | Unified on `message`. Three words for one thing. |
| `form.fields` | Split into `form.triggers` and `form.args`, and both keyed by field name so the name is the key rather than a repeated property. |
| `validation` | Removed. The preflight call has the same shape for every automation, and the payload-path mapping is recovered by walking `payload`. |
| `review` | Removed. The confirmation screen is the declared fields and their labels. |
| `submit` | Reduced to the parts that vary: `prompt` and, for an event trigger, `filter` for direct; `message` for assisted (and, on direct entries, as the fallback-conversation seed). The action, success navigation, and error handling are identical everywhere; the endpoints are domain-level and live in `interface.json`. |
| `submit.payload` | Removed. `name`, `repos` and `trigger` all restated the form, so they are rebuilt from it. What is left is the prompt and the event filter. |
| `analytics` | Removed. The same stages fire for every automation, so they belong in shared host code. |
| `workflow.steps` | Removed. It restated which keys were present, creating a second source of truth that could contradict the file. |
| `form.intent: "seed"` | Removed. Derivable from `setup.mode: "assisted"`. |
| `triggerKindsAnyOf` | Removed. The keys of `form.triggers` are the available trigger variants, and multiple keys already mean the host can offer any supported one. |
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
- **Delete confirmation and per-run views.** `interface.json` models the routes, the settable attributes,
  and the dashboard and templates sub-pages; deletion and run logs remain host-owned surfaces with no
  manifest data of their own yet.
- **Types from the schema.** `index.d.ts` is hand-written and mirrors `catalog.schema.json`. Generating it
  would remove that second source of truth.

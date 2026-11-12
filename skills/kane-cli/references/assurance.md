# Kane CLI assurance: tests designed from requirements

When the user has requirements (a PRD, a spec or acceptance notes) and wants tests designed from them, wants to know what is covered, or wants the suite kept current, use the assurance commands: `kane-cli context`, `design`, `cover` and `maintain`. Each designed test is tagged with the acceptance criteria it verifies, and coverage is measured against the requirements.

The commands need Kane CLI 0.6.1 or later. On an older CLI, `kane-cli context ...` fails as an unknown command with exit code `2`; that means the CLI is too old, not that the command is wrong.

The work lives in a local store (`.context/` in the project folder) that the commands manage. A folder linked to a team's shared project works differently; see the upstream reference linked below.

## The journey

Follow these steps in order and stop at the two checkpoints:

```bash
kane-cli context ingest ./prd.md --mode agent                   # 1. land the source and propose use-cases
kane-cli context review --verdicts verdicts.json --json         # 2. CHECKPOINT: the user approves the use-cases
kane-cli design tests --use-case <uc-ref> --mode agent --max 8  # 3. design criteria, scenarios and tests
kane-cli context review --verdicts verdicts.json --json         # 4. CHECKPOINT: the user approves the design
kane-cli testmd run .testmuai/tests/<name>_test.md --agent      # 5. author each kept test once, in a real browser
kane-cli testrun run --match 't-' < /dev/null                   # 6. replay them in a batch from then on
kane-cli cover gaps                                             # 7. coverage and the work left per use-case
```

When a source changes, run `kane-cli maintain reconcile --from <new.md> --source-id <id> --mode agent`.

## Rules

- **The checkpoints are the user's.** Everything the commands propose stays unreviewed until the user approves it, even when the user asked for an end-to-end run. Show the user the items themselves (`kane-cli context list --json --inferred` lists what is waiting, and `kane-cli context explain <ref> --json` shows one item with its citations), collect their decisions, then land them.
- **`verdicts.json`** is an array of `{"ref": "<ref>", "resolution": "..."}`, where `resolution` is `approved`, `edited`, `rejected`, `skipped` or `supersede`. One unknown ref fails the whole file with exit code `2`. For single decisions, use `kane-cli context review --approve <ref>` or `--skip <ref>`.
- **One store-writing command at a time.** Never run `ingest`, `extract`, `review` with verdicts, `design`, `reconcile` or `evolve` at the same time. A concurrent extraction is refused with `EXTRACT_LOCKED` and exit code `2`; wait for the first one, and never delete lock files.
- **Credits.** Extraction, design, reconcile and evolve call the KaneAI service and spend credits. The rest is local.

## Pauses: exit code 3

`context ingest`, `context extract`, `design tests`, `maintain reconcile` and `maintain evolve`, like the other assurance commands, reject `--agent`; pass `--mode agent`. Without a terminal and without `--mode`, `context ingest` only adds the files and does not look for use-cases.

In `--mode agent`, every question pauses the session. The command exits `3` and prints a `session_paused` event with the questions, their options, the recommended option and the exact resume command. This is a pause, not a failure. (For `run`, `testmd run` and `testrun run`, exit code `3` still means timed out or cancelled.)

- Never drop a pause. If your own context clearly settles a question, answer it; otherwise show the user the question, its options and the recommendation, and ask.
- Resume in plain words, by question id, or with a new source:

```bash
kane-cli context extract --resume <session-id> --mode agent --message "Sign-in is required for checkout"
kane-cli context extract --resume <session-id> --mode agent --answer q1=1 --answer q2="https://app.example.com"
kane-cli context extract --resume <session-id> --mode agent --with-source ./addendum.md
```

- Sessions last 24 hours. `kane-cli context sessions --json` lists resumable sessions with their resume commands.

Adapted from the Kane CLI agent skill (Apache-2.0) at the `0.10.0` tag, where the full reference also covers shared projects, coverage accounting and reconcile: https://github.com/LambdaTest/kane-cli/blob/0.10.0/.agents/skills/kane-cli/references/assurance.md

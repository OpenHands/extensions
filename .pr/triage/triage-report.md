# Live Canvas: independent GitHub issue triage

[Actual Canvas recording](triage-live.gif), captured 2026-09-13 around 15:02 UTC, shows the UI-created triage automation working on [Airbnb issue #47](https://github.com/neubig/airbnb-clone/issues/47). The operator only opened that feature request, without labels or an acceptance-criteria list.

The agent assessed scope, assigned normal priority, and produced eight testable acceptance criteria. The wrapper published a [readable triage comment](https://github.com/neubig/airbnb-clone/issues/47#issuecomment-5654062140) and applied `priority:normal` and `ready-for-dev`. The next scheduled sweep completed with the source unchanged; the issue still has exactly one triage note. [Issue snapshot](triage-issue.json) records the resulting labels and comment.

Conversation `a8f9a37f-a4f2-4b65-967d-2cf5b00d37d1` came from definition `dbf75907-f092-443f-95d7-2f7b3e97e9fa`, configured entirely through Canvas. It selected profile `factory-triage`; runtime probes separately verified only the triage PAT name was present. No token values are recorded.

## Installation and companions

Catalog bundles explicitly contain the shared GitHub helper. [Actual clean SDK Git installs](git-install.json) materialize the source symlinks as ordinary files and import all four workers. The npm release has a separate resource-materialization prerequisite, extensions #579; unmodified `npm pack` in a source checkout omits symlinks. The new staged npm archive has been tested, but no npm release has been published.

This after-only enhancement demonstration uses composed preview dependencies: Canvas `a3c7915db5f47800f5240a25987b2af75b0d8d04`; host SDK `7fe37443b`; Docker image `d8bbd04fd795` from SDK `e0c6a73752fe`; Automation `6df90db2` with SDK client `ac6d12b0b9d76f1cc38a6eb1ea51cd92e34a0bf2`; deployed catalog runtime bundle from extensions `591ce05`. The packaging-only symlinks added afterward do not alter those bundle bytes. Git-install verification used extensions `e8a4508296a7f3ec118b7e69ee681ab73bdcd800`.

The GIF comprises five genuine Canvas screenshots at three seconds each. It proves this triage flow and unchanged-input behavior, not every dependency/error edge case. The source screenshots remain in the demo workspace under `factory-state/evidence/live-delivery`.

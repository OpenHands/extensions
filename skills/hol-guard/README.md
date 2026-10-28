# HOL Guard Plugin Scanner for OpenHands

This optional OpenHands skill teaches an agent to inspect a supported third-party AI-agent artifact **without executing it**. It uses HOL's separately published `plugin-scanner` CLI to perform a security scan, plus optional authoring/packaging checks.

It **does not** install HOL Guard hooks, intercept OpenHands tool calls, protect OpenHands itself, or modify another coding agent's configuration. An OpenHands extension file is not necessarily a format recognized by the scanner.

## Example

When the user authorizes a scan of an artifact format supported by the installed scanner:

```bash
pipx install 'plugin-scanner==3.58.0'
plugin-scanner --version
plugin-scanner scan <path> --format json
```

Replace `<path>` with the selected supported package root. The pinned version was available on PyPI on October 28, 2026; check its suitability before running the command.

Optional authoring and package-readiness checks, **not** a replacement for the security scan:

```bash
plugin-scanner lint <path>
plugin-scanner verify <path>
```

Do not execute untrusted package hooks or report an unrecognized package as clean. Report actual files in scope, command results, unresolved findings, and unsupported formats. No successful scanner result is an OpenHands runtime enforcement guarantee.

## Sources

- Published scanner: https://pypi.org/project/plugin-scanner/
- Open-source implementation: https://github.com/hashgraph-online/hol-guard
- Product context: https://hol.org/guard

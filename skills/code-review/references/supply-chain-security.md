# Supply Chain Security Checklist for Dependency Changes

When a PR adds a new dependency or bumps an existing one, review the upstream release for supply chain risk. Real-world incidents (e.g., LiteLLM 1.82.7-1.82.8 in March 2026, PyTorch Lightning 2.6.2-2.6.3 in April 2026) show that trusted packages can be hijacked through compromised CI/CD pipelines, stolen publishing credentials, or poisoned build artifacts - with malicious code present only in the published package, not in the source repository.

## Default Approval Rule

Use a simple default rule for dependency updates:

- If the target version was published less than 7 days ago, do **NOT** approve the PR. Leave a blocking review comment that cites the 7-day minimum age policy.
- If the target version is at least 7 days old, continue with the sanity checks below before approving.
- Apply the same rule to both new dependencies and version bumps. Recent supply-chain attacks often land in the first few days after publication, before the ecosystem has time to notice and react.

For PyPI: visit `https://pypi.org/project/<package>/<version>/` and check the "Released" date. For npm: run `npm view <package>@<version> time`.

## Sanity Checklist

Once the version clears the 7-day minimum age rule, do a quick sanity check:

- **Release metadata looks normal**: Verify a source tag or release note exists for the target version. Check `https://github.com/<org>/<repo>/releases/tag/v<version>` or run `gh release view v<version> --repo <org>/<repo>`.
- **No obvious registry warning**: Check whether the target version or nearby versions are yanked, deprecated, or retracted. For npm: `npm view <package>@<version>` or `https://www.npmjs.com/package/<package>/v/<version>`. For PyPI: `pip index versions <package>` or the package history page.
- **No suspicious install-time behavior**: For npm, check for new `preinstall`, `install`, `postinstall`, or `prepare` scripts in the package's `package.json`. For Python, look for `.pth` files or setup/install code that executes on install or import.
- **No active compromise signals**: Search the registry page and a security feed such as Socket, OSV, or Snyk for an active compromise or supply-chain incident affecting the target package or version.

## Escalation Guidance

Escalate to 🔴 High Risk, and do **NOT** approve the PR, when any of the following is true:

- the target version is newer than 7 days
- the version is yanked, deprecated, or retracted for security reasons
- the published package shows suspicious install-time behavior
- a security feed reports an active compromise or supply-chain incident

If the update is at least 7 days old and the quick checks look normal, continue the ordinary review flow.

# Verification and local acceptance

Run type-checking, build, unit/integration tests, static artifact validation, and a real Chromium Blob-import smoke test. A Vite preview or Node-only module import is not an adequate production test.

Test manifest registrations, unsupported API rejection, root/nested/unknown routes, loading/empty/error/malformed-response states, exact Agent Server request shape, cancellation/stale response suppression, mount cleanup, activation cleanup, and remounting. Confirm one-file browser output even for a multi-process architecture and confirm no service secret or origin assumption is embedded. For Workers/WASM/native integrations, exercise the genuine core behavior in the browser or focused temporary integration fixture.

For a Sidecar-backed App, verify explicit consent and idempotent onboarding, restart and version-mismatch recovery, backend switching, and the distinction between App removal, service uninstall, and data deletion.

For local Agent Canvas acceptance:

1. Run `npm install` and `npm run check` from the App directory.
2. Obtain the absolute directory path.
3. Install that one App from the local path; it must remain disabled initially.
4. Enable it and exercise primary and nested routes.
5. Reload Canvas.
6. Disable it and confirm its page disappears.
7. Re-enable it and repeat the primary flow.
8. After changing a bundle, rebuild, uninstall, and reinstall before retesting. The current Apps screen has no refresh action.

Record unavailable manual checks as not run. Do not enable, uninstall, publish, push, or open a pull request without explicit authorization.

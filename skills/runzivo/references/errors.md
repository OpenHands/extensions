# rzv errors and what to do

`rzv` prints a short message and exits non-zero. With `--json` the error has a `code`.

| Message or code | What to do |
| --- | --- |
| `rzv: command not found` | Ask the user to install rzv: `curl -fsSL https://runzivo.dev/downloads/rzv/install.sh \| sh` |
| "Sign in with `rzv login` first", sign-in expired | Ask the user to run `rzv login`, then retry. |
| `credit_exhausted` | The workspace is out of credit. Ask the user to add credit, then start or create again. |
| `sandbox_limit_reached` | The workspace runs its maximum number of sandboxes. Offer to stop or delete one the user names. |
| `sandbox_capacity_busy`, `no_capacity` | No capacity right now. Wait a few minutes and retry, or try a smaller `--size`. |
| `size_unavailable` | Run `rzv sandboxes sizes` and pick a size that is available. |
| `lifetime_unavailable`, `invalid_lifetime` | Use `8h`, or a lifetime that `rzv sandboxes list` shows. |
| `sandbox_name_taken` | Pick another `openhands-<slug>` name. |
| `sandbox_wrong_state` | Check `rzv sandboxes get <sandbox-id>`; wait for "running" or start it. |
| `sandbox_expired` | The lifetime ended. Create a new sandbox. |
| `sandbox_not_found` | Wrong id or wrong workspace. Run `rzv sandboxes list`. |
| `insufficient_role`, access denied | The user's role or API key lacks `sandboxes:write`. Ask them to fix access. |
| SSH host certificate wait or connection closed | Make sure the sandbox is running, rerun `rzv sandboxes ssh-config <sandbox-id> --write`, then reconnect. |

Never retry `create` in a loop. Pass `--idempotency-key <8-200 chars>` if you might repeat a create; the same key returns the same sandbox.

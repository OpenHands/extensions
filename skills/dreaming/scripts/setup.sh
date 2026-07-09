#!/usr/bin/env bash
# Install-time script for the Dreaming automation tarball.
#
# Installs bun (if missing) and the @letta-ai/openhands-dreaming CLI, then
# writes an absolute-path wrapper `./openhands-dreaming` into the automation
# working directory. The wrapper is required because PATH exports made here
# do NOT survive into the entrypoint (`bash run.sh`).
#
# Env knob (optional):
#   OPENHANDS_DREAMING_VERSION  npm version to pin (default: latest)
set -euo pipefail

if ! command -v bun >/dev/null 2>&1 && [ ! -x "$HOME/.bun/bin/bun" ]; then
  # Tradeoff acknowledged: the automation sandbox has no preinstalled bun, so
  # we use the official installer, pinned to a known-good release.
  curl -fsSL https://bun.sh/install | bash -s "bun-v1.3.4"
fi
export PATH="$HOME/.bun/bin:$PATH"

DREAMING_VERSION="${OPENHANDS_DREAMING_VERSION:-latest}"

# Absolute paths baked into the wrapper below (bun may be preinstalled
# somewhere other than ~/.bun, e.g. via a system package).
BUN_BIN="$(command -v bun || echo "$HOME/.bun/bin/bun")"
BUN_GLOBAL_BIN="${BUN_INSTALL:-$HOME/.bun}/bin"

bun add --global "@letta-ai/openhands-dreaming@${DREAMING_VERSION}"

# Wrapper in the extracted automation directory so run.sh can invoke
# `./openhands-dreaming` by relative path regardless of PATH. All paths are
# baked in as absolute at install time.
cat > openhands-dreaming <<EOF
#!/usr/bin/env bash
if [ -x "${BUN_GLOBAL_BIN}/openhands-dreaming" ]; then
  exec "${BUN_GLOBAL_BIN}/openhands-dreaming" "\$@"
fi
exec "${BUN_BIN}" x --bun "@letta-ai/openhands-dreaming@${DREAMING_VERSION}" "\$@"
EOF
chmod +x openhands-dreaming

./openhands-dreaming --version || true
echo "setup complete"

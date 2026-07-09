#!/usr/bin/env bash
# Entrypoint TEMPLATE for the Dreaming automation.
#
# The /dreaming:setup flow substitutes the __PLACEHOLDER__ values below before
# packaging the tarball. This file is a thin launcher only: all logic lives in
# the pinned @letta-ai/openhands-dreaming npm package, installed by setup.sh,
# which also writes the ./openhands-dreaming wrapper this script execs.
#
# Secrets (GITHUB_TOKEN + the model provider API key) are never baked into
# this file: the CLI resolves them from the environment or fetches them from
# the Agent Server secret store at run time.
set -euo pipefail

exec ./openhands-dreaming run \
  --repo "__TARGET_REPO__" \
  --model "__MODEL__" \
  --to "__TO_PATH__" \
  --lookback "__LOOKBACK_MINUTES__" \
  --json

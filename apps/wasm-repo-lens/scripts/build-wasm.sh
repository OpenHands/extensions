#!/bin/sh
set -eu

app_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
engine_root="$app_root/rust-engine"
output="$engine_root/target/wasm32-unknown-unknown/release/repo_lens_engine.wasm"

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo is required to rebuild the Rust engine. The checked-in WASM remains sufficient for App users." >&2
  exit 1
fi

cargo build --manifest-path "$engine_root/Cargo.toml" --target wasm32-unknown-unknown --release
cp "$output" "$app_root/src/repo_lens_engine.wasm"
echo "Updated src/repo_lens_engine.wasm from the release Rust build."

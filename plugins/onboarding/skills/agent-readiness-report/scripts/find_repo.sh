# shellcheck shell=bash
# Shared filesystem boundary for the readiness scanners. Source this file;
# it is not a scanner entrypoint.

find_repo() {
  local root="$1"
  shift
  local -a depth_options=()
  # find's depth options apply globally and must precede the prune expression.
  while [ "$#" -ge 2 ] && { [ "$1" = -maxdepth ] || [ "$1" = -mindepth ]; }; do
    depth_options+=("$1" "$2")
    shift 2
  done

  # Prune at any depth, including dependencies inside authored monorepo packages.
  # Do not use .gitignore: ignored project docs/examples can still be evidence.
  find "$root" "${depth_options[@]}" \
    \( -type d \( -name .git -o -name node_modules -o -name .venv -o -name venv \) -prune \) \
    -o \( "$@" \) -print
}

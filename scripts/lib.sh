#!/usr/bin/env bash
# Shared library; source it from operational scripts.
set -Eeuo pipefail
EP_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
require() { command -v "$1" >/dev/null 2>&1 || { printf 'Missing dependency: %s\n' "$1" >&2; return 127; }; }
compose() { docker compose --project-directory "$EP_ROOT" -f "$EP_ROOT/compose.yml" "$@"; }
local_url() {
  case "$1" in
    http://127.0.0.1:*|http://localhost:*) ;;
    *) printf 'Only loopback HTTP URLs are supported; use an SSM/SSH tunnel.\n' >&2; return 2 ;;
  esac
}

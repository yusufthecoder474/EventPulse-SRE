#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
require docker
require python
docker compose version >/dev/null
compose config --quiet
for service in db api web prometheus grafana alertmanager; do
  id="$(compose ps -q "$service")"
  [[ -n "$id" ]] || { printf 'Missing running service: %s\n' "$service" >&2; exit 1; }
  state="$(docker inspect --format '{{.State.Status}}' "$id")"
  [[ "$state" == running ]] || { printf '%s: %s\n' "$service" "$state" >&2; exit 1; }
  printf '%s: running\n' "$service"
done
bash "$EP_ROOT/scripts/smoke-test.sh"
python "$EP_ROOT/scripts/verify_monitoring.py"

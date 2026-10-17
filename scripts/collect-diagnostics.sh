#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
require docker
require python
# Deliberately exclude environment, resolved Compose config, raw logs and attendee data.
OUT_DIR="${OUT_DIR:-$EP_ROOT/evidence/v2/diagnostics-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p -- "$OUT_DIR"
for service in db api web prometheus grafana alertmanager; do
  id="$(compose ps -a -q "$service")"
  if [[ -n "$id" ]]; then
    docker inspect --format '{"service":"'"$service"'","status":"{{.State.Status}}","restart_count":{{.RestartCount}},"started_at":"{{.State.StartedAt}}"}' "$id" > "$OUT_DIR/$service.json"
  fi
done
API_URL="${API_URL:-http://127.0.0.1:8000}"
local_url "$API_URL"
export API_URL OUT_DIR
python "$EP_ROOT/scripts/collect_health.py"
printf 'Sanitized diagnostics saved: %s\n' "$OUT_DIR"

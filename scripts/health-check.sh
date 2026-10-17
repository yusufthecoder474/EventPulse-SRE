#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
require curl
API_URL="${API_URL:-http://127.0.0.1:8000}"
local_url "$API_URL"
for endpoint in live ready; do
  code="$(curl --noproxy '*' --connect-timeout 2 --max-time "${HEALTH_TIMEOUT:-5}" --output /dev/null --write-out '%{http_code}' "$API_URL/health/$endpoint")" || { printf '%s probe transport failure\n' "$endpoint" >&2; exit 1; }
  [[ "$code" == 200 ]] || { printf '%s probe returned HTTP %s\n' "$endpoint" "$code" >&2; exit 1; }
  printf '%s probe: HTTP %s\n' "$endpoint" "$code"
done

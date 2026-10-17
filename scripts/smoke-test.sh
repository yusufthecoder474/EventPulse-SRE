#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
require python
require curl
API_URL="${API_URL:-http://127.0.0.1:8000}"
export API_URL
local_url "$API_URL"
bash "$EP_ROOT/scripts/health-check.sh"
python "$EP_ROOT/scripts/smoke.py"

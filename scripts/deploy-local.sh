#!/usr/bin/env bash
# An in-place local/EC2-host Compose deployment, NOT a zero-downtime rollout.
set -Eeuo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
require docker
require git
require python
[[ "${DEPLOY_LOCAL_APPROVED:-}" == yes ]] || { printf 'Set DEPLOY_LOCAL_APPROVED=yes on the intended local host after reviewing this script.\n' >&2; exit 2; }
[[ -z "$(git -C "$EP_ROOT" status --porcelain)" ]] || { printf 'Working tree must be clean.\n' >&2; exit 1; }
REVISION="${REVISION:?Set REVISION to a reviewed full 40-character commit SHA already checked out}"
[[ "$REVISION" =~ ^[0-9a-f]{40}$ ]] || { printf 'Full commit SHA required.\n' >&2; exit 2; }
[[ "$(git -C "$EP_ROOT" rev-parse HEAD)" == "$REVISION" ]] || { printf 'Checkout the requested revision explicitly before deployment.\n' >&2; exit 2; }
compose config --quiet
compose build api web
compose up -d --wait --wait-timeout 180
bash "$EP_ROOT/scripts/verify-stack.sh"
printf 'Verified in-place deployment at %s; no zero-downtime guarantee.\n' "$REVISION"

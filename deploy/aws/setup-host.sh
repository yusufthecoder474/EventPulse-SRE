#!/usr/bin/env bash
# Run manually only on an explicitly approved EC2 host. No cloud resources created here.
set -Eeuo pipefail
[[ "${EC2_SETUP_APPROVED:-}" == yes ]] || { printf 'Review costs and host identity, then set EC2_SETUP_APPROVED=yes.\n' >&2; exit 2; }
command -v dnf >/dev/null || { printf 'This setup targets Amazon Linux 2023.\n' >&2; exit 2; }
command -v sudo >/dev/null || exit 127
sudo dnf install -y docker git python3
sudo systemctl enable --now docker
printf 'Docker installed. Install Compose v2 from official Docker instructions for x86_64, verify its checksum and docker compose version.\n'
printf 'Clone the repository, check out a reviewed SHA, then follow docs/AWS_DEPLOYMENT.md. No AWS keys are needed inside containers.\n'

"""Generate local credentials once; never commit the output."""

from pathlib import Path
import secrets

p = Path(__file__).resolve().parents[1] / ".env"
if p.exists():
    raise SystemExit(".env exists; preserving your settings.")
p.write_text(
    f"POSTGRES_PASSWORD={secrets.token_hex(24)}\nGRAFANA_PASSWORD={secrets.token_hex(24)}\nFAULT_TOKEN={secrets.token_hex(24)}\nENABLE_FAULTS=false\nAPP_ENV=local\n"
)
try:
    p.chmod(0o600)
except OSError:
    pass
print(
    "Created .env. Keep it local. Grafana user: admin; password: GRAFANA_PASSWORD in .env."
)

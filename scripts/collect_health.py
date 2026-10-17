"""Capture bounded health data without secrets or application records."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

out = {"observed_at": datetime.now(timezone.utc).isoformat(), "health": {}}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for path in ("/health/live", "/health/ready"):
    try:
        with opener.open(os.environ["API_URL"] + path, timeout=3) as response:
            out["health"][path] = {"status": response.status}
    except urllib.error.HTTPError as error:
        out["health"][path] = {"status": error.code}
    except OSError:
        out["health"][path] = {"status": None, "error": "transport unavailable"}
Path(os.environ["OUT_DIR"], "health.json").write_text(json.dumps(out, indent=2))

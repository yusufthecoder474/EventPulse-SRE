"""Inspect staged paths and common real credential patterns before publication."""

import re
import subprocess

paths = (
    subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z"]
    )
    .decode()
    .split("\0")
)
problems = []
for path in filter(None, paths):
    if (
        (path.split("/")[-1].startswith(".env") and path != ".env.example")
        or path.endswith((".db", ".pem", ".key"))
        or "node_modules/" in path
    ):
        problems.append(path + ": excluded file staged")
        continue
    data = subprocess.check_output(["git", "show", ":" + path])
    if path.endswith((".png", ".jpg", ".zip")):
        continue
    text = data.decode(errors="replace")
    patterns = [
        r"gh[pousr]_[A-Za-z0-9]{30,}",
        r"github_pat_[A-Za-z0-9_]{30,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    if any(re.search(pattern, text) for pattern in patterns):
        problems.append(path + ": possible real credential pattern")
if problems:
    raise SystemExit("\n".join(problems))
print(
    f"Checked {len(list(filter(None, paths)))} staged paths; no excluded files or common credential patterns detected. Test-only constants and empty placeholders are intentional."
)

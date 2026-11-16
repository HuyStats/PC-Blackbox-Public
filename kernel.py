"""Collect a bounded kernel-log window and select troubleshooting messages."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

folder = Path(__file__).resolve().parent

result = subprocess.run(
    ["sudo", "journalctl", "-k", "-b", "--no-pager",
     "-o", "short-iso", "-n", "2000"],
    capture_output=True,
    text=True,
    check=True,
    timeout=15,
)

patterns = [
    "i/o error",
    "pcie bus error",
    "aer:",
    "hardware error",
    "timed out",
    "timeout",
    "reset controller",
    "gpu fault",
    "gpu hang",
    "nvrm: xid",
    "link is down",
    "usb disconnect",
]

matches = [
    line
    for line in result.stdout.splitlines()
    if any(pattern in line.lower() for pattern in patterns)
]

record = {
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "scope": "Latest 2000 available kernel entries from this boot",
    "patterns": patterns,
    "matches": matches,
    "collection_notice": result.stderr.strip(),
}

(folder / "kernel.log").write_text(result.stdout)
(folder / "kernel.json").write_text(json.dumps(record, indent=2))

print("Saved kernel.log and kernel.json")
print(f"Selected messages: {len(matches)}")
print("Matches are troubleshooting leads, not confirmed failures.")

for line in matches[-10:]:
    print(line)

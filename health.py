"""Read one NVMe controller health log and append a timestamped health record."""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 health.py /dev/nvme0")

folder = Path(__file__).resolve().parent

device = sys.argv[1]

result = subprocess.run(
    ["sudo", "nvme", "smart-log", device, "-o", "json"],
    capture_output=True,
    text=True,
    check=True,
    timeout=15,
)

health = json.loads(result.stdout)

temperature_c = health["temperature"] - 273.15

print(f"Device: {device}")
print(f"Temperature: {temperature_c:.1f} °C")
print(f"Estimated endurance used: {health['percent_used']}%")
print(f"Media errors: {health['media_errors']}")
print(f"Lifetime error-log entries: {health['num_err_log_entries']}")

warnings = []

if health["critical_warning"] != 0:
    warnings.append(
        f"Critical warning flags set: {health['critical_warning']}"
    )

if health["avail_spare"] < health["spare_thresh"]:
    warnings.append("Available spare is below the drive's threshold")

if health["percent_used"] >= 100:
    warnings.append("Estimated endurance has been consumed")

if health["media_errors"] > 0:
    warnings.append("Drive reports unrecovered media/data-integrity errors")

if warnings:
    for warning in warnings:
        print(f"WARNING: {warning}")
else:
    print("No selected SMART warning conditions detected.")

identity_result = subprocess.run(
    ["sudo", "nvme", "id-ctrl", device, "-o", "json"],
    capture_output=True,
    text=True,
    check=True,
    timeout=15,
)

identity = json.loads(identity_result.stdout)

record = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "device": device,
    "serial": identity["sn"].strip(),
    "model": identity["mn"].strip(),
    "temperature_c": round(temperature_c, 1),
    "warnings": warnings,
    "smart": health,
}

with open(folder / "health.jsonl", "a") as file:
    file.write(json.dumps(record) + "\n")

print("Health record saved in health.jsonl")

"""Scan disks, preserve an initial baseline, and append timestamped observations."""

from datetime import datetime, timezone
import json
import subprocess
import sys
from pathlib import Path

folder = Path(__file__).resolve().parent

result = subprocess.run(
    ["lsblk", "--json", "--nodeps",
     "--output", "NAME,SIZE,MODEL,SERIAL,TRAN,TYPE"],
    capture_output=True,
    text=True,
    check=True,
    timeout=15,
)

inventory = json.loads(result.stdout)

disks = [
    device
    for device in inventory["blockdevices"]
    if device["type"] == "disk"
]

print(json.dumps(disks, indent=2))


baseline = {
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "disks": disks,
}

try:
    with open(folder / "baseline.json", "x") as file:
        json.dump(baseline, file, indent=2)
    print("Saved baseline.json")
except FileExistsError:
    print("Baseline already exists. Keeping the original.")

with open(folder / "baseline.json", "r") as file:
    saved_baseline = json.load(file)

current_serials = {
    disk["serial"]
    for disk in disks
    if disk.get("serial")
}
if "--simulate-missing" in sys.argv:
    simulated_serial = next(iter(sorted(current_serials)), None)

    if simulated_serial:
        current_serials.remove(simulated_serial)
        print(
            "\nSIMULATION: treating disk with serial "
            f"{simulated_serial} as missing"
        )

print("\nBaseline comparison:")

for disk in saved_baseline["disks"]:
    serial = disk.get("serial")

    if not serial:
        print(f"UNKNOWN: {disk['model']} has no serial number")
    elif serial in current_serials:
        print(f"PRESENT: {disk['model']}")
    else:
        print(f"MISSING: {disk['model']} (serial: {serial})")

with open("/proc/uptime", "r") as file:
    uptime_seconds = float(file.read().split()[0])

scan_record = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "simulation": "--simulate-missing" in sys.argv,
    "uptime_seconds": uptime_seconds,
    "detected_serials": sorted(current_serials),
    "missing_serials": [
        disk["serial"]
        for disk in saved_baseline["disks"]
        if disk.get("serial")
        and disk["serial"] not in current_serials
    ],
}

with open(folder / "scans.jsonl", "a") as file:
    file.write(json.dumps(scan_record) + "\n")

print("Scan recorded in scans.jsonl")

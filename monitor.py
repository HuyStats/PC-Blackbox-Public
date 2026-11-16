"""Repeat inventory scans and record disk appearance and disappearance events."""

import subprocess
import sys
import time
import json
from collections import deque
from pathlib import Path

project_folder = Path(__file__).resolve().parent

print("Monitoring every 10 seconds. Press Ctrl+C to stop.", flush=True)
previous_serials = None
try:
    while True:
        try:
            result = subprocess.run(
                [sys.executable, "inventory.py"],
                cwd=project_folder,
                timeout=45,
            )
        except subprocess.TimeoutExpired:
            print("Scan timed out. Resetting event comparison.", flush=True)
            previous_serials = None
            time.sleep(10)
            continue

        if result.returncode != 0:
            print("Scan failed. Check the error above.", flush=True)
            previous_serials = None
        else:
            with open(project_folder / "scans.jsonl", "r") as file:
                latest_scan = json.loads(deque(file, maxlen=1)[0])

            if latest_scan.get("simulation"):
                print("Skipping simulated scan for live event comparison.", flush=True)
                previous_serials = None
                time.sleep(10)
                continue

            current_serials = set(latest_scan["detected_serials"])

            if previous_serials is not None:
                disappeared = previous_serials - current_serials
                appeared = current_serials - previous_serials

                for event_type, serials in [
                    ("disappeared", disappeared),
                    ("appeared", appeared),
                ]:
                    for serial in sorted(serials):
                        event = {
                            "timestamp": latest_scan["timestamp"],
                            "event": event_type,
                            "serial": serial,
                            "simulation": latest_scan["simulation"],
                        }

                        with open(
                            project_folder / "events.jsonl", "a"
                        ) as file:
                            file.write(json.dumps(event) + "\n")

                        print(f"EVENT: {serial} {event_type}", flush=True)

            previous_serials = current_serials

        time.sleep(10)

except KeyboardInterrupt:
    print("\nMonitoring stopped.")

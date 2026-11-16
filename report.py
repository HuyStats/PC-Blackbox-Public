"""Build a Markdown report from saved observations without rescanning hardware."""

import json
from pathlib import Path
from collections import deque

folder = Path(__file__).resolve().parent

def latest_record(filename):
    path = folder / filename
    if not path.exists():
        return None
    with path.open() as stream:
        lines = deque((line for line in stream if line.strip()), maxlen=1)
    return json.loads(lines[0]) if lines else None


scan = latest_record("scans.jsonl")
if scan is None:
    raise SystemExit("No saved disk scan. Run python3 inventory.py first.")

health = latest_record("health.jsonl")

report = f"""# PC Hardware Black Box

## Last disk scan
Time: {scan["timestamp"]}
Simulation: {scan["simulation"]}
System uptime: {scan["uptime_seconds"]} seconds
Detected disk serials: {", ".join(scan["detected_serials"])}
Missing baseline disk serials: {", ".join(scan["missing_serials"]) or "None"}

These are saved observations collected at the times shown.
"""

if health is not None:
    report += f"""
## Last saved SSD health reading
Time: {health["timestamp"]}
Model: {health["model"]}
Serial: {health["serial"]}
Temperature: {health["temperature_c"]} °C
Estimated endurance used: {health["smart"]["percent_used"]}%
Media errors: {health["smart"]["media_errors"]}
Warnings: {"; ".join(health["warnings"]) or "No selected warning conditions detected"}
"""
    if health["serial"] not in scan["detected_serials"]:
        report += "\nThis SSD was not in the last scan's detected serials; its saved health reading is historical.\n"
else:
    report += "\n## Last saved SSD health reading\nNot collected yet. Run health.py for an NVMe controller.\n"


events_path = folder / "events.jsonl"

report += "\n## Recent device changes\n\n"

if events_path.exists():
    with events_path.open() as stream:
        event_lines = list(deque((line for line in stream if line.strip()), maxlen=10))

    for line in event_lines[-10:]:
        event = json.loads(line)
        report += (
            f"- {event['timestamp']}: "
            f"{event['serial']} {event['event']} "
            f"(simulation: {event['simulation']})\n"
        )
else:
    report += "No device-change events recorded.\n"

kernel_path = folder / "kernel.json"

report += "\n## Selected kernel messages\n\n"

if kernel_path.exists():
    kernel = json.loads(kernel_path.read_text())

    report += f"Collected: {kernel['collected_at']}\n"
    report += f"Scope: {kernel['scope']}\n"
    report += "Matches are troubleshooting leads, not confirmed failures.\n"

    if kernel["collection_notice"]:
        report += f"Collection notice: {kernel['collection_notice']}\n"

    if kernel["matches"]:
        report += "\n```text\n"
        report += "\n".join(kernel["matches"][-20:])
        report += "\n```\n"
    else:
        report += "\nNo selected patterns found in the collected log window.\n"
else:
    report += "Kernel logs have not been collected yet.\n"

hardware_path = folder / "hardware.json"

report += "\n## Hardware overview\n\n"

if hardware_path.exists():
    hardware = json.loads(hardware_path.read_text())

    report += f"Collected: {hardware['collected_at']}\n"

    for name, output in hardware["sections"].items():
        title = {"cpu": "CPU", "pci_devices": "PCI Devices"}.get(
            name, name.replace("_", " ").title()
        )
        report += f"\n### {title}\n"
        report += f"\n```text\n{output}\n```\n"
else:
    report += "Hardware information has not been collected yet.\n"

(folder / "report.md").write_text(report)
print(report)
print("Saved report.md")

"""Collect CPU, motherboard, PCI device, and network interface information."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

folder = Path(__file__).resolve().parent

commands = {
    "cpu": ["lscpu"],
    "motherboard": ["sudo", "dmidecode", "-t", "baseboard"],
    "pci_devices": ["lspci", "-nn"],
    "network_interfaces": ["ip", "-br", "link"],
}

hardware = {
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "sections": {},
}

for name, command in commands.items():
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        hardware["sections"][name] = result.stdout.strip()
        print(f"Collected: {name}")

    except subprocess.CalledProcessError as error:
        hardware["sections"][name] = (
            f"Collection failed: {error.stderr.strip()}"
        )
        print(f"Failed: {name}")

    except (OSError, subprocess.TimeoutExpired) as error:
        hardware["sections"][name] = f"Collection unavailable: {error}"
        print(f"Unavailable: {name}")

(folder / "hardware.json").write_text(
    json.dumps(hardware, indent=2)
)

print("Saved hardware.json")


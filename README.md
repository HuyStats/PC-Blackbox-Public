# PC Hardware Black Box

A small Linux hardware diagnostic and monitoring project written in Python. It records disk presence, NVMe health information, and selected kernel messages, then combines the saved observations into a Markdown troubleshooting report.

Built as a personal project to develop Linux troubleshooting skills and investigate intermittent device detection. This is a prototype, with six separate scripts so each collection step stays easy to inspect.

**The report in [examples/report.md](examples/report.md) uses synthetic data only.** No real machine logs or hardware identifiers are included in this public source package.

## Features

- Inventory CPU, motherboard, PCI devices (including GPUs and network controllers), and network interfaces.
- Save an initial disk baseline and compare later scans by disk serial number.
- Poll every 10 seconds and record disks appearing or disappearing.
- Record scan timestamps and system uptime.
- Read a selected NVMe controller's SMART health log and identity.
- Save the latest 2000 available kernel messages from the current boot and select messages using a short keyword list.
- Generate a Markdown report from the saved observations, with separate collection timestamps.

## Requirements

- Ubuntu Desktop or a compatible Linux environment; Python 3.8 or newer.
- Linux command-line utilities listed below.
- Permission to read NVMe health data, motherboard firmware information, and kernel logs. The relevant commands invoke `sudo`.

No third-party Python packages are required. On Ubuntu:

```bash
sudo apt update
sudo apt install pciutils dmidecode nvme-cli util-linux iproute2
```

`journalctl` must also be available with a readable system journal. This project does not provide a fallback for distributions without it.

## Run a diagnostic collection

Open a terminal in the project folder. Run each step individually and check that it succeeds before building the report:

```bash
python3 inventory.py
python3 health.py /dev/nvme0
python3 kernel.py
python3 hardware.py
python3 report.py
```

`/dev/nvme0` is an example controller path. Identify the appropriate controller with `sudo nvme list` first; names can change across machines or boots. On a computer without NVMe storage, skip `health.py`; the report will say no health reading has been collected. This version reports only the latest saved health record, even if you query multiple controllers.

All generated files are saved beside the scripts, regardless of the terminal's working directory. Use a separate project copy and baseline for each computer. The baseline is created on the first successful inventory scan and is never automatically overwritten. Only attach devices you want in the initial baseline. A live Ubuntu boot USB will be included if detected.

The commands collect information; they do not repair drives, change hardware settings, run disk self-tests, or install an operating system. The Python scripts write their output files beside the source code. In a standard live Ubuntu session, save code and any wanted measurements to persistent storage before shutdown.

## Monitor disk changes

```bash
python3 monitor.py
```

Press **Ctrl+C** to stop. This repeats `inventory.py`; it does not automatically refresh health, kernel logs, hardware overview, or the report. Run those scripts separately when needed.

A first successful scan establishes the comparison state. Later scans compare disk serials with the previous successful scan. If a scan fails or times out, the comparison state is reset to avoid recording a command failure as a disk disappearance. The first successful scan after that reset establishes a new state. Baseline comparison still checks the original baseline.

To check changes using a spare USB drive:

1. Start monitoring and wait for a completed scan.
2. Connect the spare USB and leave it attached for at least one complete scan.
3. If mounted, unmount its volume before removing it. Keep the live Ubuntu boot drive connected.
4. Wait for another scan and check `events.jsonl` for `appeared` and `disappeared` observations.
5. Run `python3 report.py` to include the saved events in the report.

The USB needs a usable, unique serial number for this prototype's comparison logic.

## Scripts and generated files

| Script | Purpose | Output |
|---|---|---|
| `inventory.py` | Disk inventory, original-baseline comparison, uptime | `baseline.json`, `scans.jsonl` |
| `monitor.py` | Repeat inventory and record device changes | `events.jsonl`, additional scan records |
| `health.py` | NVMe health and controller identity | `health.jsonl` |
| `kernel.py` | Collect kernel text and select messages | `kernel.log`, `kernel.json` |
| `hardware.py` | CPU, motherboard, PCI, network inventory | `hardware.json` |
| `report.py` | Summarize saved results without rescanning | `report.md` |

JSONL files contain one JSON record per line. `report.py` uses the latest disk scan and health record, the latest collected kernel/hardware files, and up to 10 recent device-change events. Old measurements remain old measurements; timestamps are shown so they are not mistaken for current readings.

## What the results mean

- **Detected** means visible to the inventory command at collection time. It does not mean healthy.
- **Missing** means a baseline serial number was absent from the scan. This does not prove physical drive failure.
- **Appeared/disappeared** means detected presence changed between polls. Timestamps mark observations, not the exact physical event. Changes entirely between polls can be missed.
- **No selected SMART warning conditions** means the script found none of its checks: nonzero critical-warning flags, spare below the drive threshold, estimated endurance used at least 100%, or nonzero unrecovered media/data-integrity errors.
- **Estimated endurance used** is a manufacturer estimate, not filesystem space used or a prediction of remaining years.
- **Lifetime error-log entries** are displayed as context. A nonzero count alone is not classified as drive failure. Detailed NVMe error-log diagnosis is outside this script.
- **Selected kernel messages** are keyword matches for review. An intentional USB removal can be a match. No matches does not establish that the entire system is problem-free. Only the collected log window was searched.
- Individual command failures in `hardware.py` are saved as unavailable/failed sections. Other collectors generally stop with an error if a required command, field, or file is unavailable. A failed collection does not refresh an older result; inspect the command's output and the report's timestamps.

## Public repository and local data

The supplied `.gitignore` excludes the generated files at the project root. They can contain hardware serial numbers, MAC addresses, hostnames, and other device details. Keep real baselines and reports in a private backup. The `examples/` directory contains only invented demonstration data.

For this project, publish this clean source folder to a **new repository**, keeping the original private repository as a backup. Do not copy old generated files or the old repository's `.git` directory into the public folder. An ignore rule does not remove files already committed, does not erase earlier history, and is not a substitute for reviewing files before publication. GitHub's web uploader can also accept files that a local `.gitignore` would exclude; upload only this clean package's contents.

## Testing and development

The original scripts were manually tested on an HP laptop running live Ubuntu: hardware collection, NVMe SMART reads, report generation, and real USB removal/reconnection were exercised. This cleaned version retains those separate scripts. It has automated checks with synthetic command results; the cleaned version has not yet been rerun on that laptop.

```bash
python3 -m unittest discover -s tests -v
```

The tests run copies of the scripts in temporary folders with mocked hardware-command output. They do not access or modify physical storage devices.

The project was developed with AI assistance for code generation, debugging, and documentation. Hardware testing and output review were performed manually. See [CHANGES.md](CHANGES.md) for the small changes made while preparing the public version.

## Current limits

- No BMC/IPMI, Redfish, external availability monitoring, stress testing, or PCIe negotiated-link analysis.
- Automated baseline comparison covers disks only. Other hardware is inventoried for review.
- No automatic machine-identity guard: keep each computer's baseline in a separate project copy.
- Serial matching assumes usable, unique identifiers. Missing serials are reported as unknown; duplicate serials can be conflated. WWN-based matching is not implemented.
- The monitor can log only while its process and the computer are running. It does not establish why a device disappeared or why a computer stopped responding.
- Use only one monitor per project directory. Concurrent writers and mid-write interruption are not handled transactionally.
- Kernel filtering is a simple keyword list; it is not a full error classifier. The report shows up to 20 selected kernel lines; `kernel.json` contains all matches from the collected window.

## References

- [nvme-cli](https://github.com/linux-nvme/nvme-cli)
- [NVMe SMART field definitions](https://learn.microsoft.com/en-us/windows/win32/api/nvme/ns-nvme-nvme_health_info_log)
- [journalctl documentation](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)

# Changes for the public version

The original six-script design is retained. There is no replacement application or new framework.

- Added a one-sentence description at the top of each script and removed trailing whitespace.
- Made inventory and health output paths relative to their script, matching the other collectors. Running from a different terminal directory now uses the same baseline and logs.
- Added a 15-second timeout to `lsblk` and a 45-second inventory-subprocess timeout in the monitor. Timed-out scans reset event-comparison state instead of generating disappearance events.
- Made the simulated missing-disk selection deterministic by sorting serials. Simulation remains explicitly labeled.
- The monitor skips simulated scan records for live device-change comparison.
- Read the last scan/event records with a bounded deque instead of loading the complete log into memory.
- Allowed report generation when no health record exists yet; a missing disk scan still produces a clear instruction to run inventory first.
- Added a report note when the saved SSD health serial was absent from the last disk scan. This is a historical-data warning, not a failure diagnosis.
- Improved report heading spacing and CPU/PCI capitalization.
- Added setup, usage, interpretation, testing, limitations, and AI-assistance notes.
- Added `.gitignore` rules for generated data, plus synthetic examples and tests.

No real baselines, health records, kernel logs, MAC addresses, motherboard serials, or device serial numbers are included. Example identifiers beginning with `DEMO-` are invented.

Before using this cleaned copy as your working version, rerun its collectors and USB event test on your laptop. Keep the original private backup intact.

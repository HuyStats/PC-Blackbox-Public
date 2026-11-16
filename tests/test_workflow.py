"""Synthetic command results only; no hardware commands are executed."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
DISK = {'name': 'nvme0n1', 'size': '100G', 'model': 'Example NVMe SSD',
        'serial': 'DEMO-SSD-001', 'tran': 'nvme', 'type': 'disk'}
USB = {'name': 'sdb', 'size': '16G', 'model': 'Example USB',
       'serial': 'DEMO-USB-001', 'tran': 'usb', 'type': 'disk'}
SMART = {'temperature': 303, 'critical_warning': 0, 'avail_spare': 100,
         'spare_thresh': 5, 'percent_used': 2, 'media_errors': 0, 'num_err_log_entries': 3}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        for script in ROOT.glob('*.py'):
            shutil.copy2(script, self.folder / script.name)
        self.devices = [dict(DISK)]
        self.original_open = open

    def fake_open(self, path, *args, **kwargs):
        if str(path) == '/proc/uptime':
            return io.StringIO('1200.0 300.0\n')
        return self.original_open(path, *args, **kwargs)

    def fake_command(self, args, **kwargs):
        tool = args[1] if args[0] == 'sudo' else args[0]
        if tool == 'lsblk':
            value = json.dumps({'blockdevices': self.devices})
        elif tool == 'nvme' and 'smart-log' in args:
            value = json.dumps(SMART)
        elif tool == 'nvme' and 'id-ctrl' in args:
            value = json.dumps({'sn': 'DEMO-SSD-001 ', 'mn': 'Example NVMe SSD '})
        elif tool == 'journalctl':
            value = '2026-01-01T00:00:10+00:00 demo-host kernel: USB disconnect, device number 2\n'
        elif tool == 'lscpu':
            value = 'Architecture: x86_64\nModel name: Example CPU\n'
        elif tool == 'dmidecode':
            value = 'Manufacturer: Example Vendor\nProduct Name: Example Board\n'
        elif tool == 'lspci':
            value = '01:00.0 VGA compatible controller: Example GPU\n'
        elif tool == 'ip':
            value = 'demo0 DOWN\n'
        else:
            raise AssertionError('Unexpected command: ' + repr(args))
        return subprocess.CompletedProcess(args, 0, value, '')

    def execute(self, script, args=(), command=None):
        output = io.StringIO()
        with patch.object(sys, 'argv', [script, *args]), \
             patch('subprocess.run', side_effect=command or self.fake_command), \
             patch('builtins.open', side_effect=self.fake_open), \
             contextlib.redirect_stdout(output):
            runpy.run_path(str(self.folder / script), run_name='__main__')
        return output.getvalue()

    def test_collectors_and_report_use_script_directory(self):
        # The test runner's CWD is outside the temporary project directory.
        for script, args in [('inventory.py', ()), ('health.py', ('/dev/nvme0',)),
                             ('kernel.py', ()), ('hardware.py', ()), ('report.py', ())]:
            self.execute(script, args)
        report = (self.folder / 'report.md').read_text()
        self.assertIn('DEMO-SSD-001', report)
        self.assertIn('29.9 °C', report)
        self.assertIn('Example GPU', report)
        self.assertIn('USB disconnect', report)
        self.assertIn('## Hardware overview', report)

    def test_baseline_preserved_and_serial_survives_name_change(self):
        self.execute('inventory.py')
        baseline = (self.folder / 'baseline.json').read_bytes()
        self.devices[0]['name'] = 'nvme3n1'
        self.execute('inventory.py')
        self.assertEqual(baseline, (self.folder / 'baseline.json').read_bytes())
        latest = json.loads((self.folder / 'scans.jsonl').read_text().splitlines()[-1])
        self.assertEqual(latest['missing_serials'], [])

    def test_simulation_is_labeled_and_does_not_change_baseline(self):
        self.execute('inventory.py')
        baseline = (self.folder / 'baseline.json').read_bytes()
        self.execute('inventory.py', ('--simulate-missing',))
        record = json.loads((self.folder / 'scans.jsonl').read_text().splitlines()[-1])
        self.assertTrue(record['simulation'])
        self.assertEqual(record['missing_serials'], ['DEMO-SSD-001'])
        self.assertEqual(baseline, (self.folder / 'baseline.json').read_bytes())

    def test_report_without_optional_collectors(self):
        self.execute('inventory.py')
        self.execute('report.py')
        report = (self.folder / 'report.md').read_text()
        self.assertIn('Not collected yet', report)
        self.assertIn('Kernel logs have not been collected', report)

    def test_report_without_scan_has_clear_instruction(self):
        with self.assertRaises(SystemExit) as error:
            self.execute('report.py')
        self.assertIn('inventory.py', str(error.exception))

    def test_report_marks_health_of_absent_disk_historical(self):
        self.execute('health.py', ('/dev/nvme0',))
        self.devices = [dict(USB)]
        self.execute('inventory.py')
        self.execute('report.py')
        self.assertIn('historical', (self.folder / 'report.md').read_text())

    def test_failed_inventory_does_not_append_false_empty_scan(self):
        self.execute('inventory.py')
        before = (self.folder / 'scans.jsonl').read_bytes()
        def fail(args, **kwargs):
            raise subprocess.CalledProcessError(1, args, stderr='SYNTHETIC command failure')
        with self.assertRaises(subprocess.CalledProcessError):
            self.execute('inventory.py', command=fail)
        self.assertEqual(before, (self.folder / 'scans.jsonl').read_bytes())

    def monitor_sequence(self, sequence):
        count = 0
        def command(args, **kwargs):
            nonlocal count
            if args[0] == sys.executable:
                item = sequence[count]
                count += 1
                if item == 'failed':
                    return subprocess.CompletedProcess(args, 1)
                if item == 'timeout':
                    raise subprocess.TimeoutExpired(args, 45)
                self.devices = item
                self.execute('inventory.py')
                return subprocess.CompletedProcess(args, 0)
            return self.fake_command(args, **kwargs)
        def sleep(seconds):
            if count >= len(sequence):
                raise KeyboardInterrupt()
        with patch('time.sleep', side_effect=sleep):
            self.execute('monitor.py', command=command)

    def test_monitor_records_removal_and_return(self):
        self.monitor_sequence([[dict(DISK), dict(USB)], [dict(DISK)], [dict(DISK), dict(USB)]])
        events = [json.loads(line) for line in (self.folder / 'events.jsonl').read_text().splitlines()]
        self.assertEqual([event['event'] for event in events], ['disappeared', 'appeared'])
        self.assertTrue(all(event['serial'] == 'DEMO-USB-001' for event in events))

    def test_monitor_failed_scan_resets_comparison(self):
        self.monitor_sequence([[dict(DISK), dict(USB)], 'failed', [dict(DISK)]])
        self.assertFalse((self.folder / 'events.jsonl').exists())

    def test_monitor_timeout_resets_comparison(self):
        self.monitor_sequence([[dict(DISK), dict(USB)], 'timeout', [dict(DISK)]])
        self.assertFalse((self.folder / 'events.jsonl').exists())


if __name__ == '__main__':
    unittest.main()

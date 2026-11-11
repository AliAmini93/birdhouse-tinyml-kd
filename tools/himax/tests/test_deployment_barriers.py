"""Targeted new audit tests; no previous inference/build/packaging suites rerun."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import audit_deployment_barriers as audit
from postlink_audit import elf_sections, read_elf_bytes


class BarrierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf = audit.regular_file(audit.REPO / audit.ELF_REL)
        assert audit.fingerprint(cls.elf)['sha256'] == audit.ELF_SHA
        tool = lambda n: str(audit.regular_file(audit.REPO / audit.TC_REL / ('arc-elf32-' + n)))
        raw = subprocess.run([tool('objdump'), '-d', '-C', '--no-show-raw-insn', str(cls.elf)],
                             capture_output=True, text=True, check=True).stdout
        cls.funcs = audit.functions(raw)
        cls.sections = elf_sections(tool, str(cls.elf))
        cls.loader_raw = audit.first_loader_disassembly(audit.REPO / audit.SDK_REL)

    def read_bytes(self, addr, size):
        return read_elf_bytes(self.sections, str(self.elf), addr, size)

    def test_actual_binary_control_flow(self):
        report = audit.pdm_findings(self.funcs, self.read_bytes)
        self.assertEqual(len(report['checks']), 16)
        self.assertTrue(all(x['status'] == 'PASS' for x in report['checks']), report['checks'])
        self.assertEqual(report['open_risks'][0]['status'], 'OPEN')

    def test_internal_branches_are_not_external_calls(self):
        self.assertNotIn('io_pdm_rx_read+0x90', audit.callees(self.funcs['io_pdm_rx_read']))

    def test_interrupt_enable_mutation_is_rejected(self):
        funcs = copy.deepcopy(self.funcs)
        funcs['io_pdm_rx_read']['body'] += '\n1002a458:\tseti\tr0\n'
        report = audit.pdm_findings(funcs, self.read_bytes)
        self.assertTrue(any(x['status'] == 'FAIL' for x in report['checks']))

    def test_unknown_helper_mutation_is_rejected(self):
        funcs = copy.deepcopy(self.funcs)
        funcs['io_pdm_rx_read']['body'] += '\n1002a458:\tbl\t1\t;10030000 <unreviewed_wait_helper>\n'
        report = audit.pdm_findings(funcs, self.read_bytes)
        self.assertGreaterEqual(sum(x['status'] == 'FAIL' for x in report['checks']), 2)

    def test_wrong_switch_table_is_rejected(self):
        report = audit.pdm_findings(self.funcs, lambda addr, size: bytes(size))
        self.assertTrue(any(x['status'] == 'FAIL' for x in report['checks']))

    def test_cached_transport_facts_without_identifiers(self):
        path = audit.REPO / '.local-tools/diagnostics/grove-ai-v1/kernel_grove_full.log'
        r = audit.summarize_saved_kernel(audit.regular_file(path).read_text())
        self.assertEqual(r['reset_events'], 22)
        self.assertEqual(r['failed_read10_commands'], 1)
        self.assertEqual(r['observed_product_ids'], ['0060', '8060'])
        self.assertEqual(len(r['reset_intervals_in_25_to_35_second_band']), 16)
        # Check against actual cached identifiers without printing them on failure.
        serials = [line.split('SerialNumber: ', 1)[1] for line in path.read_text().splitlines()
                   if 'SerialNumber: ' in line]
        self.assertTrue(all(value not in json.dumps(r) for value in serials))
        self.assertIn('Not established', r['causation'])

    def test_actual_loader_call_order(self):
        r = audit.first_loader_findings(self.loader_raw)
        self.assertTrue(all(r['checks'].values()), r['checks'])
        self.assertIn('ACK is not burn completion', r['conclusion'])

    def test_loader_mutations_fail(self):
        # Directly mutate the real disassembly: do not test a made-up receiver.
        for before, after in [('200015ae:', '200015af:'), ('20009c82:', '20009c83:'),
                              ('200016b2:', '200016b3:'), ('200015c6:', '200015c7:')]:
            with self.subTest(instruction=before):
                bad = self.loader_raw.replace(before, after)
                self.assertNotEqual(bad, self.loader_raw)
                self.assertFalse(all(audit.first_loader_findings(bad)['checks'].values()))

    def test_observer_defaults_and_scope(self):
        self.assertEqual(audit.observer_admission({})['status'], 'NO-GO')
        for malformed in [None, [], 'approved']:
            self.assertEqual(audit.observer_admission(malformed)['status'], 'NO-GO')
        keys = audit.observer_admission({})['missing_prerequisites']
        record = {k: True for k in keys}
        record['requested_actions'] = ['read_cached_kernel_journal', 'read_cached_usb_identity']
        self.assertEqual(audit.observer_admission(record)['status'], 'REVIEW_READY')
        for malformed in [None, True, 'read_cached_kernel_journal', [{}]]:
            bad = dict(record); bad['requested_actions'] = malformed
            self.assertEqual(audit.observer_admission(bad)['status'], 'NO-GO')
        for key in keys:
            if key == 'explicit_requested_actions': continue
            bad = dict(record); bad[key] = 'yes'
            self.assertEqual(audit.observer_admission(bad)['status'], 'NO-GO')
        for action in ['open_cdc_rx', 'mount_readonly', 'i2c_scan', 'set_1200_baud', 'reset', 'flash']:
            bad = dict(record); bad['requested_actions'] = [action]
            self.assertEqual(audit.observer_admission(bad)['status'], 'NO-GO')

    def test_regular_file_guard_and_recovery_limits(self):
        # Local FIFO is rejected by stat, without opening it or touching /dev.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): audit.regular_file(tmp)
            fifo = Path(tmp) / 'not-a-regular-file'
            os.mkfifo(fifo)
            with self.assertRaises(ValueError): audit.regular_file(fifo)
        report = audit.recovery_findings(audit.REPO / audit.SDK_REL)
        self.assertTrue(all(report['checks'].values()))
        self.assertEqual(report['recovery_capability'], 'UNTESTED / NOT ESTABLISHED')


if __name__ == '__main__':
    unittest.main()

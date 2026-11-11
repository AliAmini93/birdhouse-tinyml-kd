"""Adversarial checks against real preserved candidate files and pure audit logic."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import package_offline as pkg
import uf2_tool as uf2
import verify_tflm_ops as ops
import run_offline_checks as runner


class ToolsTest(unittest.TestCase):
    def test_no_inherited_passes(self):
        self.assertEqual(runner.overall_status([]), "PARTIAL")
        self.assertEqual(runner.overall_status([{'status': 'PASS'}, {'status': 'NOT_RUN'}]), "PARTIAL")
        self.assertEqual(runner.overall_status([{'status': 'PASS'}, {'status': 'FAIL'}]), "FAIL")

    def test_interleaved_warning_attribution(self):
        vendor = "repo/firmware/himax_arc/birdhouse/bh_model.cc -o obj " + \
                 "sdk/firmware-sdk/ei_fusion.h:45:6: warning: vendor config\n"
        self.assertEqual(runner.first_party_warnings(vendor), [])
        self.assertEqual(len(runner.first_party_warnings("repo/firmware/himax_arc/birdhouse/bh_model.cc:4:5: warning: ours")), 1)

    def test_failed_preprocess_cli_has_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'preprocess'
            subprocess.run(['g++', '-std=c++11', '-O2', '-I' + str(REPO),
                            str(REPO / 'firmware/preprocess/test_preprocess_parity.cc'),
                            str(REPO / 'firmware/preprocess/audio_preprocess.cc'),
                            str(REPO / 'firmware/preprocess/mel_filterbank.cc'), '-o', str(binary)], check=True)
            pcm, wrong = Path(tmp) / 'silence.bin', Path(tmp) / 'wrong.bin'
            pcm.write_bytes(bytes(80000 * 4)); wrong.write_bytes(bytes(9960))
            p = subprocess.run([str(binary), str(pcm), str(wrong)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn('status: FAIL', p.stdout)

    def test_backend_must_equal_one(self):
        manifest = json.loads((REPO / 'firmware/himax_arc/birdhouse/model_manifest.json').read_text())
        for val, want in [('1', True), ('2', False), ('0', False)]:
            rep = ops.Report()
            ops.check_configuration(manifest, {}, {'EI_CLASSIFIER_TFLITE_ENABLE_ARC': val}, rep, True)
            self.assertEqual(rep.ok, want)

    def test_sdk_wrapper_rejects_injection_before_make(self):
        for arg in ('flash', 'run', 'ota', '-f', '--eval=bad', 'SHELL=bad', 'APP_TYPE=bad',
                    'OUT_DIR_ROOT=/tmp/escape', '-j8;bad', 'all', 'clean'):
            p = subprocess.run([str(TOOLS / 'sdk_make.sh'), '/tmp/unused-bh-output', arg], capture_output=True)
            self.assertEqual(p.returncode, 2, arg)

    def test_invalid_uf2_and_empty_image(self):
        with self.assertRaises(ValueError): uf2.pack(b'')
        data = uf2.pack(bytes(range(256)))
        self.assertTrue(all(ok for _, ok, _ in uf2.firmware_checks(uf2.describe(data)[0])))
        for offset in (0, 12, 16, 20, 24, 28, 508):
            bad = bytearray(data); bad[offset] ^= 1
            self.assertFalse(all(ok for _, ok, _ in uf2.firmware_checks(uf2.describe(bad)[0])), offset)
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'bad.uf2', Path(tmp) / 'out.bin'
            src.write_bytes(b'bad')
            p = subprocess.run([sys.executable, str(TOOLS / 'uf2_tool.py'), 'unpack', str(src), str(dst)],
                               capture_output=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(dst.exists())

    def test_real_candidate_full_payload_and_mutations(self):
        old = REPO / '.local-tools/port-himax/bh-candidate/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf'
        image_file = REPO / '.local-tools/port-himax/bh-package/candidate/out/birdhouse_candidate_output.img'
        if not old.is_file() or not image_file.is_file():
            self.skipTest('preserved original offline candidate required')
        facts = json.loads((REPO / 'docs/research/birdhouse_v1_implementation_20261111/results/package_candidate.json').read_text())['facts']
        parts = [{'addr': int(p['addr'], 16), 'size': p['size']} for p in facts['partitions'] if p['type'] == '0x4']
        image, elf = image_file.read_bytes(), old.read_bytes()
        self.assertEqual(pkg.sha256(image), facts['image']['sha256'])
        self.assertEqual(pkg.sha256(elf), facts['elf']['sha256'])
        secs = pkg.elf_sections(str(REPO / '.local-tools/toolchains/arc_gnu_ei_prebuilt_minimal_elf32_le_linux_install/bin'), str(old))
        self.assertGreater(pkg.verify_application_payload(image, parts, secs, elf), 470000)
        # A code byte far away from the old sampled windows, a destination,
        # chain pointer, marker, missing chunk, and truncation must all fail.
        for offset in (0x24000, 0x22000 + 0x494 + 36, 0x22000 + 0x494 + 12,
                       0x22000 + 0x494 + 64):
            bad = bytearray(image); bad[offset] ^= 1
            with self.assertRaises(ValueError, msg=hex(offset)):
                pkg.verify_application_payload(bad, parts, secs, elf)
        with self.assertRaises(ValueError): pkg.verify_application_payload(image, parts[:-1], secs, elf)
        with self.assertRaises(ValueError): pkg.verify_application_payload(image[:-0x1000], parts, secs, elf)


if __name__ == '__main__':
    unittest.main()

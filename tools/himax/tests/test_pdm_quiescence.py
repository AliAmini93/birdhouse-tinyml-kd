"""Offline diagnostic contracts and independent-witness negative controls."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

REPO = Path(__file__).resolve().parents[3]
BH = 'firmware/himax_arc/birdhouse/'
TEST = 'firmware/himax_arc/tests/'
SDK = REPO / '.local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3'


def body(text, name):
    start = text.index('{', text.index(name))
    depth = 1
    end = start + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


class QuiescenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert Path(sys.executable).resolve() == Path(os.environ['BH_PYTHON']).resolve()
        cls.work = Path(os.environ['BH_PDM_DIAG_WORK']).resolve()
        assert cls.work.is_relative_to(REPO / '.local-tools/port-himax')
        cls.work.mkdir(exist_ok=False)
        cls.results = {'native': [], 'mutants': [], 'static': []}

    @classmethod
    def tearDownClass(cls):
        (cls.work / 'results.json').write_text(json.dumps(cls.results, indent=2) + '\n')

    def test_00_sdk_read_contract_and_mapping(self):
        config = (SDK / 'board/socket/configs/24/io_config.h').read_text()
        self.assertRegex(config, r'#define\s+IO_PDM_RX0_DMA\s+\(4\)')
        self.assertRegex(config, r'#define\s+IO_PDM_RX0_INT_RX_AVAIL\s+\(69\)')
        code = (SDK / 'arc/arc_udma.c').read_text()
        for name, reg in [('_dmac_irq_status', 'AUX_DMACIRQ'),
                          ('_dmac_channel_status', 'AUX_DMACSTAT0'),
                          ('_dmac_complete_status', 'AUX_DMACSTAT1')]:
            b = body(code, 'uint32_t ' + name + '(')
            self.assertIn('_arc_aux_read(' + reg + ')', b)
            self.assertNotIn('_arc_aux_write', b)
        arc = (REPO / (BH + 'bh_arc_glue.cc')).read_text()
        b = body(arc, 'BhPdmDmaStatus bh_port_pdm_diag_read_status()')
        self.assertEqual(re.findall(r'_arc_aux_read\((\w+)\)', b),
                         ['AUX_DMACSTAT0', 'AUX_DMACSTAT1', 'AUX_DMACIRQ'])
        self.assertNotIn('_arc_aux_write', b)
        self.assertNotIn('IRQ_SELECT', b.split('//')[0])
        self.results['static'].append('SDK read getters and board/24 channel/IRQ match')

    def test_01_capture_and_forwarding_contract(self):
        port = (REPO / (BH + 'bh_pdm_port.cc')).read_text()
        original = subprocess.run(['git', 'show', '3d0fb3fd4c1889d79462bbc404aee722c1811894:' +
                                   BH + 'bh_pdm_port.cc'], capture_output=True, text=True, check=True).stdout
        for name in ['void OnAudio(', 'int bh_port_pdm_start(']:
            self.assertEqual(body(port, name), body(original, name))
        stop = body(port, 'int bh_port_pdm_stop()')
        self.assertEqual(stop.count('hx_lib_audio_stop()'), 1)
        self.assertLess(stop.index('g_capture = nullptr'), stop.index('g_started = 2'))
        self.assertLess(stop.index('g_started = 2'), stop.index('bh_port_irq_restore(irq)'))
        self.assertLess(stop.index('bh_port_irq_restore(irq)'), stop.index('hx_lib_audio_stop()'))
        event = body(port, 'void bh_port_pdm_diag_enable_event(')
        self.assertNotIn('printf', event)
        self.assertNotIn('irq_save', event)
        self.assertNotIn('g_capture', event)
        arc = (REPO / (BH + 'bh_arc_glue.cc')).read_text()
        wrap = body(arc, 'extern "C" void __wrap__dma_chan_enable(')
        self.assertEqual(wrap.count('__real__dma_chan_enable(mask, enable)'), 1)
        self.assertNotIn('printf', wrap)
        self.assertNotIn('irq_save', wrap)
        self.assertEqual((REPO / (BH + 'bh_runtime.cc')).read_bytes(),
                         subprocess.run(['git', 'show', '3d0fb3fd4c1889d79462bbc404aee722c1811894:' +
                                         BH + 'bh_runtime.cc'], capture_output=True, check=True).stdout)
        self.results['static'].append('ISR/start/runtime unchanged; stop detachment and forwarding retained')

    def build_run(self, label, san=False, alternate=None):
        sources = [TEST + 'test_pdm_diag.cc', BH + 'bh_pdm_port.cc', BH + 'bh_capture.cc',
                   TEST + 'fake_aud_lib.cc', TEST + 'host_port.cc']
        exe = self.work / label
        flags = ['-std=c++11', '-O2', '-g', '-fno-pie', '-no-pie', '-DBIRDHOUSE_HOST_BUILD=1',
                 '-I' + str(REPO), '-Wall', '-Wextra', '-Werror']
        if san:
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        cmd = ['g++', *flags, *[str(alternate) if s == BH + 'bh_pdm_port.cc' and alternate
                               else str(REPO / s) for s in sources], '-o', str(exe)]
        compiled = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        (self.work / (label + '-compile.log')).write_text(compiled.stdout + compiled.stderr)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
        result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30, env=env)
        (self.work / (label + '.log')).write_text(result.stdout + result.stderr)
        return result

    def test_10_native_and_sanitizers(self):
        for san in [False, True]:
            r = self.build_run('diag-san' if san else 'diag', san)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            summary = json.loads(re.search(r'SUMMARY (\{[^\n]+\})', r.stdout)[1])
            self.assertEqual(summary['checks_failed'], 0)
            self.results['native'].append(dict(summary, sanitizer=san))

    def test_20_independent_witness_mutations(self):
        source = (REPO / (BH + 'bh_pdm_port.cc')).read_text()
        mutations = [
            ('unknown_as_zero', 'r.dma.valid == kBhPdmDiagValid && !r.dma.error', 'true'),
            ('ignore_word_change', 'r.changed_words != 0', 'false'),
            ('ignore_enable_attempt', 'bool activity = g_diag_post_enable != 0;', 'bool activity = false;'),
            ('ignore_irq', '((r.dma.valid & 8u) && r.dma.irq)', 'false'),
            ('ignore_late', 'r.late_callbacks != first.late_callbacks', 'false'),
            ('arm_after_quarantine', 'if (g_started != 0 || g_diag.armed) return -1;', 'if (false) return -1;'),
        ]
        for label, old, new in mutations:
            self.assertEqual(source.count(old), 1)
            path = self.work / (label + '.cc')
            path.write_text(source.replace(old, new, 1))
            r = self.build_run(label, alternate=path)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertIn('CHECK FAILED', r.stdout)
            self.results['mutants'].append({'mutation': label, 'compiled': True, 'rejected_by_assertion': True})


if __name__ == '__main__':
    unittest.main()

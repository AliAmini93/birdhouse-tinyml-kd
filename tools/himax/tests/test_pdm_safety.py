"""Focused offline PDM contract checks. No hardware, make, packagers or vendor execution.

Run only with the owner's existing BH_PYTHON: -I -B -m unittest discover ...
Native compiler operands below are explicit. ARC objdump/readelf inspect inert
files only. Cached validated host kernels are reused read-only; the three host
parser translation units are compiled from the read-only SDK in place.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
TOOLS = REPO / 'tools/himax'
sys.path.insert(0, str(TOOLS))
import audit_deployment_barriers as audit
from postlink_audit import elf_sections, read_elf_bytes

WORK = REPO / '.local-tools/port-himax/pdm-safety-20261113-OFFLINE_ONLY-NOT_FOR_FLASH'
VALIDATED = REPO / '.local-tools/port-himax/bh-codex-validated/host-tests'
SDK = REPO / audit.SDK_REL
EI = SDK / 'app/scenario_app/edge_impulse_visionai/ei-model'
BH = 'firmware/himax_arc/birdhouse/'
TESTS = 'firmware/himax_arc/tests/'
COMMON = [BH+'bh_capture.cc', BH+'bh_pdm_port.cc', TESTS+'fake_aud_lib.cc', TESTS+'host_port.cc']
PIPE = [BH+'bh_runtime.cc', BH+'bh_diag.cc', BH+'bh_model.cc',
        'firmware/preprocess/audio_preprocess.cc', 'firmware/preprocess/mel_filterbank.cc',
        'firmware/model/student_final_int8_model_data.cc']
NATIVE = {
    'diag': [BH+'bh_diag.cc'],
    'capture': [BH+'bh_capture.cc'],
    'pdm_port': COMMON,
    'pdm_lifecycle': COMMON,
    'pdm_diag': COMMON,
    'runtime': COMMON+PIPE,
    'console': COMMON+PIPE+[BH+'bh_console.cc'],
    'preprocess_reference': ['firmware/preprocess/audio_preprocess.cc', 'firmware/preprocess/mel_filterbank.cc'],
    'tflm_inference': [BH+'bh_model.cc', 'firmware/model/student_final_int8_model_data.cc'],
}


def run(cmd):
    # No shell, no inherited make options, no executable ARC/vendor code.
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
               UBSAN_OPTIONS='halt_on_error=1', LC_ALL='C')
    return subprocess.run([str(x) for x in cmd], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=60)


def evidence_checks(fs, reader):
    rx = fs['hx_lib_audio_rx_callback']['body']
    isr = fs['pdm_rx0_rx_ISR']['body']
    # These checks intentionally refer to the pinned binary's observed ordering,
    # not a model-selected hardware assumption.
    rearm = rx.index('<hx_drv_pdm_init_transfer>')
    app = rx.index('j_s\t[r1]')
    dispatch = isr.index('jlne\t[r1]')
    ack = isr.index('<_dma_int_clear>')
    loop = fs['io_pdm_rx_open']['body']
    return {
        'original_16_static_observations': all(c['status'] == 'PASS' for c in audit.pdm_findings(fs, reader)['checks']),
        'rearm_before_application': rearm < app,
        'rx_dispatch_before_ack': dispatch < ack,
        'boot_to_microphone': 'edge_impulse_visionai' in audit.callees(fs['main']) and
            'ei_microphone_init()' in audit.callees(fs['edge_impulse_visionai']),
        'microphone_to_audio_init': 'hx_lib_audio_init' in audit.callees(fs['ei_microphone_init()']),
        'audio_to_driver_to_open': 'hx_drv_pdm_init' in audit.callees(fs['hx_lib_audio_init']) and
            'io_pdm_rx_open' in audit.callees(fs['hx_drv_pdm_init']),
        'error_isr_dispatches_indirect_callback': 'jlne\t[r1]' in fs['pdm_rx0_err_ISR']['body'],
        'audio_init_registers_error_callback': '0x100241a4' in fs['hx_lib_audio_init']['body'],
        'error_callback_reinitializes_inline': 'hx_lib_audio_init' in audit.callees(fs['hx_lib_audio_err_callback']),
        'unbounded_ready_poll': bool(re.search(r'1002a1b8:\s+lr\s+r0,\[r0\]\n'
            r'1002a1bc:\s+btst_s\s+r0,0x1\n'
            r'1002a1be:\s+beq_s\s+-8\s+;1002a1b4', loop)),
    }


class PdmSafetyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if Path(sys.executable).resolve() != Path(os.environ['BH_PYTHON']).resolve():
            raise RuntimeError('Use the owner-mandated BH_PYTHON interpreter')
        WORK.mkdir(parents=True, exist_ok=True)
        cls.tmp = tempfile.TemporaryDirectory(prefix='verification-', dir=WORK)
        cls.build = Path(cls.tmp.name)
        cls.objects = {}
        cls.results = {'scope': 'OFFLINE_ONLY / NOT_FOR_FLASH; behavioral model, not hardware validation',
                       'native': [], 'negative_controls': [], 'static': {}}
        elf = audit.regular_file(REPO/audit.ELF_REL)
        assert hashlib.sha256(elf.read_bytes()).hexdigest() == audit.ELF_SHA
        cls.elf = elf
        tool = lambda n: REPO/audit.TC_REL/('arc-elf32-'+n)
        cls.tool = staticmethod(tool)
        raw = run([tool('objdump'), '-d', '-C', '--no-show-raw-insn', elf])
        assert raw.returncode == 0
        cls.fs = audit.functions(raw.stdout)
        cls.sections = elf_sections(lambda n: str(tool(n)), str(elf))
        # Cache identities remain private; ensure native checks do not modify them.
        cls.inputs = list(VALIDATED.glob('overlay*/libtflm.a'))
        cls.inputs += list(VALIDATED.glob('overlay*/at/*.o'))
        cls.hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.inputs}

    @classmethod
    def tearDownClass(cls):
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p,h in cls.hashes.items())
        (WORK/'test_results.json').write_text(json.dumps(cls.results, indent=2)+'\n')
        cls.tmp.cleanup()

    def reader(self, addr, size):
        return read_elf_bytes(self.sections, str(self.elf), addr, size)

    def compile_object(self, source, san, alternate=None):
        key = (source, san, str(alternate))
        if key in self.objects:
            return self.objects[key]
        obj = self.build / ('obj-'+str(len(self.objects))+'.o')
        flags = ['-std=c++11', '-O2', '-g', '-fno-pie', '-DBIRDHOUSE_HOST_BUILD=1',
                 '-DTF_LITE_STATIC_MEMORY', '-I'+str(REPO), '-I'+str(REPO/BH/'tflm_overlay'),
                 '-isystem', str(EI), '-isystem', str(EI.parent), '-Wall', '-Wextra', '-Werror']
        if san:
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        if source.startswith(str(SDK.relative_to(REPO))+'/'):
            flags += ['-w']  # vendor parser only; first-party warnings stay strict
        r = run(['g++', *flags, '-c', alternate or REPO/source, '-o', obj])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.objects[key] = obj
        return obj

    def executable(self, name, san=False, alternates=None):
        alternates = alternates or {}
        objs = [self.compile_object(s, san, alternates.get(s))
                for s in [TESTS+'test_'+name+'.cc', *NATIVE[name]]]
        flags = ['-no-pie']
        if san:
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        cached = VALIDATED/('overlay-san' if san else 'overlay')
        if name == 'console':
            objs += [self.compile_object(str((EI.parent/'firmware-sdk/at-server'/
                       ('ei_at_'+n+'.cpp')).relative_to(REPO)), san)
                     for n in ['parser','server','server_singleton']]
            flags += ['-Wl,--wrap=_ZN8ATParser5parseENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE']
        if name in ['runtime','console','tflm_inference']:
            objs += [cached/'libtflm.a']
        out = self.build / ('test-'+name+'-'+str(len(self.objects)))
        r = run(['g++', *flags, '-o', out, *objs, '-lm'])
        self.assertEqual(r.returncode, 0, r.stderr)
        return out

    def test_frozen_binary_call_paths_and_order(self):
        checks = evidence_checks(self.fs, self.reader)
        self.assertTrue(all(checks.values()), checks)
        self.results['static'] = checks
        print('STATIC: 16 original observations plus 9 focused call-path/order checks PASS')

    def test_static_negative_controls(self):
        for symbol, before, after in [
            ('hx_lib_audio_rx_callback', '<hx_drv_pdm_init_transfer>', '<unreviewed_helper>'),
            ('pdm_rx0_rx_ISR', 'jlne\t[r1]', 'j_s\t[blink]'),
            ('io_pdm_rx_open', 'beq_s\t-8', 'nop_s\t-8'),
            ('hx_lib_audio_err_callback', '<hx_lib_audio_init>', '<unreviewed_helper>'),
        ]:
            with self.subTest(symbol=symbol):
                fs = copy.deepcopy(self.fs)
                self.assertIn(before, fs[symbol]['body'])
                fs[symbol]['body'] = fs[symbol]['body'].replace(before, after)
                try:
                    passed = all(evidence_checks(fs, self.reader).values())
                except (ValueError, KeyError):
                    passed = False
                self.assertFalse(passed)
        self.results['static_negative_controls'] = 4

    def test_native_regressions_and_sanitizers(self):
        for san in [False, True]:
            for name in NATIVE:
                with self.subTest(suite=name, sanitizer=san):
                    if san and name in ['runtime','console','tflm_inference']:
                        cached = VALIDATED/'overlay-san'
                        nm = run(['nm', '-u', cached/'libtflm.a'])
                        self.assertEqual(nm.returncode, 0)
                        self.assertIn('__asan_', nm.stdout)
                        self.assertIn('__ubsan_', nm.stdout)
                    binary = self.executable(name, san)
                    r = run([binary])
                    self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
                    self.assertNotIn('runtime error:', r.stderr)
                    summary = json.loads(re.search(r'SUMMARY (\{[^\n]+\})', r.stdout)[1])
                    self.assertEqual(summary['status'], 'PASS', summary)
                    entry = dict(summary, sanitizer='ASan+UBSan' if san else 'none')
                    self.results['native'].append(entry)
                    print('NATIVE '+json.dumps(entry))

    def test_compiled_mutations_fail_assertions(self):
        rearm = ('  g.running = true;\n  ++g.counters.rearms;\n'
                 '  g.counters.last_rearm = ++g.counters.sequence;\n')
        mutations = [
            ('stop_reopens', BH+'bh_pdm_port.cc', '  g_started = 2;\n', '  g_started = 0;\n'),
            ('restart_guard_bypassed', BH+'bh_pdm_port.cc', 'if (g_started != 0) return -1;', 'if (g_started == 1) return -1;'),
            ('owner_not_detached', BH+'bh_pdm_port.cc', '  g_capture = nullptr;\n  g_started = 2;', '  g_started = 2;'),
            ('start_mask_removed', BH+'bh_pdm_port.cc', 'const uint32_t irq = bh_port_irq_save();\n  g_started = 1;',
             'const uint32_t irq = fake_aud::irq_state();\n  g_started = 1;'),
            ('irq_restore_enables_caller', TESTS+'host_port.cc', 'fake_aud::IrqRestore(state);', 'fake_aud::IrqRestore(state | 1u);'),
            ('model_ack_too_early', TESTS+'fake_aud_lib.cc', rearm, '  g.pending = false;\n'+rearm),
        ]
        for label, source, old, new in mutations:
            with self.subTest(mutation=label):
                text = (REPO/source).read_text()
                self.assertEqual(text.count(old), 1)
                mutated = self.build/(label+'.cc')
                mutated.write_text(text.replace(old, new, 1))
                binary = self.executable('pdm_lifecycle', alternates={source: mutated})
                r = run([binary])
                self.assertEqual(r.returncode, 1, r.stderr)
                self.assertIn('CHECK FAILED', r.stdout)
                summary = json.loads(re.search(r'SUMMARY (\{[^\n]+\})', r.stdout)[1])
                self.assertGreater(summary['checks_failed'], 0)
                self.results['negative_controls'].append({'mutation': label, 'rejected_by_assertion': True})
                print('NEGATIVE '+label+': compiled; assertions reject it')
        source = TESTS+'fake_aud_lib.cc'
        text = (REPO/source).read_text()
        self.assertEqual(text.count(rearm), 1)
        late = text.replace(rearm, '', 1).replace('  // The completion remains pending', rearm+'  // The completion remains pending', 1)
        mutated = self.build/'model_rearm_too_late.cc'
        mutated.write_text(late)
        r = run([self.executable('pdm_lifecycle', alternates={source: mutated})])
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn('CHECK FAILED', r.stdout)
        self.results['negative_controls'].append({'mutation': 'model_rearm_too_late', 'rejected_by_assertion': True})
        print('NEGATIVE model_rearm_too_late: compiled; assertions reject it')


if __name__ == '__main__':
    unittest.main()

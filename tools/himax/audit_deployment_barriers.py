#!/usr/bin/env python3
"""Inspect the pinned candidate and cached recovery evidence, strictly file-only.

No firmware build, image generation, device discovery, serial, I2C or network.
Results distinguish static checks from open hardware questions. A successful
static audit is never hardware-access authorization or tested recovery.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from postlink_audit import elf_sections, read_elf_bytes

REPO = Path(__file__).resolve().parents[2]
SDK_REL = '.local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3'
ELF_REL = '.local-tools/port-himax/bh-codex-validated/bh-candidate/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf'
TC_REL = '.local-tools/toolchains/arc_gnu_ei_prebuilt_minimal_elf32_le_linux_install/bin'
ELF_SHA = '8a280fa470c5e6a40b10a941a4e1fe99625233e8d28253b6bcfe4104aff7142f'
FIRST_LOADER_SHA = '6ed391b0eea39eafacf6f5f621cdd5afda4351b651b8234e87c4b9554b98d1f0'


def regular_file(path):
    p = Path(path).resolve(strict=True)
    if not (p.is_relative_to(REPO) or p.is_relative_to(Path('/tmp'))):
        raise ValueError('only repository or temporary regular files may be inspected')
    if not stat.S_ISREG(p.stat().st_mode):
        raise ValueError('not a regular file')
    return p


def fingerprint(path):
    p = regular_file(path)
    return {'path': str(p.relative_to(REPO)) if p.is_relative_to(REPO) else '<temporary-file>',
            'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def functions(disassembly):
    blocks = re.split(r'^([0-9a-f]+) <([^\n]+)>:\n', disassembly, flags=re.M)
    return {blocks[i + 1]: {'address': int(blocks[i], 16), 'body': blocks[i + 2],
                           'end': int(blocks[i + 3], 16) if i + 3 < len(blocks) else 2**32}
            for i in range(1, len(blocks), 3)}


def call_sites(fn):
    # Direct ARC calls/tail calls only. Do not mistake jump-table data for code:
    # the ioctl and sample-rate dispatch tables are resolved separately below.
    return [(int(m.group(1), 16), m.group(2), m.group(3)) for m in re.finditer(
        r'^([0-9a-f]+):\s+(?:bl(?:_s)?|b(?:_s)?)(?:\.[a-z]+)?\s+[^\n]*;([0-9a-f]+) <([^>]+)>',
        fn['body'], re.M) if not fn['address'] <= int(m.group(2), 16) < fn['end']]


def callees(fn):
    return [x[2] for x in call_sites(fn)]


def pdm_findings(funcs, read_bytes):
    checks = []

    def check(name, ok):
        checks.append({'check': name, 'status': 'PASS' if ok else 'FAIL'})

    required = ['bh_port_pdm_start(bh::Capture*)', 'bh_port_pdm_stop()', 'hx_lib_audio_start',
                'hx_drv_pdm_set_pcm_freq', 'io_pdm_rx_ioctl', 'hx_drv_pdm_init_transfer',
                'hx_drv_ckgen_set_gated', 'io_pdm_rx_read', '_dma_chan_desc',
                '_dma_chan_enable', '_dma_chan_desc_aux', '_dma_chan_reset', '_dma_int_clear',
                'cpu_lock_save', 'cpu_unlock_restore', 'hx_lib_audio_rx_callback',
                'pdm_rx0_rx_ISR', 'hx_drv_pdm_stop_transfer', 'io_pdm_rx_stop',
                'hx_lib_audio_err_callback', 'io_pdm_rx_open']
    missing = [n for n in required if n not in funcs]
    check('required functions exist in the exact linked candidate', not missing)
    if missing:
        return {'checks': checks, 'missing_symbols': missing}

    start_calls = callees(funcs[required[0]])
    save, start, restore = 'bh_port_irq_save()', 'hx_lib_audio_start', 'bh_port_irq_restore(unsigned long)'
    check('first-party start brackets vendor start with IRQ save/restore',
          all(n in start_calls for n in (save, start, restore)) and
          start_calls.index(save) < start_calls.index(start) < start_calls.index(restore))
    check('IRQ primitives are real clri/seti instructions',
          bool(re.search(r'\bclri\s+r0', funcs['cpu_lock_save']['body'])) and
          bool(re.search(r'\bseti\s+r0', funcs['cpu_unlock_restore']['body'])))

    rate = funcs['hx_drv_pdm_set_pcm_freq']
    ioctl = funcs['io_pdm_rx_ioctl']
    rate_table = re.search(r'ldb\s+r0,\[(0x[0-9a-f]+),r0\]', rate['body'])
    ioctl_table = re.search(r'ldh\.as\s+r1,\[(0x[0-9a-f]+),r1\]', ioctl['body'])
    check('switch tables are identified rather than disassembled as instructions', bool(rate_table and ioctl_table))
    if not (rate_table and ioctl_table):
        return {'checks': checks}
    rate_base, ioctl_base = int(rate_table[1], 16), int(ioctl_table[1], 16)
    rate_target = rate_base + read_bytes(rate_base + 1, 1)[0]  # AUDIO_SR_16KHZ == 1
    ioctl_target = ioctl_base + struct.unpack('<H', read_bytes(ioctl_base + 2 * (0x26 - 1), 2))[0]
    check('16 kHz selector reaches the expected oversampling setup',
          bool(re.search(r'^' + f'{rate_target:x}' + r':\s+st\s+8,\[sp\]', rate['body'], re.M)))
    leaf = [m.group(2) for m in re.finditer(r'^([0-9a-f]+):\s+(.*)$', ioctl['body'], re.M)
            if int(m.group(1), 16) >= ioctl_target][:5]
    check('rate ioctl reaches a register-write leaf, not an interrupt wait',
          len(leaf) == 5 and all(re.fullmatch(pattern, line) for pattern, line in zip([
              r'ld_s\s+r0,\[r0,0\]', r'ld_s\s+r1,\[r2,0\]', r'add\s+r0,r0,464',
              r'sr\s+r1,\[r0\]', r'j_s\s+\[blink\]'], leaf)))

    normal = ['hx_drv_pdm_init_transfer', 'hx_drv_ckgen_set_gated', 'io_pdm_rx_read',
              '_dma_chan_desc', '_dma_chan_enable', '_dma_chan_desc_aux']
    check('reviewed transfer helpers have no global IRQ-enable, indirect call or named wait',
          all(not re.search(r'\bseti\b|\bsleep\b|\bflag\b|\b(?:jl\w*|j(?:_s)?)\s+\[(?!blink\])', funcs[n]['body']) and
              not any(re.search(r'wait|sleep|timer|semaphore|cpu_unlock', c, re.I)
                      for c in callees(funcs[n])) for n in normal))
    check('normal DMA read helpers have only the reviewed direct callees',
          set(callees(funcs['io_pdm_rx_read'])) <=
          {'xprintf', '_arc_exit_halt', '_dma_chan_desc', '_dma_chan_desc_aux', '_dma_chan_enable'})

    cb = funcs['hx_lib_audio_rx_callback']
    cb_sites = call_sites(cb)
    rearm = next((a for a, _, c in cb_sites if c == 'hx_drv_pdm_init_transfer'), None)
    callback = re.search(r'^([0-9a-f]+):\s+j_s\s+\[r1\]', cb['body'], re.M)
    check('vendor RX callback re-arms PDM before the indirect application callback',
          rearm is not None and callback is not None and rearm < int(callback[1], 16))
    isr = funcs['pdm_rx0_rx_ISR']['body']
    check('vendor ISR invokes its indirect callback before the DMA IRQ clear tail',
          'jlne\t[r1]' in isr and '_dma_int_clear' in callees(funcs['pdm_rx0_rx_ISR']))
    stop_calls = callees(funcs['io_pdm_rx_stop'])
    port_stop = callees(funcs['bh_port_pdm_stop()'])
    check('first-party stop restores IRQ state before vendor stop',
          restore in port_stop and 'hx_lib_audio_stop' in port_stop and
          port_stop.index(restore) < port_stop.index('hx_lib_audio_stop'))
    check('stop has channel disable/reset but no explicit DMA completion clear',
          '_dma_chan_enable' in stop_calls and '_dma_chan_reset' in stop_calls and
          '_dma_int_clear' not in stop_calls)
    check('channel reset and completion clear write distinct auxiliary registers',
          '1674' in funcs['_dma_chan_reset']['body'] and '1672' in funcs['_dma_int_clear']['body'])
    check('low-level start return is discarded by audio start',
          bool(re.search(r'<hx_drv_pdm_init_transfer>\n[0-9a-f]+:\s+mov_s\s+r0,0',
                         funcs['hx_lib_audio_start']['body'])))
    check('error recovery calls hardware initialization inside callback path',
          'hx_lib_audio_init' in callees(funcs['hx_lib_audio_err_callback']))
    check('hardware open contains an unbounded ready-bit poll',
          bool(re.search(r'beq_s\s+-8\s+;[^\n]*<io_pdm_rx_open\+', funcs['io_pdm_rx_open']['body'])))

    return {'checks': checks,
            'dispatch': {'sample_rate_selector': 1, 'oversampling_case': hex(rate_target),
                         'ioctl_command': '0x26', 'ioctl_register_write_case': hex(ioctl_target)},
            'normal_start_assessment': 'No software ISR wait found on the traced initialized-PDM 16 kHz path; elapsed time remains unmeasured.',
            'open_risks': [
                {'id': 'P1', 'status': 'OPEN', 'risk': 'An IRQ may interleave with vendor stop, and a pending old DMA IRQ may re-arm it after stop or count a completion against a new run. Channel-reset implicit IRQ-clearing semantics are not established.'},
                {'id': 'P2', 'status': 'VERIFIED_LIMIT', 'risk': 'Application late-callback tests do not emulate vendor ISR re-arm/ack behavior. Safe PCM ownership is not proof of stopped hardware.'},
                {'id': 'P3', 'status': 'VERIFIED_LIMIT', 'risk': 'Audio start discards the lower transfer return; success is not proof of active DMA. The low-level read API also returns void on its queue-full exit.'},
                {'id': 'P4', 'status': 'OPEN', 'risk': 'Boot initialization and FIFO-error ISR recovery can poll a peripheral ready bit without a software deadline; main-loop capture timeout cannot interrupt them.'}],
            'function_addresses': {n: hex(funcs[n]['address']) for n in required}}


def summarize_saved_kernel(text):
    resets, failed_reads, mode_sense, pids, serials = [], 0, [], [], set()
    for line in text.splitlines():
        m = re.match(r'(\S+) .*?kernel: (.*)', line)
        if not m:
            continue
        try:
            ts = datetime.datetime.fromisoformat(m[1]).timestamp()
        except ValueError:
            continue
        msg = m[2]
        if 'reset full-speed USB device' in msg:
            resets.append(ts)
        if 'Mode Sense:' in msg:
            mode_sense.append(ts)
        if 'CDB: Read(10)' in msg:
            failed_reads += 1
        p = re.search(r'idVendor=2886, idProduct=([0-9a-f]{4})', msg)
        if p:
            pids.append(p[1])
        v = re.search(r'SerialNumber: (.*)', msg)
        if v:
            serials.add(v[1])  # count only; never publish device identifiers
    deltas = [round(b - a, 3) for a, b in zip(resets, resets[1:]) if 25 <= b - a <= 35]
    return {'reset_events': len(resets), 'reset_intervals_in_25_to_35_second_band': deltas,
            'failed_read10_commands': failed_reads, 'mode_sense_log_entries': len(mode_sense),
            'observed_product_ids': sorted(set(pids)), 'distinct_serial_string_count': len(serials),
            'diagnostic_scope': 'historical cached logs only, not current hardware state',
            'causation': 'Not established: the log does not isolate the exact stalled SCSI command, driver bug, power issue or competing process.'}


def first_loader_disassembly(sdk):
    """Wrap vendor bytes for objdump only. The temporary ELF is never executed."""
    first = sdk / 'tools/image_gen_cstm/input/BLp/QFN72/HX6537-A09TDIG-1111V/sign_formal_PA8530_EM9D_Bootloader.bin'
    if fingerprint(first)['sha256'] != FIRST_LOADER_SHA:
        raise ValueError('first-loader bytes changed; address-specific analysis no longer applies')
    tc = REPO / TC_REL
    with tempfile.TemporaryDirectory(prefix='bh-loader-static-', dir='/tmp') as tmp:
        payload, wrapper = Path(tmp) / 'payload.bin', Path(tmp) / 'ANALYSIS_ONLY.elf'
        # This signed image has a 0x28c-byte envelope. Its first payload word is
        # the entry pointer and startup vectors/code follow at 0x20000000.
        payload.write_bytes(regular_file(first).read_bytes()[0x28c:])
        if struct.unpack('<I', payload.read_bytes()[:4])[0] != 0x20000004:
            raise ValueError('unexpected first-loader payload entry')
        subprocess.run([str(regular_file(tc / 'arc-elf32-objcopy')), '-I', 'binary',
                        '-O', 'elf32-littlearc', '-B', 'arc:ARCv2',
                        '--rename-section', '.data=.text,alloc,load,readonly,code,contents',
                        '--adjust-vma=0x20000000', str(payload), str(wrapper)],
                       check=True, capture_output=True)
        return subprocess.run([str(regular_file(tc / 'arc-elf32-objdump')), '-D',
                               '--no-show-raw-insn', str(regular_file(wrapper))],
                              check=True, capture_output=True, text=True).stdout


def first_loader_findings(disassembly):
    """Address-specific facts, not proof that this is the installed receiver."""
    insn = {int(m[1], 16): m[2] for m in re.finditer(
        r'^([0-9a-f]+):\s+(.*)$', disassembly, re.M)}

    def matches(addr, pattern):
        return bool(re.fullmatch(pattern, insn.get(addr, '')))

    def call(addr, target):
        return matches(addr, r'bl\s+[^;]+;' + f'{target:x}' + r' <[^>]+>')

    receiver = '\n'.join(line for addr, line in insn.items() if 0x20009bf0 <= addr < 0x20009df0)
    targets = {int(m[1], 16) for m in re.finditer(r'\bbl\s+[^;\n]+;([0-9a-f]+) <', receiver)}
    checks = {
        'caller_passes_RAM_buffer_0x20050000': matches(0x20001596, r'mov_s\s+r0,0x20050000'),
        'caller_receives_before_erase_and_program_calls': call(0x200015ae, 0x20009bf0) and
            call(0x200016b2, 0x20000fb4) and call(0x200016cc, 0x20003180),
        'caller_does_not_inspect_program_return_before_done_message':
            matches(0x200016d0, r'mov_s\s+r0,0x9000074c') and call(0x200016d6, 0x20009df0),
        'negative_receive_result_branches_away_from_write_path':
            matches(0x200015b6, r'brge\.nt\s+r0,0,20\s+;200015c8 <[^>]+>') and
            matches(0x200015c6, r'b_s\s+320\s+;20001704 <[^>]+>'),
        'receiver_EOT_path_ACKs_then_returns':
            matches(0x20009c64, r'breq\.nt\s+r0,0x4,24\s+;20009c7c <[^>]+>') and
            matches(0x20009c80, r'mov_s\s+r0,6') and call(0x20009c82, 0x20001c10) and
            matches(0x20009c92, r'b_s\s+334\s+;20009dde <[^>]+>') and
            matches(0x20009dee, r'j_s\s+\[blink\]'),
        'receiver_direct_callees_are_reviewed_byte_IO_flush_CRC_and_copy':
            targets == {0x20001bd0, 0x20001c10, 0x200039d4, 0x20001b44, 0x200009e4} and
            not re.search(r'\bjl\w*\b', receiver),
        'sector_erase_helper_constructs_0x20_command': matches(0x20002c3c, r'mov_s\s+r0,0x20'),
        'page_program_helper_selects_0x02_or_0x12_command':
            matches(0x20003230, r'mov_s\s+r1,0x12') and matches(0x2000324c, r'mov_s\s+r1,2'),
    }
    return {'checks': checks, 'evidence_kind': 'STATIC CALL-ORDER ANALYSIS OF PINNED SDK BINARY',
            'receive_buffer': '0x20050000', 'receive_call': '0x200015ae',
            'EOT_ACK_call': '0x20009c82', 'erase_call': '0x200016b2',
            'program_call': '0x200016cc',
            'conclusion': 'In this SDK receiver, transfer ACK precedes the caller erase/program path; ACK is not burn completion or update atomicity. The caller does not inspect the program return before its done message.',
            'limits': ['Installed Himax loader identity and BL702 forwarding/segmentation are unknown.',
                       'UART byte I/O uses driver function pointers; this is not an exhaustive flash-write call-graph proof.',
                       'No interrupted-transfer, power-loss, flash verification or recovery experiment was performed.']}


def recovery_findings(sdk):
    tool = sdk / 'tools'
    bl = tool / 'image_gen_cstm/input/BLp/QFN72/HX6537-A09TDIG-1111V'
    rom = tool / 'OTA_Tool/BootUpFromI2C/HX6537-A09TDIG-1111V_QFN72/sign_formal_PA8530_EM9D_2nd_Bootloader.bin'
    guide = tool / 'OTA_Tool/doc/WE-I OTA_v2.1.0 usage guide for cstm.docx'
    first, second = bl / 'sign_formal_PA8530_EM9D_Bootloader.bin', bl / 'sign_formal_PA8530_EM9D_2nd_Bootloader.bin'
    guide_xml = zipfile.ZipFile(regular_file(guide)).read('word/document.xml')
    text = ' '.join(ET.fromstring(guide_xml).itertext())
    checks = {'first_loader_xmodem_menu_marker': b'Xmodem download and burn FW image' in regular_file(first).read_bytes(),
              'second_loader_dump_and_erase_markers': all(x in regular_file(second).read_bytes() for x in [b'FLASH_DUMP', b'FLASH_ERASE_ALL']),
              'rom_loader_filename_matches_part_and_package': 'HX6537-A09TDIG-1111V_QFN72' in str(rom),
              'rom_loader_under_128_KiB': regular_file(rom).stat().st_size < 128 * 1024,
              'guide_documents_conditional_rom_boot': all(x in text for x in ['bootloader verified failed', '011', '128K', '0x20000000']),
              'guide_requires_version_matching': 'corresponding version' in text}
    return {'checks': checks, 'inputs': [fingerprint(p) for p in (first, second, rom, guide)],
            'new_asset_found': 'Exact-part-labelled Himax ROM-I2C bootstrap already exists in SDK; it is not a BL702 recovery image or a tested Grove recovery route.',
            'limits': ['Installed 2022 BL702 source/binary not present in the inspected cache.',
                       'ROM-entry straps, external-host wiring and loader signature acceptance on this Grove are unverified.',
                       'A generic WE-I OTA guide and menu markers do not prove Grove-specific reachability, safe readback, update atomicity or successful recovery.',
                       'The SDK ota.exe default action is force-upgrade; it is not an approved diagnostic tool.'],
            'recovery_capability': 'UNTESTED / NOT ESTABLISHED'}


def observer_admission(record):
    """Review a supplied checklist, not live host state. Never executes a plan."""
    if not isinstance(record, dict):
        return {'status': 'NO-GO', 'missing_prerequisites': ['checklist_object'],
                'out_of_scope_actions': [], 'authorization': 'No hardware access is authorized.'}
    required = ['owner_phase_approval', 'already_powered_connected_no_replug',
                'host_probes_quiescent', 'msc_driver_activity_prevented',
                'no_open_tty_or_block_clients', 'device_path_verified_from_cached_os_metadata',
                'stop_rule_acknowledged']
    missing = [name for name in required if record.get(name) is not True]
    allowed = {'read_cached_kernel_journal', 'read_cached_usb_identity'}
    actions = record.get('requested_actions', [])
    if not isinstance(actions, list) or not all(isinstance(x, str) for x in actions):
        actions = []
    unsafe = [name for name in actions if name not in allowed]
    if not actions:
        missing.append('explicit_requested_actions')
    return {'status': 'NO-GO' if missing or unsafe else 'REVIEW_READY',
            'missing_prerequisites': missing, 'out_of_scope_actions': unsafe,
            'authorization': 'This offline checklist is not approval and does not inspect or access hardware.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--elf', default=str(REPO / ELF_REL))
    ap.add_argument('--observer-plan', help='optional regular JSON file; evaluates supplied claims only')
    ap.add_argument('--out', required=True, help='new JSON evidence file in repository docs or /tmp')
    args = ap.parse_args()
    elf, sdk = regular_file(args.elf), REPO / SDK_REL
    meta = fingerprint(elf)
    if meta['sha256'] != ELF_SHA:
        ap.error('candidate ELF differs from 1095349 evidence; audit its control flow explicitly first')
    out = Path(args.out).resolve()
    if not (out.is_relative_to(REPO / 'docs/research') or out.is_relative_to(Path('/tmp'))) or out.exists():
        ap.error('output must be a new local report file')
    tc = REPO / TC_REL
    tool = lambda name: str(regular_file(tc / ('arc-elf32-' + name)))
    raw = subprocess.run([tool('objdump'), '-d', '-C', '--no-show-raw-insn', str(elf)],
                         check=True, capture_output=True, text=True).stdout
    secs = elf_sections(tool, str(elf))
    reader = lambda addr, size: read_elf_bytes(secs, str(elf), addr, size)
    pdm = pdm_findings(functions(raw), reader)
    recovery = recovery_findings(sdk)
    recovery['first_loader_call_order'] = first_loader_findings(first_loader_disassembly(sdk))
    log = REPO / '.local-tools/diagnostics/grove-ai-v1/kernel_grove_full.log'
    info = REPO / '.local-tools/diagnostics/grove-ai-v1/INFO_UF2.TXT'
    info_text = regular_file(info).read_text()
    report = {'starting_source_commit': '1095349f459d974975e606d243c84d26635f67bf',
              'candidate': meta, 'pdm': pdm, 'recovery': recovery,
              'historical_transport': summarize_saved_kernel(regular_file(log).read_text()),
              'historical_bootloader': {'build_id': '2d5b48b' if '2d5b48b' in info_text else 'UNEXPECTED',
                                         'date': '2022-08-23' if 'Aug 23 2022' in info_text else 'UNEXPECTED'},
              'cached_input_fingerprints': [fingerprint(log), fingerprint(info)],
              'observer_plan_review': observer_admission(
                  json.loads(regular_file(args.observer_plan).read_text()) if args.observer_plan else {}),
              'firmware_modified_or_rebuilt': False, 'hardware_access': False,
              'decision': {'firmware_write': 'NO-GO', 'hardware_diagnostic_execution': 'NO-GO pending explicit reviewed scope and host isolation',
                           'next_boundary': 'Any live USB enumeration/attachment, tty/block-device open, serial/I2C transfer or board control'}}
    ok = (all(c['status'] == 'PASS' for c in pdm['checks']) and all(recovery['checks'].values()) and
          all(recovery['first_loader_call_order']['checks'].values()))
    report['static_audit'] = 'PASS' if ok else 'FAIL'
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as f:
        json.dump(report, f, indent=2); f.write('\n')
    print(f"static audit: {report['static_audit']}; {len(pdm['checks'])} PDM checks; recovery remains untested; hardware NO-GO")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

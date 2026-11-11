#!/usr/bin/env python3
"""Post-link audit of the Birdhouse firmware candidate (offline, read-only).

Checks the linked ELF against what the design requires and writes a JSON report.
A link that succeeds is not evidence; each item below is checked on the artefact.

  memory     every section lies inside its linker region; margins are reported
             and compared with policy thresholds and with the vendor-only build
  buffers    arena, PCM, feature and DMA buffers have the designed size and sit
             in the designed region; DMA buffer alignment
  model      the model bytes inside the ELF equal the tracked model array
  hooks      the two link-time interpositions exist, the vendor main loop and the
             audio library really call the wrappers, and the wrappers reach the
             original functions
  leftovers  nothing from the abandoned stage50 design is linked
  stack      per-function frame sizes (from -fstack-usage) summed along the
             inference call chain, against the 8 KB stack
  heap       bytes left for the vendor's malloc users

Exit status: 0 = PASS, 1 = FAIL, 2 = usage error.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

POLICY = {
    "iccm1_min_free_bytes": 16 * 1024,     # code region
    "system0_min_free_bytes": 256 * 1024,  # data / big buffers
    "heap_min_bytes": 128 * 1024,          # DCCM left for malloc
    "stack_known_chain_max_fraction": 0.5,
    "arena_bytes": 256 * 1024,
    "pcm_bytes": 160000,
    "feature_bytes": 9960,
    "dma_bytes": 16384,
}

LEFTOVER_SYMBOLS = ["birdhouse_pdm_feed", "birdhouse_runtime_poll", "birdhouse_runtime_start",
                    "birdhouse_queue_pop_v2", "birdhouse_pdm_hw_start", "PdmMonoQueue", "StreamingLogMel",
                    "birdhouse_link_probe"]

# Functions on the path main loop -> inference, in call order. Each entry is a
# regular expression matched against the demangled name in the .su files.
STACK_CHAIN = [
    ("vendor main loop", r":int edge_impulse_visionai\(\)$"),
    ("wrapper", r"__wrap_is_inference_running"),
    ("RuntimePoll", r"bh::RuntimePoll\(\)"),
    ("ProcessPcm", r"bh::\{anonymous\}::ProcessPcm\(\)"),
    ("ModelInvoke", r"bh::ModelInvoke\(\)"),
    ("MicroInterpreter::Invoke", r"tflite::MicroInterpreter::Invoke\(\)"),
    ("MicroGraph::InvokeSubgraph", r"tflite::MicroGraph::InvokeSubgraph\("),
    ("kernel Eval (largest)", r"kernels/(conv|depthwise_conv|fully_connected)\.cc:\d+:\d+:TfLiteStatus tflite::(\{anonymous\}::)?Eval\("),
    ("kernel MLI worker (largest)", r"EvalMliQuantized(PerChannel|Int8)\("),
]


class Report:
    def __init__(self):
        self.checks = []
        self.facts = {}

    def add(self, group, name, ok, detail=""):
        self.checks.append({"group": group, "check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)})

    @property
    def ok(self):
        return all(c["status"] == "PASS" for c in self.checks)


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, errors="replace").stdout


def parse_regions(ld_path):
    regions = {}
    text = open(ld_path, encoding="utf-8", errors="replace").read()
    block = text[text.index("MEMORY"):text.index("}", text.index("MEMORY"))]
    for m in re.finditer(r"([.\w]+)\s*:\s*ORIGIN\s*=\s*(0x[0-9a-fA-F]+)\s*,\s*LENGTH\s*=\s*(0x[0-9a-fA-F]+)", block):
        regions[m.group(1)] = (int(m.group(2), 16), int(m.group(3), 16))
    return regions


def elf_sections(tool, elf):
    secs = []
    for line in run([tool("readelf"), "-S", "-W", elf]).splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]{8})\s+([0-9a-f]+)\s+([0-9a-f]+)\s+\S+\s+(\S*)", line)
        if m and "A" in m.group(6):
            secs.append({"name": m.group(1), "type": m.group(2), "addr": int(m.group(3), 16),
                         "offset": int(m.group(4), 16), "size": int(m.group(5), 16)})
    return secs


def elf_symbols(tool, elf):
    syms = {}
    for line in run([tool("nm"), "-S", "-C", elf]).splitlines():
        m = re.match(r"^([0-9a-f]+)\s+([0-9a-f]+)\s+(\w)\s+(.*)$", line)
        if m:
            syms[m.group(4)] = {"addr": int(m.group(1), 16), "size": int(m.group(2), 16), "type": m.group(3)}
            continue
        m = re.match(r"^([0-9a-f]+)\s+(\w)\s+(.*)$", line)
        if m:
            syms.setdefault(m.group(3), {"addr": int(m.group(1), 16), "size": 0, "type": m.group(2)})
    return syms


def find_symbol(syms, pattern):
    hits = [(n, s) for n, s in syms.items() if re.search(pattern, n)]
    return hits[0] if len(hits) == 1 else (None, None)


def region_of(addr, regions):
    for name, (origin, length) in regions.items():
        if origin <= addr < origin + length:
            return name
    return None


def read_elf_bytes(secs, elf, addr, size):
    for s in secs:
        if s["addr"] <= addr and addr + size <= s["addr"] + s["size"] and s["type"] != "NOBITS":
            with open(elf, "rb") as f:
                f.seek(s["offset"] + (addr - s["addr"]))
                return f.read(size)
    return None


def function_calls(tool, elf, func):
    """Names of functions called (bl/b/jl) from one function of the ELF."""
    out = run([tool("objdump"), "-d", "-C", "--no-show-raw-insn", elf])
    calls, inside = [], False
    for line in out.splitlines():
        m = re.match(r"^[0-9a-f]+ <(.*)>:$", line)
        if m:
            inside = (m.group(1) == func)
            continue
        if inside:
            m = re.search(r"\s(bl|b|bl_s|b_s|jl|j)\S*\s+.*<([^>+]+)>", line)
            if m and m.group(2) != func:
                calls.append(m.group(2))
    return calls


def load_stack_usage(roots):
    entries = []
    for root in roots:
        for path in glob.glob(os.path.join(root, "**", "*.su"), recursive=True):
            for line in open(path, encoding="utf-8", errors="replace"):
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2 and parts[1].isdigit():
                    entries.append((parts[0], int(parts[1])))
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--elf", required=True)
    ap.add_argument("--baseline-elf", help="vendor-only build for comparison")
    ap.add_argument("--ldscript", required=True)
    ap.add_argument("--toolchain-bin", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--stack-usage-root", action="append", default=[])
    ap.add_argument("--json-out")
    args = ap.parse_args()

    def tool(name):
        return os.path.join(args.toolchain_bin, "arc-elf32-" + name)

    for p in (args.elf, args.ldscript, args.manifest):
        if not os.path.isfile(p):
            print(f"missing input: {p}", file=sys.stderr)
            return 2

    rep = Report()
    regions = parse_regions(args.ldscript)
    secs = elf_sections(tool, args.elf)
    syms = elf_symbols(tool, args.elf)
    manifest = json.load(open(args.manifest, encoding="utf-8"))

    # ---- memory -------------------------------------------------------------
    usage = {}
    for s in secs:
        if s["size"] == 0:
            continue
        r = region_of(s["addr"], regions)
        inside = r is not None and s["addr"] + s["size"] <= regions[r][0] + regions[r][1]
        if not inside:
            rep.add("memory", f"section {s['name']} inside a linker region", False, hex(s["addr"]))
            continue
        usage[r] = max(usage.get(r, 0), s["addr"] + s["size"] - regions[r][0])
    rep.add("memory", "all allocated sections lie inside linker regions",
            all(c["status"] == "PASS" for c in rep.checks), f"{len(secs)} sections")
    mem = {}
    for name, (origin, length) in regions.items():
        used = usage.get(name, 0)
        mem[name] = {"origin": hex(origin), "length": length, "used": used, "free": length - used,
                     "used_percent": round(100.0 * used / length, 2)}
    rep.facts["memory"] = mem
    rep.add("memory", f"ICCM1 free >= {POLICY['iccm1_min_free_bytes']} bytes",
            mem["ICCM1"]["free"] >= POLICY["iccm1_min_free_bytes"],
            f"used {mem['ICCM1']['used']} of {mem['ICCM1']['length']} ({mem['ICCM1']['used_percent']}%), free {mem['ICCM1']['free']}")
    rep.add("memory", f"SYSTEM0 free >= {POLICY['system0_min_free_bytes']} bytes",
            mem["SYSTEM0"]["free"] >= POLICY["system0_min_free_bytes"],
            f"used {mem['SYSTEM0']['used']} of {mem['SYSTEM0']['length']} ({mem['SYSTEM0']['used_percent']}%), free {mem['SYSTEM0']['free']}")

    heap_start = syms.get("__start_heap", {}).get("addr")
    heap_end = syms.get("__end_heap", {}).get("addr")
    stack_top = syms.get("__stack_top", {}).get("addr")
    heap = (heap_end - heap_start) if heap_start and heap_end else 0
    stack = (stack_top - heap_end) if stack_top and heap_end else 0
    rep.facts["heap_bytes"] = heap
    rep.facts["stack_bytes"] = stack
    rep.add("heap", f"heap left in DCCM >= {POLICY['heap_min_bytes']} bytes", heap >= POLICY["heap_min_bytes"],
            f"{heap} bytes between __start_heap and __end_heap")

    # ---- buffers ------------------------------------------------------------
    buffers = {}
    for label, pattern, size, region in (
            ("tensor arena", r"bh::\(anonymous namespace\)::g_arena$", POLICY["arena_bytes"], "SYSTEM0"),
            ("PCM buffer", r"bh::\(anonymous namespace\)::g_pcm$", POLICY["pcm_bytes"], "SYSTEM0"),
            ("feature buffer", r"bh::\(anonymous namespace\)::g_features$", POLICY["feature_bytes"], "SYSTEM0"),
            ("DMA buffer", r"^\(anonymous namespace\)::g_dma_buffer$", POLICY["dma_bytes"], "DCCM")):
        name, s = find_symbol(syms, pattern)
        if s is None:
            rep.add("buffers", f"{label} present (unique symbol)", False, pattern)
            continue
        r = region_of(s["addr"], regions)
        buffers[label] = {"addr": hex(s["addr"]), "size": s["size"], "region": r}
        rep.add("buffers", f"{label}: {size} bytes in {region}", s["size"] == size and r == region,
                f"size {s['size']} at {hex(s['addr'])} in {r}")
        if label == "DMA buffer":
            rep.add("buffers", "DMA buffer aligned to 32 bytes", s["addr"] % 32 == 0, hex(s["addr"]))
        if label == "tensor arena":
            rep.add("buffers", "tensor arena aligned to 16 bytes", s["addr"] % 16 == 0, hex(s["addr"]))
    rep.facts["buffers"] = buffers

    # ---- model --------------------------------------------------------------
    name, s = find_symbol(syms, r"birdhouse::g_student_final_int8_model_data$")
    if s is None:
        rep.add("model", "model array linked", False, "symbol missing")
    else:
        blob = read_elf_bytes(secs, args.elf, s["addr"], s["size"])
        sha = hashlib.sha256(blob).hexdigest() if blob else None
        rep.facts["model"] = {"addr": hex(s["addr"]), "size": s["size"], "sha256_in_elf": sha}
        rep.add("model", "model bytes in the ELF equal the tracked model array",
                sha == manifest["sha256"] and s["size"] == manifest["size_bytes"],
                f"size {s['size']}, sha256 {sha}")

    # ---- hooks --------------------------------------------------------------
    for wrap, real in (("__wrap_is_inference_running", "is_inference_running"),
                       ("__wrap_hx_drv_pdm_deinit", "hx_drv_pdm_deinit")):
        rep.add("hooks", f"{wrap} is linked", wrap in syms and syms[wrap]["size"] > 0,
                f"size {syms.get(wrap, {}).get('size')}")
        rep.add("hooks", f"original {real} is still linked", real in syms, "")
        calls = function_calls(tool, args.elf, wrap) if wrap in syms else []
        rep.add("hooks", f"{wrap} reaches the original {real}", real in calls, f"calls: {sorted(set(calls))[:6]}")
    loop_calls = function_calls(tool, args.elf, "edge_impulse_visionai")
    rep.add("hooks", "vendor main loop calls the wrapper, not the original",
            "__wrap_is_inference_running" in loop_calls and "is_inference_running" not in loop_calls,
            f"wrapper calls: {loop_calls.count('__wrap_is_inference_running')}, direct calls: {loop_calls.count('is_inference_running')}")
    deinit_calls = function_calls(tool, args.elf, "hx_lib_audio_deinit")
    rep.add("hooks", "audio library's de-init path calls the wrapper",
            "__wrap_hx_drv_pdm_deinit" in deinit_calls and "hx_drv_pdm_deinit" not in deinit_calls,
            f"calls: {sorted(set(deinit_calls))}")
    err_calls = function_calls(tool, args.elf, "hx_lib_audio_err_callback")
    rep.add("hooks", "audio library's error handler reaches that de-init path",
            "hx_lib_audio_deinit" in err_calls, f"calls: {sorted(set(err_calls))}")
    rep.add("hooks", "runtime entry points are linked",
            all(n in syms for n in ("bh::RuntimePoll()", "bh::ModelInvoke()")), "")
    for function, original in (("bh_port_irq_save()", "cpu_lock_save"),
                               ("bh_port_irq_restore(unsigned long)", "cpu_unlock_restore")):
        # uint32_t is unsigned long in the ARC ABI (unsigned int on the host).
        calls = function_calls(tool, args.elf, function)
        rep.add("hooks", function + " uses the real ARC interrupt primitive", original in calls, calls)
    calls = function_calls(tool, args.elf, "bh_port_pdm_stop()")
    rep.add("hooks", "capture detach IRQ exclusion precedes vendor audio stop",
            "bh_port_irq_save()" in calls and "hx_lib_audio_stop" in calls and
            calls.index("bh_port_irq_save()") < calls.index("hx_lib_audio_stop"), calls)
    caller, _ = find_symbol(syms, r"^ATServer::execute\(")
    calls = function_calls(tool, args.elf, caller) if caller else []
    rep.add("hooks", "actual vendor AT server calls the whitespace parser guard",
            any(c.startswith("__wrap__ZN8ATParser5parse") for c in calls), "pinned SDK C++11 ABI")

    # ---- leftovers ----------------------------------------------------------
    stale = sorted(n for n in syms if any(tag in n for tag in LEFTOVER_SYMBOLS))
    rep.add("leftovers", "no symbols from the abandoned stage50 design", not stale, stale[:5])

    # ---- stack --------------------------------------------------------------
    su = load_stack_usage(args.stack_usage_root)
    chain, total, missing = [], 0, []
    for label, pattern in STACK_CHAIN:
        frames = [size for fn, size in su if re.search(pattern, fn)]
        if not frames:
            missing.append(label)
            continue
        chain.append({"function": label, "frame_bytes": max(frames)})
        total += max(frames)
    rep.facts["stack_chain"] = {"frames": chain, "known_total_bytes": total, "stack_bytes": stack,
                                "safety_verdict": "UNPROVEN",
                                "interpretation": "partial frame inventory, neither a bound nor a measured peak",
                                "not_included": ["prebuilt MLI kernel code and its nested helper calls",
                                                 "interrupt frames and nesting", "C start-up frames",
                                                 "preprocessing/libm call chains", "serial/allocator call chains",
                                                 "compiler-outlined and indirect helper calls"]}
    rep.add("stack", "frame sizes available for every function on the inference chain", not missing,
            f"missing: {missing}" if missing else f"{len(su)} functions with stack data")
    if stack:
        rep.add("stack", f"partial frame sum <= {int(POLICY['stack_known_chain_max_fraction'] * 100)}% (not stack safety)",
                total <= stack * POLICY["stack_known_chain_max_fraction"],
                f"{total} of {stack} bytes ({round(100.0 * total / stack, 1)}%)")

    # ---- baseline comparison ------------------------------------------------
    if args.baseline_elf and os.path.isfile(args.baseline_elf):
        base_secs = elf_sections(tool, args.baseline_elf)
        base_usage = {}
        for s in base_secs:
            r = region_of(s["addr"], regions)
            if r and s["size"]:
                base_usage[r] = max(base_usage.get(r, 0), s["addr"] + s["size"] - regions[r][0])
        rep.facts["delta_vs_vendor_only"] = {r: usage.get(r, 0) - base_usage.get(r, 0)
                                             for r in ("ICCM1", "SYSTEM0", "DCCM")}

    comment = run([tool("readelf"), "-p", ".comment", args.elf])
    rep.facts["compiler"] = sorted(set(re.findall(r"GCC: \([^)]*\) [\d.]+", comment)))
    rep.facts["elf"] = {"size_bytes": os.path.getsize(args.elf),
                        "sha256": hashlib.sha256(open(args.elf, "rb").read()).hexdigest()}
    rep.facts["policy"] = POLICY

    result = {"status": "PASS" if rep.ok else "FAIL", "checks": rep.checks, "facts": rep.facts}
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
    fails = [c for c in rep.checks if c["status"] == "FAIL"]
    print(f"[postlink] {len(rep.checks)} checks, {len(fails)} failed -> {result['status']}")
    for c in fails:
        print(f"  FAIL [{c['group']}] {c['check']}: {c['detail']}")
    for r in ("ICCM1", "SYSTEM0", "DCCM"):
        print(f"  {r}: used {mem[r]['used']} / {mem[r]['length']} ({mem[r]['used_percent']}%), free {mem[r]['free']}")
    print(f"  heap {heap} bytes, stack {stack} bytes, known inference chain {total} bytes")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())

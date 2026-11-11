#!/usr/bin/env python3
"""Verify that a firmware build can execute every operator of the model.

A successful link proves nothing: the vendor TFLite Micro tree compiles kernels
down to error-returning stubs when a per-model header disables a data type.
This tool checks three independent layers and fails if any of them disagrees
with the model manifest.

  1. compatibility  - operators and tensor types of the model are ones the
                      runtime supports at all (INT8 activations/filters, INT32
                      bias, no dilation, per-channel filter scales where the
                      kernels expect them).
  2. configuration  - the macro state the compiler really sees (dumped with the
                      firmware flags by `make bh_tflm_config`) does not disable
                      any (operator, data type) pair the model uses, and the
                      reference fallback has not been stripped.
  3. objects        - in the compiled kernel objects, each operator's Eval is
                      not a stub, and (with --elf) its registration function
                      and worker code are present in the linked firmware.

Exit status: 0 = PASS, 1 = FAIL, 2 = usage or input error.

Examples:
  # configuration only
  verify_tflm_ops.py --manifest firmware/himax_arc/birdhouse/model_manifest.json \
      --kernel-src <sdk>/.../edge-impulse-sdk/tensorflow/lite/micro/kernels \
      --macros <out>/birdhouse/tflm_config.macros

  # full audit of a build
  verify_tflm_ops.py ... --obj-root <out>/obj_socket_24/gnu_arcem9d_wei_r16 \
      --elf <out>/obj_socket_24/gnu_arcem9d_wei_r16/WEI_FW_gnu_arcem9d_wei_r16.elf \
      --toolchain-bin <arc toolchain>/bin --json-out result.json
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

TYPE_SUFFIX = {"INT8": "I8", "UINT8": "U8", "INT16": "I16", "FLOAT32": "F32", "BOOL": "BOOL"}

# Kernel object files and the registration symbol for each builtin operator the
# Birdhouse model can contain. Extend this table when the model changes; an
# operator missing from it is reported as a failure, never skipped.
KERNELS = {
    "CONV_2D": {"objects": ["conv.o"], "register": "tflite::Register_CONV_2D()"},
    "DEPTHWISE_CONV_2D": {"objects": ["depthwise_conv.o"], "register": "tflite::Register_DEPTHWISE_CONV_2D()"},
    "FULLY_CONNECTED": {"objects": ["fully_connected.o"], "register": "tflite::Register_FULLY_CONNECTED()"},
    "MEAN": {"objects": ["reduce.o", "reduce_common.o"], "register": "tflite::Register_MEAN()",
             "eval_name": r"tflite::EvalMean\("},
    "LOGISTIC": {"objects": ["logistic.o", "logistic_common.o"], "register": "tflite::Register_LOGISTIC()",
                 "eval_name": r"LogisticEval\("},
}

# Calls that only fetch tensors or log; an Eval that calls nothing else and is
# tiny cannot be doing arithmetic.
ACCESSOR_CALLEES = re.compile(
    r"GetEvalInput|GetEvalOutput|GetTensorShape|GetTensorData|MicroPrintf|TfLiteTypeGetName|"
    r"ReportError|DebugLog|__stack_chk")

EVAL_DEFAULT = r"(^|::)Eval\(TfLiteContext\*, TfLiteNode\*\)"


class Report:
    def __init__(self):
        self.checks = []

    def add(self, layer, name, ok, detail):
        self.checks.append({"layer": layer, "check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    @property
    def ok(self):
        return all(c["status"] == "PASS" for c in self.checks)


def read_macros(path):
    macros = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"#define\s+(\w+)(?:\s+(.*))?$", line.rstrip("\n"))
            if m:
                macros[m.group(1)] = (m.group(2) or "").strip()
    return macros


def macro_truthy(macros, name):
    """Value of `#if NAME` as the preprocessor would evaluate it."""
    if name not in macros:
        return False
    val = macros[name]
    try:
        return int(val, 0) != 0
    except ValueError:
        return True  # defined to something non-numeric: treat as enabled gate


def discover_gates(kernel_src):
    """Map operator token -> set of gate macro names consumed by kernel sources."""
    gates = {}
    pat = re.compile(r"EI_TFLITE_DISABLE_([A-Za-z0-9_]+?)_(IN|OUT)_(U8|I8|I16|F32|BOOL)\b")
    files = sorted(glob.glob(os.path.join(kernel_src, "*.cc")) + glob.glob(os.path.join(kernel_src, "*.h")))
    if not files:
        raise SystemExit(f"no kernel sources under {kernel_src}")
    for path in files:
        text = open(path, "r", encoding="utf-8", errors="replace").read()
        for m in pat.finditer(text):
            gates.setdefault(m.group(1), set()).add(m.group(0))
    return gates


def activation_range_int8(activation, scale, zero_point):
    """Quantised activation range as TFLite computes it for an INT8 output."""
    lo, hi = -128, 127
    if activation in ("RELU", "RELU6", "RELU_N1_TO_1"):
        floor_real = -1.0 if activation == "RELU_N1_TO_1" else 0.0
        lo = max(lo, zero_point + int(round(floor_real / scale)))
    if activation == "RELU6":
        hi = min(hi, zero_point + int(round(6.0 / scale)))
    if activation == "RELU_N1_TO_1":
        hi = min(hi, zero_point + int(round(1.0 / scale)))
    return lo, hi


def check_compatibility(manifest, rep, arc_backend=True):
    for io_name in ("subgraph_inputs", "subgraph_outputs"):
        for t in manifest[io_name]:
            rep.add("compatibility", f"{io_name[9:-1]} tensor '{t['name']}' is INT8",
                    t["type"] == "INT8", f"type={t['type']} shape={t['shape']}")
    for op in manifest["operators"]:
        name, idx = op["op"], op["index"]
        tag = f"op{idx} {name}"
        if name not in KERNELS:
            rep.add("compatibility", f"{tag}: operator known to this audit", False,
                    "add it to KERNELS after auditing its kernel")
            continue
        ins = [t for t in op["inputs"] if t is not None]
        outs = op["outputs"]
        act_types = {ins[0]["type"]} | {t["type"] for t in outs}
        rep.add("compatibility", f"{tag}: INT8 activations", act_types == {"INT8"}, f"types={sorted(act_types)}")
        opts = op.get("options", {})
        if name in ("CONV_2D", "DEPTHWISE_CONV_2D", "FULLY_CONNECTED"):
            filt, bias = ins[1], (ins[2] if len(ins) > 2 else None)
            rep.add("compatibility", f"{tag}: INT8 filter, INT32 bias",
                    filt["type"] == "INT8" and (bias is None or bias["type"] == "INT32"),
                    f"filter={filt['type']} bias={(bias or {}).get('type')}")
        if name in ("CONV_2D", "DEPTHWISE_CONV_2D"):
            filt = ins[1]
            out_ch = outs[0]["shape"][-1]
            rep.add("compatibility", f"{tag}: dilation 1",
                    opts.get("dilationWFactor", 1) == 1 and opts.get("dilationHFactor", 1) == 1, str(opts))
            rep.add("compatibility", f"{tag}: per-channel filter scales match output channels",
                    filt["quant_channels"] == out_ch,
                    f"scales={filt['quant_channels']} out_channels={out_ch}")
        if name == "DEPTHWISE_CONV_2D":
            rep.add("compatibility", f"{tag}: depth multiplier 1", opts.get("depthMultiplier", 1) == 1, str(opts))
        if name == "FULLY_CONNECTED" and arc_backend:
            # ARC backend, kernels/fully_connected.cc: an INT8 node is evaluated by
            # the MLI kernel only if IsMliApplicable() holds. The fallback
            # EvalQuantized() in that backend handles UINT8 and INT16 outputs but
            # has no INT8 case, so a non-applicable INT8 node fails at Invoke.
            filt, out = ins[1], outs[0]
            act = opts.get("fusedActivationFunction", "NONE")
            lo, hi = activation_range_int8(act, out["scale"], out["zero_point"])
            applicable = (filt.get("zero_point") == 0 and filt["quant_channels"] <= 1 and
                          (act == "NONE" or (lo == -128 and hi == 127)))
            rep.add("compatibility", f"{tag}: accepted by the ARC MLI kernel (no INT8 fallback exists)",
                    applicable,
                    f"activation={act} activation_range=[{lo},{hi}] filter_zero_point={filt.get('zero_point')}")


def check_configuration(manifest, gates, macros, rep, expect_arc):
    rep.add("configuration", "reference kernels not stripped (TF_LITE_STRIP_REFERENCE_IMPL undefined)",
            "TF_LITE_STRIP_REFERENCE_IMPL" not in macros,
            "needed for nodes the optimised library does not accept")
    if expect_arc:
        rep.add("configuration", "ARC MLI backend selected (EI_CLASSIFIER_TFLITE_ENABLE_ARC == 1)",
                macro_truthy(macros, "EI_CLASSIFIER_TFLITE_ENABLE_ARC"),
                f"value={macros.get('EI_CLASSIFIER_TFLITE_ENABLE_ARC')!r}")
    seen = set()
    for op in manifest["operators"]:
        name = op["op"]
        in_t = TYPE_SUFFIX.get(op["inputs"][0]["type"])
        out_t = TYPE_SUFFIX.get(op["outputs"][0]["type"])
        key = (name, in_t, out_t)
        if key in seen:
            continue
        seen.add(key)
        if in_t is None or out_t is None:
            rep.add("configuration", f"{name}: data type has a gate suffix", False, str(key))
            continue
        family = gates.get(name, set())
        if not family:
            rep.add("configuration", f"{name}: no per-type gate exists in kernel sources", True, "ungated")
            continue
        for direction, suffix in (("IN", in_t), ("OUT", out_t)):
            macro = f"EI_TFLITE_DISABLE_{name}_{direction}_{suffix}"
            disabled = macro_truthy(macros, macro)
            rep.add("configuration", f"{name}: {macro} is not set", not disabled,
                    f"value={macros.get(macro, '<undefined>')!r}")
    rep.add("configuration", "overlay marker (informational)", True,
            f"BIRDHOUSE_TFLM_OPS_OVERLAY={'defined' if 'BIRDHOUSE_TFLM_OPS_OVERLAY' in macros else 'absent'}")


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def object_functions(objdump, nm, path):
    """Return {demangled function name: {'size': int, 'callees': set}} for one object."""
    sizes = {}
    for line in run([nm, "-S", "-C", path]).splitlines():
        m = re.match(r"^[0-9a-f]+\s+([0-9a-f]+)\s+[TtWw]\s+(.*)$", line)
        if m:
            sizes[m.group(2)] = int(m.group(1), 16)
    funcs = {}
    cur = None
    for line in run([objdump, "-d", "-r", "-C", "--no-show-raw-insn", path]).splitlines():
        m = re.match(r"^[0-9a-f]+ <(.*)>:$", line)
        if m:
            cur = m.group(1)
            funcs.setdefault(cur, {"size": sizes.get(cur, 0), "callees": set()})
            continue
        m = re.match(r"^\s+[0-9a-f]+:\s+R_ARC_\w+\s+(.*)$", line)
        if m and cur is not None:
            target = re.sub(r"[+-]0x[0-9a-f]+$", "", m.group(1).strip())
            funcs[cur]["callees"].add(target)
    return funcs


def check_objects(manifest, obj_root, elf, toolchain_bin, rep):
    objdump = os.path.join(toolchain_bin, "arc-elf32-objdump")
    nm = os.path.join(toolchain_bin, "arc-elf32-nm")
    elf_syms = {}
    if elf:
        for line in run([nm, "-S", "-C", elf]).splitlines():
            m = re.match(r"^[0-9a-f]+\s+([0-9a-f]+)\s+[TtWw]\s+(.*)$", line)
            if m:
                elf_syms[m.group(2)] = int(m.group(1), 16)
    for name in sorted({op["op"] for op in manifest["operators"]}):
        spec = KERNELS.get(name)
        if spec is None:
            continue  # already failed in compatibility
        funcs = {}
        missing = []
        for obj in spec["objects"]:
            hits = glob.glob(os.path.join(obj_root, "**", "kernels", obj), recursive=True)
            if not hits:
                if obj == spec["objects"][0]:
                    missing.append(obj)
                continue
            funcs.update(object_functions(objdump, nm, hits[0]))
        if missing:
            rep.add("objects", f"{name}: kernel object present", False, f"missing {missing} under {obj_root}")
            continue
        eval_pat = re.compile(spec.get("eval_name", EVAL_DEFAULT))
        evals = {n: f for n, f in funcs.items() if eval_pat.search(n)}
        if not evals:
            rep.add("objects", f"{name}: Eval function found in kernel object", False, "no symbol matched")
            continue
        for fn, info in sorted(evals.items()):
            # Follow tail calls into helpers defined in the same object set.
            reach, todo = set(), [fn]
            total = 0
            while todo:
                cur = todo.pop()
                if cur in reach or cur not in funcs:
                    continue
                reach.add(cur)
                total += funcs[cur]["size"]
                todo.extend(funcs[cur]["callees"])
            external = set()
            for cur in reach:
                external |= {c for c in funcs[cur]["callees"] if c not in funcs}
            workers = sorted(c for c in (reach - {fn}) | external if not ACCESSOR_CALLEES.search(c))
            stub = (info["size"] < 96 and not workers)
            rep.add("objects", f"{name}: Eval is not a stub", not stub,
                    f"{fn.split('(')[0]} size={info['size']} reachable_code={total}B "
                    f"workers={[w.split('(')[0] for w in workers[:4]]}")
        if elf:
            reg = spec["register"]
            rep.add("objects", f"{name}: registration linked into firmware", reg in elf_syms,
                    f"{reg} {'size=%d' % elf_syms[reg] if reg in elf_syms else 'absent'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--kernel-src", required=True, help="vendor TFLM kernels source directory")
    ap.add_argument("--macros", required=True, help="macro dump from `make bh_tflm_config`")
    ap.add_argument("--host", action="store_true", help="macro dump comes from a host build (no ARC backend)")
    ap.add_argument("--obj-root", help="build object directory to audit")
    ap.add_argument("--elf", help="linked firmware ELF")
    ap.add_argument("--toolchain-bin", help="directory with arc-elf32-nm/objdump")
    ap.add_argument("--json-out")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    for p in (args.manifest, args.macros):
        if not os.path.isfile(p):
            print(f"missing input: {p}", file=sys.stderr)
            return 2
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    macros = read_macros(args.macros)
    gates = discover_gates(args.kernel_src)

    rep = Report()
    check_compatibility(manifest, rep, arc_backend=not args.host)
    check_configuration(manifest, gates, macros, rep, expect_arc=not args.host)
    if args.obj_root:
        if not args.toolchain_bin:
            print("--obj-root needs --toolchain-bin", file=sys.stderr)
            return 2
        check_objects(manifest, args.obj_root, args.elf, args.toolchain_bin, rep)

    result = {
        "label": args.label,
        "model_sha256": manifest["sha256"],
        "operators": manifest["operator_histogram"],
        "gate_families_in_sources": {k: sorted(v) for k, v in sorted(gates.items())},
        "layers_run": ["compatibility", "configuration"] + (["objects"] if args.obj_root else []),
        "checks": rep.checks,
        "status": "PASS" if rep.ok else "FAIL",
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")

    fails = [c for c in rep.checks if c["status"] == "FAIL"]
    print(f"[{args.label or 'tflm-ops'}] {len(rep.checks)} checks, {len(fails)} failed -> {result['status']}")
    for c in fails:
        print(f"  FAIL [{c['layer']}] {c['check']}: {c['detail']}")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())

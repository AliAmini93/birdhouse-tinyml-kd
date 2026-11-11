#!/usr/bin/env python3
"""Generate reference outputs for the host TFLite Micro inference test.

Inputs are defined by small integer rules that the C++ test re-implements, so
no large data files are needed. For every input this script records

  * an FNV-1a hash of the input bytes (the C++ side checks it before invoking,
    which proves both sides built the same input), and
  * the INT8 model output from the TensorFlow Lite interpreter, once with the
    default (optimised) kernels and once with the reference kernels.

Outputs:
  firmware/himax_arc/tests/testdata/tflm_reference_vectors.json   (evidence)
  firmware/himax_arc/tests/testdata/tflm_reference_vectors.h      (for the test)

Usage:
  python3 tools/himax/gen_tflm_reference.py
"""
import hashlib
import argparse
import json
import os
import re
import sys

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from model_manifest import load_c_array  # noqa: E402

MELS, FRAMES = 40, 249
N = MELS * FRAMES
THRESHOLD = 0.673462986946106
OUT_SCALE, OUT_ZP = 0.00390625, -128

# (name, kind, parameter). Kinds are re-implemented in tflm_vectors.h.
VECTORS = [
    ("python_reference_clip", "REFERENCE", 0),
    ("all_zero_point", "CONSTANT", -67),
    ("all_min", "CONSTANT", -128),
    ("all_max", "CONSTANT", 127),
    ("ramp_mel", "RAMP_MEL", 0),
    ("ramp_frame", "RAMP_FRAME", 0),
    ("checker", "CHECKER", 0),
    ("lcg_full_1", "LCG_FULL", 1),
    ("lcg_full_2", "LCG_FULL", 0x12345678),
    ("lcg_full_3", "LCG_FULL", 0xDEADBEEF),
    ("lcg_narrow_1", "LCG_NARROW", 7),
    ("lcg_narrow_2", "LCG_NARROW", 2026),
    ("lcg_narrow_3", "LCG_NARROW", 0xB1BD0001),
    # Derived from the real clip so that outputs land in the middle of the
    # range, where a one-step numeric difference is visible (saturated outputs
    # hide it).
    ("ref_scaled_1_8", "REF_SCALED", 1),
    ("ref_scaled_2_8", "REF_SCALED", 2),
    ("ref_scaled_3_8", "REF_SCALED", 3),
    ("ref_scaled_4_8", "REF_SCALED", 4),
    ("ref_scaled_5_8", "REF_SCALED", 5),
    ("ref_scaled_6_8", "REF_SCALED", 6),
    ("ref_scaled_7_8", "REF_SCALED", 7),
    ("ref_scaled_8_8", "REF_SCALED", 8),
    ("ref_noise_1", "REF_NOISE", 11),
    ("ref_noise_2", "REF_NOISE", 22),
    ("ref_noise_3", "REF_NOISE", 33),
    ("ref_shift_25", "REF_SHIFT", 25),
    ("ref_shift_100", "REF_SHIFT", 100),
    ("ref_shift_200", "REF_SHIFT", 200),
    ("ref_reversed", "REF_REVERSED", 0),
]
KIND_IDS = {"REFERENCE": 0, "CONSTANT": 1, "RAMP_MEL": 2, "RAMP_FRAME": 3, "CHECKER": 4,
            "LCG_FULL": 5, "LCG_NARROW": 6, "REF_SCALED": 7, "REF_NOISE": 8, "REF_SHIFT": 9,
            "REF_REVERSED": 10}
INPUT_ZP = -67


def to_int8(v):
    v &= 0xFF
    return v - 256 if v >= 128 else v


def load_reference_input():
    path = os.path.join(REPO, "firmware/preprocess/testdata/reference_input_int8.h")
    text = open(path, encoding="utf-8").read()
    body = text[text.index("{", text.index("kReferenceInputInt8")) + 1:text.index("};")]
    vals = [int(x) for x in re.findall(r"-?\d+", body)]
    if len(vals) != N:
        raise SystemExit(f"reference input has {len(vals)} values, expected {N}")
    return vals


def make_input(kind, param, reference):
    if kind == "REFERENCE":
        return list(reference)
    if kind == "CONSTANT":
        return [param] * N
    out = [0] * N
    if kind == "RAMP_MEL":
        for m in range(MELS):
            for f in range(FRAMES):
                out[m * FRAMES + f] = -128 + m * 6
    elif kind == "RAMP_FRAME":
        for m in range(MELS):
            for f in range(FRAMES):
                out[m * FRAMES + f] = -128 + f
    elif kind == "CHECKER":
        for m in range(MELS):
            for f in range(FRAMES):
                out[m * FRAMES + f] = 100 if (m + f) % 2 else -100
    elif kind in ("LCG_FULL", "LCG_NARROW"):
        state = param & 0xFFFFFFFF
        for i in range(N):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            byte = state >> 24
            out[i] = byte - 128 if kind == "LCG_FULL" else -67 + (byte % 41) - 20
    elif kind == "REF_SCALED":
        # zero_point + (ref - zero_point) * param / 8, truncating toward zero.
        for i in range(N):
            d = (reference[i] - INPUT_ZP) * param
            d = d // 8 if d >= 0 else -((-d) // 8)
            out[i] = INPUT_ZP + d
    elif kind == "REF_NOISE":
        state = param & 0xFFFFFFFF
        for i in range(N):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            v = reference[i] + ((state >> 24) % 25) - 12
            out[i] = max(-128, min(127, v))
    elif kind == "REF_SHIFT":
        for m in range(MELS):
            for f in range(FRAMES):
                out[m * FRAMES + f] = reference[m * FRAMES + (f + param) % FRAMES]
    elif kind == "REF_REVERSED":
        for m in range(MELS):
            for f in range(FRAMES):
                out[m * FRAMES + f] = reference[m * FRAMES + (FRAMES - 1 - f)]
    else:
        raise SystemExit(f"unknown kind {kind}")
    return out


def fnv1a32(values):
    h = 0x811C9DC5
    for v in values:
        h ^= v & 0xFF
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=os.path.join(REPO, "firmware/himax_arc/tests/testdata"))
    ap.add_argument("--selftest-out", default=os.path.join(REPO, "firmware/himax_arc/birdhouse/bh_selftest_expected.h"))
    args = ap.parse_args()
    import numpy as np
    import tensorflow as tf

    model = load_c_array(os.path.join(REPO, "firmware/model/student_final_int8_model_data.cc"))
    reference = load_reference_input()

    def make_interp(ref_kernels):
        kwargs = {"model_content": model}
        if ref_kernels:
            kwargs["experimental_op_resolver_type"] = tf.lite.experimental.OpResolverType.BUILTIN_REF
        it = tf.lite.Interpreter(**kwargs)
        it.allocate_tensors()
        return it

    interps = {"default": make_interp(False), "reference": make_interp(True)}
    results = []
    for name, kind, param in VECTORS:
        data = make_input(kind, param, reference)
        arr = np.array(data, dtype=np.int8).reshape(1, MELS, FRAMES, 1)
        outs = {}
        for label, it in interps.items():
            it.set_tensor(it.get_input_details()[0]["index"], arr)
            it.invoke()
            outs[label] = int(it.get_tensor(it.get_output_details()[0]["index"]).reshape(-1)[0])
        q = outs["reference"]
        p = (q - OUT_ZP) * OUT_SCALE
        results.append({
            "name": name, "kind": kind, "param": param,
            "input_fnv1a32": fnv1a32(data),
            "input_sha256": hashlib.sha256(bytes(v & 0xFF for v in data)).hexdigest(),
            "output_q_reference_kernels": outs["reference"],
            "output_q_default_kernels": outs["default"],
            "p_bird": p,
            "is_bird": bool(np.float32(p) >= np.float32(THRESHOLD)),
        })

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    summary = {
        "generator": "tools/himax/gen_tflm_reference.py",
        "tensorflow_version": tf.__version__,
        "model_sha256": hashlib.sha256(model).hexdigest(),
        "kernel_sets_agree": all(r["output_q_reference_kernels"] == r["output_q_default_kernels"]
                                 for r in results),
        "vectors": results,
    }
    with open(os.path.join(out_dir, "tflm_reference_vectors.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    lines = [
        "// Generated by tools/himax/gen_tflm_reference.py - do not edit.",
        f"// TensorFlow {tf.__version__}, reference kernels. Model sha256 {summary['model_sha256']}",
        "#ifndef BIRDHOUSE_HIMAX_TESTS_TFLM_REFERENCE_VECTORS_H_",
        "#define BIRDHOUSE_HIMAX_TESTS_TFLM_REFERENCE_VECTORS_H_",
        "",
        "#include <cstdint>",
        "",
        "namespace bh_test {",
        "",
        "enum VectorKind {",
    ]
    lines += [f"  kVector{k.title().replace('_', '')} = {v}," for k, v in KIND_IDS.items()]
    lines += [
        "};",
        "",
        "struct ReferenceVector {",
        "  const char* name;",
        "  VectorKind kind;",
        "  uint32_t param;",
        "  uint32_t input_fnv1a32;",
        "  int8_t expected_q;",
        "  bool expected_is_bird;",
        "};",
        "",
        "static const ReferenceVector kReferenceVectors[] = {",
    ]
    for r in results:
        kind = "kVector" + r["kind"].title().replace("_", "")
        lines.append(f"  {{\"{r['name']}\", {kind}, 0x{r['param'] & 0xFFFFFFFF:08x}u, "
                     f"0x{r['input_fnv1a32']:08x}u, {r['output_q_reference_kernels']}, "
                     f"{'true' if r['is_bird'] else 'false'}}},")
    lines += [
        "};",
        f"static const int kReferenceVectorCount = {len(results)};",
        "",
        "}  // namespace bh_test",
        "",
        "#endif  // BIRDHOUSE_HIMAX_TESTS_TFLM_REFERENCE_VECTORS_H_",
        "",
    ]
    with open(os.path.join(out_dir, "tflm_reference_vectors.h"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Expected values for the firmware's built-in model self-test
    # (AT+BIRDSELFTEST=k): reference features scaled by k/8 about the zero point.
    scaled = {r["param"]: r for r in results if r["kind"] == "REF_SCALED"}
    if sorted(scaled) != list(range(1, 9)):
        raise SystemExit("self-test table needs REF_SCALED vectors for k = 1..8")
    st = [
        "// Generated by tools/himax/gen_tflm_reference.py - do not edit.",
        f"// Expected raw model outputs (TensorFlow {tf.__version__} reference kernels) for the",
        "// embedded reference features scaled by k/8 about the input zero point.",
        "#ifndef BIRDHOUSE_HIMAX_BH_SELFTEST_EXPECTED_H_",
        "#define BIRDHOUSE_HIMAX_BH_SELFTEST_EXPECTED_H_",
        "",
        "#include <cstdint>",
        "",
        "namespace bh {",
        "",
        "constexpr int kSelfTestSteps = 8;",
        "// Index k = 1..8; index 0 is unused.",
        "static const int8_t kSelfTestExpectedQ[kSelfTestSteps + 1] = {",
        "    0, " + ", ".join(str(scaled[k]["output_q_reference_kernels"]) for k in range(1, 9)) + "};",
        "",
        "}  // namespace bh",
        "",
        "#endif  // BIRDHOUSE_HIMAX_BH_SELFTEST_EXPECTED_H_",
        "",
    ]
    with open(args.selftest_out, "w",
              encoding="utf-8") as f:
        f.write("\n".join(st))

    print(f"kernel sets agree: {summary['kernel_sets_agree']}")
    for r in results:
        print(f"  {r['name']:<24} q_ref={r['output_q_reference_kernels']:>5} "
              f"q_default={r['output_q_default_kernels']:>5} p={r['p_bird']:.4f} "
              f"{'BIRD' if r['is_bird'] else 'NON-BIRD'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Extract an operator/tensor manifest from the tracked model C array.

The manifest is the single source of truth for "what the model needs from the
runtime": every operator, its builtin options, and the data type and
quantisation of every tensor it touches. Other tools check the firmware build
against it.

Usage:
  python3 tools/himax/model_manifest.py \
      --model-cc firmware/model/student_final_int8_model_data.cc \
      --out firmware/himax_arc/birdhouse/model_manifest.json
"""
import argparse
import hashlib
import json
import os
import re
import sys

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")


def load_c_array(path):
    """Return the bytes of the first brace-delimited byte array in a C++ file."""
    text = open(path, "r", encoding="utf-8").read()
    start = text.index("{", text.index("g_student_final_int8_model_data[]"))
    end = text.index("};", start)
    body = text[start + 1:end]
    data = bytes(int(tok, 16) for tok in re.findall(r"0x([0-9a-fA-F]{2})", body))
    m = re.search(r"_len\s*=\s*(\d+)u?;", text)
    if not m:
        raise SystemExit("model length constant not found")
    if int(m.group(1)) != len(data):
        raise SystemExit(f"length mismatch: array {len(data)} vs constant {m.group(1)}")
    return data


def enum_names(enum_cls):
    return {v: k for k, v in vars(enum_cls).items() if not k.startswith("_") and isinstance(v, int)}


def build_manifest(model_bytes):
    from tensorflow.lite.python import schema_py_generated as fb
    import numpy as np

    model = fb.ModelT.InitFromPackedBuf(model_bytes, 0)
    op_names = enum_names(fb.BuiltinOperator)
    type_names = enum_names(fb.TensorType)
    act_names = enum_names(fb.ActivationFunctionType)
    pad_names = enum_names(fb.Padding)

    if len(model.subgraphs) != 1:
        raise SystemExit("expected exactly one subgraph")
    sg = model.subgraphs[0]

    def tensor_info(idx):
        if idx < 0:
            return None
        t = sg.tensors[idx]
        q = t.quantization
        scales = list(map(float, q.scale)) if q is not None and q.scale is not None else []
        zps = list(map(int, q.zeroPoint)) if q is not None and q.zeroPoint is not None else []
        buf = model.buffers[t.buffer]
        is_const = buf.data is not None and len(buf.data) > 0
        info = {
            "index": int(idx),
            "name": t.name.decode() if isinstance(t.name, bytes) else str(t.name),
            "type": type_names[t.type],
            "shape": [int(x) for x in (t.shape if t.shape is not None else [])],
            "is_constant": bool(is_const),
            "quant_channels": len(scales),
            "quantized_dimension": int(q.quantizedDimension) if q is not None else 0,
        }
        if len(scales) <= 1:
            info["scale"] = scales[0] if scales else None
            info["zero_point"] = zps[0] if zps else None
        else:
            info["scale_min"] = min(scales)
            info["scale_max"] = max(scales)
            info["zero_points_all_zero"] = all(z == 0 for z in zps)
        return info

    ops = []
    for i, op in enumerate(sg.operators):
        code = model.operatorCodes[op.opcodeIndex]
        builtin = max(int(code.builtinCode), int(code.deprecatedBuiltinCode))
        entry = {
            "index": i,
            "op": op_names[builtin],
            "version": int(code.version),
            "inputs": [tensor_info(int(x)) for x in op.inputs],
            "outputs": [tensor_info(int(x)) for x in op.outputs],
        }
        o = op.builtinOptions
        opts = {}
        if o is not None:
            for field, names in (("fusedActivationFunction", act_names), ("padding", pad_names)):
                if hasattr(o, field):
                    opts[field] = names[getattr(o, field)]
            for field in ("strideW", "strideH", "dilationWFactor", "dilationHFactor",
                          "depthMultiplier", "keepDims", "keepNumDims"):
                if hasattr(o, field):
                    v = getattr(o, field)
                    opts[field] = bool(v) if isinstance(v, (bool, np.bool_)) else int(v)
        entry["options"] = opts
        ops.append(entry)

    # Peak activation memory: sum of the non-constant tensors that are live at each op.
    peak = 0
    peak_at = None
    for e in ops:
        live = 0
        for t in e["inputs"] + e["outputs"]:
            if t is not None and not t["is_constant"]:
                n = 1
                for d in t["shape"]:
                    n *= d
                live += n * {"INT8": 1, "UINT8": 1, "INT16": 2, "INT32": 4, "FLOAT32": 4}.get(t["type"], 4)
        if live > peak:
            peak, peak_at = live, e["index"]

    return {
        "schema_version": int(model.version),
        "description": model.description.decode() if model.description else "",
        "subgraph_inputs": [tensor_info(int(x)) for x in sg.inputs],
        "subgraph_outputs": [tensor_info(int(x)) for x in sg.outputs],
        "operators": ops,
        "operator_histogram": {name: sum(1 for e in ops if e["op"] == name)
                               for name in sorted({e["op"] for e in ops})},
        "peak_live_activation_bytes": peak,
        "peak_live_activation_at_op": peak_at,
        "tensor_count": len(sg.tensors),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-cc", required=True)
    ap.add_argument("--tflite", help="optional .tflite to cross-check byte equality")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = load_c_array(args.model_cc)
    manifest = {
        "source": args.model_cc,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if args.tflite and os.path.exists(args.tflite):
        other = open(args.tflite, "rb").read()
        manifest["tflite_cross_check"] = {
            "path": args.tflite,
            "identical": other == data,
            "sha256": hashlib.sha256(other).hexdigest(),
        }
        if other != data:
            raise SystemExit("C array differs from the .tflite file")
    manifest.update(build_manifest(data))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"model {manifest['size_bytes']} bytes sha256 {manifest['sha256'][:16]}…")
    print("operators:", manifest["operator_histogram"])
    print("peak live activations:", manifest["peak_live_activation_bytes"],
          "bytes at op", manifest["peak_live_activation_at_op"])
    for t in manifest["subgraph_inputs"] + manifest["subgraph_outputs"]:
        print(f"  io {t['name']}: {t['type']} {t['shape']} scale={t.get('scale')} zp={t.get('zero_point')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

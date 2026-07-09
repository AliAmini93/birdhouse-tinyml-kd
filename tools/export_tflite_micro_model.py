#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf


def c_array_u8(data: bytes, values_per_line: int = 12) -> str:
    vals = list(data)
    lines = []
    for i in range(0, len(vals), values_per_line):
        chunk = vals[i:i + values_per_line]
        lines.append("  " + ", ".join(f"0x{x:02x}" for x in chunk) + ",")
    return "\n".join(lines)


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_rel(path: Path, repo: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def parse_ops(model_path: Path) -> list[dict[str, Any]]:
    interpreter = tf.lite.Interpreter(model_path=str(model_path))
    try:
        ops = interpreter._get_ops_details()
    except Exception:
        return []
    out = []
    for op in ops:
        row = {}
        for k, v in op.items():
            if isinstance(v, np.ndarray):
                row[k] = v.tolist()
            elif isinstance(v, (np.integer, np.floating)):
                row[k] = v.item()
            else:
                row[k] = v
        out.append(row)
    return out


def run_reference_inference(model_path: Path, reference_bin: Path, threshold: float) -> dict[str, Any] | None:
    if not reference_bin.exists():
        return None

    x = np.fromfile(reference_bin, dtype=np.int8)
    expected = 40 * 249
    if x.size != expected:
        raise RuntimeError(f"Reference input size mismatch: got {x.size}, expected {expected}")

    x = x.reshape(1, 40, 249, 1)

    interpreter = tf.lite.Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    if input_details["dtype"] != np.int8:
        raise RuntimeError(f"Expected INT8 input model, got {input_details['dtype']}")

    interpreter.set_tensor(input_details["index"], x.astype(np.int8))
    interpreter.invoke()

    yq = interpreter.get_tensor(output_details["index"]).reshape(-1)
    if yq.size != 1:
        raise RuntimeError(f"Expected scalar output, got shape {yq.shape}")

    output_q = int(yq[0])
    out_scale, out_zero = output_details["quantization"]
    p_bird = float((output_q - int(out_zero)) * float(out_scale))

    return {
        "reference_input_bin": safe_rel(reference_bin, model_path.parents[4]) if len(model_path.parents) > 4 else str(reference_bin),
        "input_shape": input_details["shape"].tolist(),
        "input_dtype": str(input_details["dtype"]),
        "input_quantization": input_details["quantization"],
        "output_shape": output_details["shape"].tolist(),
        "output_dtype": str(output_details["dtype"]),
        "output_quantization": output_details["quantization"],
        "output_int8": output_q,
        "p_bird": p_bird,
        "threshold": threshold,
        "is_bird": bool(p_bird >= threshold),
    }


def write_model_data(repo: Path, model_path: Path, out_dir: Path) -> dict[str, Any]:
    data = model_path.read_bytes()
    out_dir.mkdir(parents=True, exist_ok=True)

    h = out_dir / "student_final_int8_model_data.h"
    cc = out_dir / "student_final_int8_model_data.cc"

    h.write_text(f'''#ifndef BIRDHOUSE_STUDENT_FINAL_INT8_MODEL_DATA_H_
#define BIRDHOUSE_STUDENT_FINAL_INT8_MODEL_DATA_H_

#include <cstdint>

namespace birdhouse {{

extern const unsigned char g_student_final_int8_model_data[];
extern const unsigned int g_student_final_int8_model_data_len;

}}  // namespace birdhouse

#endif  // BIRDHOUSE_STUDENT_FINAL_INT8_MODEL_DATA_H_
''', encoding="utf-8")

    cc.write_text(f'''#include "firmware/model/student_final_int8_model_data.h"

namespace birdhouse {{

alignas(16) const unsigned char g_student_final_int8_model_data[] = {{
{c_array_u8(data)}
}};

const unsigned int g_student_final_int8_model_data_len = {len(data)}u;

}}  // namespace birdhouse
''', encoding="utf-8")

    return {
        "model_data_h": str(h.relative_to(repo)),
        "model_data_cc": str(cc.relative_to(repo)),
        "model_size_bytes": len(data),
        "model_size_kib": len(data) / 1024.0,
    }


def write_model_constants(repo: Path, out_dir: Path, export_summary: dict[str, Any]) -> str:
    path = out_dir / "model_constants.h"

    feature = export_summary.get("feature_pipeline", {})
    threshold = float(export_summary.get("recommended_threshold", 0.5))
    int8_in = export_summary.get("int8_input_details", {})
    int8_out = export_summary.get("int8_output_details", {})
    in_q = int8_in.get("quantization", [0.0200184378772974, -67])
    out_q = int8_out.get("quantization", [0.00390625, -128])

    path.write_text(f'''#ifndef BIRDHOUSE_MODEL_CONSTANTS_H_
#define BIRDHOUSE_MODEL_CONSTANTS_H_

#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {{

constexpr const char* kStudentModelName = "student_5s_kd_hw08_kw02_int8";
constexpr int kStudentModelVersion = 1;

constexpr int kModelInputBatch = 1;
constexpr int kModelInputMels = {int(feature.get("n_mels", 40))};
constexpr int kModelInputFrames = {int(feature.get("expected_frames", 249))};
constexpr int kModelInputChannels = 1;
constexpr int kModelInputElements = kModelInputMels * kModelInputFrames * kModelInputChannels;

constexpr int kModelOutputElements = 1;

constexpr float kModelInputScale = {float(in_q[0])}f;
constexpr int kModelInputZeroPoint = {int(in_q[1])};

constexpr float kModelOutputScale = {float(out_q[0])}f;
constexpr int kModelOutputZeroPoint = {int(out_q[1])};

constexpr float kModelBirdThreshold = {threshold}f;

// Starting value only. Measure/tune on the actual TFLite Micro ESP32S3 build.
constexpr int kTensorArenaSizeBytes = 160 * 1024;

}}  // namespace birdhouse

#endif  // BIRDHOUSE_MODEL_CONSTANTS_H_
''', encoding="utf-8")

    return str(path.relative_to(repo))


def write_reference_output_header(repo: Path, ref: dict[str, Any] | None) -> str | None:
    if ref is None:
        return None

    test_dir = repo / "firmware" / "inference" / "testdata"
    test_dir.mkdir(parents=True, exist_ok=True)
    path = test_dir / "reference_model_output.h"

    path.write_text(f'''#ifndef BIRDHOUSE_REFERENCE_MODEL_OUTPUT_H_
#define BIRDHOUSE_REFERENCE_MODEL_OUTPUT_H_

#include <cstdint>

namespace birdhouse {{

constexpr int8_t kReferenceModelOutputInt8 = static_cast<int8_t>({int(ref["output_int8"])});
constexpr float kReferenceModelOutputPBird = {float(ref["p_bird"])}f;
constexpr bool kReferenceModelOutputIsBird = {"true" if ref["is_bird"] else "false"};

}}  // namespace birdhouse

#endif  // BIRDHOUSE_REFERENCE_MODEL_OUTPUT_H_
''', encoding="utf-8")

    return str(path.relative_to(repo))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--model-path", default="student/final_models/5s_kd_hw08_kw02/student_final_int8.tflite")
    p.add_argument("--export-summary", default="student/final_models/5s_kd_hw08_kw02/export_summary.json")
    p.add_argument("--reference-input-bin", default="firmware/preprocess/testdata/reference_input_int8.bin")
    p.add_argument("--out-dir", default="firmware/model")
    args = p.parse_args()

    repo = Path(args.repo_root).resolve()
    model_path = (repo / args.model_path).resolve()
    export_summary_path = (repo / args.export_summary).resolve()
    reference_input_bin = (repo / args.reference_input_bin).resolve()
    out_dir = (repo / args.out_dir).resolve()

    if not model_path.exists():
        raise FileNotFoundError(model_path)
    if not export_summary_path.exists():
        raise FileNotFoundError(export_summary_path)

    export_summary = read_json(export_summary_path)
    threshold = float(export_summary.get("recommended_threshold", 0.5))

    model_data = write_model_data(repo, model_path, out_dir)
    constants_path = write_model_constants(repo, out_dir, export_summary)

    ops = parse_ops(model_path)
    ref = run_reference_inference(model_path, reference_input_bin, threshold)
    ref_header = write_reference_output_header(repo, ref)

    summary = {
        "model_path": safe_rel(model_path, repo),
        "export_summary_path": safe_rel(export_summary_path, repo),
        "model_data": model_data,
        "model_constants_h": constants_path,
        "ops": ops,
        "reference_inference": ref,
        "reference_output_header": ref_header,
    }

    summary_path = out_dir / "model_asset_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Generated TFLite Micro model assets:")
    print(f"  {repo / model_data['model_data_h']}")
    print(f"  {repo / model_data['model_data_cc']}")
    print(f"  {repo / constants_path}")
    if ref_header:
        print(f"  {repo / ref_header}")
    print(f"  {summary_path}")
    print("")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, sys
from pathlib import Path
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import numpy as np
import pandas as pd
import tensorflow as tf

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "student"))
import train_student_5s_hardlabel_baseline as v1
import train_student_5s_hardlabel_baseline_v2 as v2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--final-name", default="5s_kd_hw08_kw02")
    p.add_argument("--representative-samples", type=int, default=512)
    p.add_argument("--validation-samples", type=int, default=256)
    p.add_argument("--seed", type=int, default=46)
    p.add_argument("--force-cache", action="store_true")
    return p.parse_args()


def tflite_one(interpreter, x):
    inp = interpreter.get_input_details()[0]; out = interpreter.get_output_details()[0]
    z = x.astype(np.float32)
    if inp["dtype"] in (np.int8, np.uint8):
        scale, zero = inp["quantization"]
        z = np.round(z / scale + zero)
        z = np.clip(z, np.iinfo(inp["dtype"]).min, np.iinfo(inp["dtype"]).max).astype(inp["dtype"])
    else:
        z = z.astype(inp["dtype"])
    interpreter.set_tensor(inp["index"], z); interpreter.invoke()
    y = interpreter.get_tensor(out["index"])
    if out["dtype"] in (np.int8, np.uint8):
        scale, zero = out["quantization"]; y = (y.astype(np.float32) - zero) * scale
    return float(np.reshape(y, [-1])[0])


def main():
    a = parse_args(); repo = Path(a.repo_root).resolve(); final = repo / "student" / "final_models" / a.final_name
    weights = final / "student_final.weights.h5"; normalizer_path = final / "normalizer.json"
    if not weights.exists(): raise FileNotFoundError(weights)
    if not normalizer_path.exists(): raise FileNotFoundError(normalizer_path)
    with open(normalizer_path, "r", encoding="utf-8") as f: norm = json.load(f)
    final_summary = {}
    if (final / "final_training_summary.json").exists():
        with open(final / "final_training_summary.json", "r", encoding="utf-8") as f: final_summary = json.load(f)
    cfg = v1.Config(); cache = repo / "student" / "cache" / f"fsc22_logmel_{int(cfg.duration_s)}s_{cfg.sample_rate}hz_{cfg.n_mels}mel_{int(cfg.hop_ms)}ms.npz"
    df = v1.collect_dataset(repo / "Dataset" / "fsc22")
    X, y, rel_paths, folders = v1.load_or_build_cache(df, cache, cfg, a.force_cache)
    Xn = ((X - float(norm["mean"])) / float(norm["std"])).astype(np.float32)[..., None]
    model = v2.build_model_v2((Xn.shape[1], Xn.shape[2], 1), cfg.learning_rate, 0.75, 2.0)
    model.load_weights(weights); model.save(final / "student_final.keras", include_optimizer=False)
    fp32 = final / "student_final_fp32.tflite"; int8 = final / "student_final_int8.tflite"
    conv = tf.lite.TFLiteConverter.from_keras_model(model); fp32.write_bytes(conv.convert())
    rng = np.random.default_rng(a.seed); rep_n = min(a.representative_samples, len(Xn)); rep_idx = rng.choice(len(Xn), rep_n, replace=False)
    def rep_data():
        for i in rep_idx: yield [Xn[i:i+1].astype(np.float32)]
    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = rep_data
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = tf.int8; conv.inference_output_type = tf.int8
    int8.write_bytes(conv.convert())
    val_n = min(a.validation_samples, len(Xn)); val_idx = rng.choice(len(Xn), val_n, replace=False)
    keras_pred = model.predict(Xn[val_idx], batch_size=32, verbose=0).reshape(-1)
    interp32 = tf.lite.Interpreter(model_path=str(fp32)); interp32.allocate_tensors()
    interp8 = tf.lite.Interpreter(model_path=str(int8)); interp8.allocate_tensors()
    pred32 = np.array([tflite_one(interp32, Xn[i:i+1]) for i in val_idx], dtype=np.float32)
    pred8 = np.array([tflite_one(interp8, Xn[i:i+1]) for i in val_idx], dtype=np.float32)
    pd.DataFrame({"file_path": [rel_paths[i] for i in val_idx], "source_folder": [folders[i] for i in val_idx], "hard_label": y[val_idx], "keras_p_bird": keras_pred, "tflite_fp32_p_bird": pred32, "tflite_int8_p_bird": pred8, "absdiff_fp32": np.abs(keras_pred-pred32), "absdiff_int8": np.abs(keras_pred-pred8)}).to_csv(final / "tflite_validation_subset.csv", index=False)
    int8_in = interp8.get_input_details()[0]; int8_out = interp8.get_output_details()[0]
    summary = {
        "final_name": a.final_name, "fp32_tflite_path": str(fp32.relative_to(repo)), "int8_tflite_path": str(int8.relative_to(repo)),
        "fp32_tflite_size_bytes": int(fp32.stat().st_size), "int8_tflite_size_bytes": int(int8.stat().st_size),
        "recommended_threshold": final_summary.get("recommended_threshold"), "normalizer": norm,
        "feature_pipeline": {"sample_rate": cfg.sample_rate, "duration_s": cfg.duration_s, "n_mels": cfg.n_mels, "frame_ms": cfg.frame_ms, "hop_ms": cfg.hop_ms, "expected_frames": cfg.expected_frames},
        "int8_input_details": {"shape": int8_in["shape"].tolist(), "dtype": str(int8_in["dtype"]), "quantization": int8_in["quantization"]},
        "int8_output_details": {"shape": int8_out["shape"].tolist(), "dtype": str(int8_out["dtype"]), "quantization": int8_out["quantization"]},
        "validation": {"fp32_mean_absdiff_vs_keras": float(np.mean(np.abs(keras_pred-pred32))), "fp32_max_absdiff_vs_keras": float(np.max(np.abs(keras_pred-pred32))), "int8_mean_absdiff_vs_keras": float(np.mean(np.abs(keras_pred-pred8))), "int8_max_absdiff_vs_keras": float(np.max(np.abs(keras_pred-pred8)))}
    }
    with open(final / "export_summary.json", "w", encoding="utf-8") as f: json.dump(summary, f, indent=2)
    lines = ["# Final Student TFLite Export Report", "", "## Model files", "", f"- FP32 TFLite: `{fp32.relative_to(repo)}`", f"- INT8 TFLite: `{int8.relative_to(repo)}`", "", "## Size", "", f"- FP32 size bytes: {summary['fp32_tflite_size_bytes']}", f"- INT8 size bytes: {summary['int8_tflite_size_bytes']}", "", "## INT8 quantization", "", f"- Input dtype: `{summary['int8_input_details']['dtype']}`", f"- Input quantization: `{summary['int8_input_details']['quantization']}`", f"- Output dtype: `{summary['int8_output_details']['dtype']}`", f"- Output quantization: `{summary['int8_output_details']['quantization']}`", "", "## Validation against Keras", "", f"- FP32 mean abs diff: {summary['validation']['fp32_mean_absdiff_vs_keras']}", f"- FP32 max abs diff: {summary['validation']['fp32_max_absdiff_vs_keras']}", f"- INT8 mean abs diff: {summary['validation']['int8_mean_absdiff_vs_keras']}", f"- INT8 max abs diff: {summary['validation']['int8_max_absdiff_vs_keras']}", "", "## Deployment constants", "", "```text", f"sample_rate = {cfg.sample_rate}", f"duration_s = {cfg.duration_s}", f"n_mels = {cfg.n_mels}", f"frame_ms = {cfg.frame_ms}", f"hop_ms = {cfg.hop_ms}", f"expected_frames = {cfg.expected_frames}", f"normalizer_mean = {norm['mean']}", f"normalizer_std = {norm['std']}", f"recommended_threshold = {summary['recommended_threshold']}", "```", ""]
    (final / "export_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("="*70); print("EXPORT COMPLETE"); print("FP32:", fp32, fp32.stat().st_size, "bytes"); print("INT8:", int8, int8.stat().st_size, "bytes"); print("Report:", final / "export_report.md"); print("="*70)

if __name__ == "__main__": main()

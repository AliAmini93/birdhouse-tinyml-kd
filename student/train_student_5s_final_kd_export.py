#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math, os, random, sys
from pathlib import Path
from dataclasses import asdict

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "student"))
import train_student_5s_hardlabel_baseline as v1
import train_student_5s_hardlabel_baseline_v2 as v2
import train_student_5s_kd_binary_v1 as kd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", default=".")
    p.add_argument("--final-name", default="5s_kd_hw08_kw02")
    p.add_argument("--selected-run", default="5s_kd_binary_hw08_kw02")
    p.add_argument("--soft-label-csv", default="teacher_kd/soft_labels/fsc22_soft_labels_binary.csv")
    p.add_argument("--epochs", type=int, default=0, help="0 = median epochs_ran from selected CV run")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--seed", type=int, default=45)
    p.add_argument("--hard-weight", type=float, default=0.8)
    p.add_argument("--kd-weight", type=float, default=0.2)
    p.add_argument("--focal-alpha", type=float, default=0.75)
    p.add_argument("--focal-gamma", type=float, default=2.0)
    p.add_argument("--force-cache", action="store_true")
    p.add_argument("--cpu-only", action="store_true")
    return p.parse_args()


def set_seed(seed, cpu_only=False):
    random.seed(seed); np.random.seed(seed); tf.keras.utils.set_random_seed(seed)
    if cpu_only:
        tf.config.set_visible_devices([], "GPU")
        print("CPU-only mode enabled.")
    elif not tf.config.list_physical_devices("GPU"):
        print("TensorFlow GPU not visible; using CPU.")


def read_json(path):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    return {}


def derive_epochs(repo, selected_run):
    p = repo / "student" / "results" / selected_run / "fold_metrics.csv"
    if not p.exists(): return 40
    try:
        df = pd.read_csv(p)
        return int(max(10, min(90, round(float(df["epochs_ran"].median())))))
    except Exception:
        return 40


def metrics(y, prob, thr):
    pred = (prob >= thr).astype(np.int32)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(thr),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "fpr": float(fp / (fp + tn)) if (fp + tn) else 0.0,
    }


def report(out, s):
    lines = [
        "# Final Student 5 s KD Training Report", "",
        "This model is trained on the full FSC22 dataset using the selected KD sweep configuration.", "",
        "## Selected configuration", "", "```text",
        f"final_name = {s['final_name']}", f"selected_cv_run = {s['selected_run']}",
        f"hard_weight = {s['hard_weight']}", f"kd_weight = {s['kd_weight']}",
        f"epochs = {s['epochs']}", f"batch_size = {s['batch_size']}",
        "input = 5 s / 16 kHz / 40-bin log-mel / shape 40 x 249 x 1", "```", "",
        "## Full-dataset apparent metrics", "",
        "These metrics are measured on the full training set. The model-selection evidence remains the CV sweep.", "",
        "### Threshold 0.5", ""
    ]
    for k, v in s["full_dataset_metrics_0p5"].items(): lines.append(f"- {k}: {v}")
    lines += ["", "### Recommended CV threshold", "", f"- recommended_threshold: {s['recommended_threshold']}"]
    for k, v in s["full_dataset_metrics_recommended_threshold"].items(): lines.append(f"- {k}: {v}")
    lines += ["", "## Selected CV reference", ""]
    ref = s.get("selected_cv_reference", {})
    for k in ["precision_0p5_mean", "recall_0p5_mean", "f1_0p5_mean", "pr_auc_mean", "roc_auc_mean", "recall_at_fpr_target_mean"]:
        if k in ref: lines.append(f"- {k}: {ref[k]}")
    lines += ["", "## Saved files", "", "- `student_final.keras`", "- `student_final.weights.h5`", "- `normalizer.json`", "- `final_training_summary.json`", "- `final_training_report.md`", ""]
    (out / "final_training_report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    a = parse_args(); repo = Path(a.repo_root).resolve(); set_seed(a.seed, a.cpu_only)
    out = repo / "student" / "final_models" / a.final_name; out.mkdir(parents=True, exist_ok=True)
    cfg = v1.Config(batch_size=a.batch_size, seed=a.seed)
    epochs = a.epochs if a.epochs > 0 else derive_epochs(repo, a.selected_run)
    print("="*70); print("FINAL STUDENT 5S KD TRAINING"); print("="*70)
    print("Output dir:", out); print("Epochs:", epochs); print("KD weights:", a.hard_weight, a.kd_weight)
    df = v1.collect_dataset(repo / "Dataset" / "fsc22")
    cache = repo / "student" / "cache" / f"fsc22_logmel_{int(cfg.duration_s)}s_{cfg.sample_rate}hz_{cfg.n_mels}mel_{int(cfg.hop_ms)}ms.npz"
    X, y, rel_paths, folders = v1.load_or_build_cache(df, cache, cfg, a.force_cache)
    y_soft, soft_info = kd.load_teacher_soft_labels((repo / a.soft_label_csv).resolve(), rel_paths, len(y))
    mean, std = float(X.mean()), float(X.std()); std = std if std > 1e-6 else 1.0
    Xn = ((X - mean) / std).astype(np.float32); normalizer = {"mean": mean, "std": std, "mode": "full_dataset"}
    input_shape = (Xn.shape[1], Xn.shape[2], 1)
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    steps = int(math.ceil((2 * n_neg) / a.batch_size))
    seq = kd.BalancedKDAugmentedSequence(Xn, y, y_soft, a.batch_size, steps, a.seed + 3000, True)
    model = v2.build_model_v2(input_shape, cfg.learning_rate, a.focal_alpha, a.focal_gamma)
    model.compile(optimizer=tf.keras.optimizers.Adam(cfg.learning_rate), loss=kd.kd_loss_factory(a.hard_weight, a.kd_weight, a.focal_alpha, a.focal_gamma))
    hist = model.fit(seq, epochs=epochs, verbose=2, callbacks=[tf.keras.callbacks.ReduceLROnPlateau(monitor="loss", mode="min", factor=0.5, patience=6, min_lr=1e-5, verbose=1)])
    pd.DataFrame(hist.history).to_csv(out / "final_training_history.csv", index=False)
    model.save_weights(out / "student_final.weights.h5"); model.save(out / "student_final.keras")
    with open(out / "normalizer.json", "w", encoding="utf-8") as f: json.dump(normalizer, f, indent=2)
    pd.DataFrame({"file_path": rel_paths, "source_folder": folders, "binary_hard_label": y, "teacher_p_bird": y_soft}).to_csv(out / "final_training_manifest.csv", index=False)
    prob = model.predict(Xn[..., None].astype(np.float32), batch_size=a.batch_size, verbose=0).reshape(-1)
    ref = read_json(repo / "student" / "results" / a.selected_run / "metrics_summary.json")
    rec_thr = float(ref.get("oof_metrics_target_fpr", {}).get("threshold", 0.5))
    s = {
        "final_name": a.final_name, "selected_run": a.selected_run, "hard_weight": a.hard_weight, "kd_weight": a.kd_weight,
        "focal_alpha": a.focal_alpha, "focal_gamma": a.focal_gamma, "epochs": epochs, "batch_size": a.batch_size,
        "steps_per_epoch": steps, "n_clips": int(len(y)), "n_bird": n_pos, "n_nonbird": n_neg,
        "input_shape": list(input_shape), "feature_config": asdict(cfg), "normalizer": normalizer, "soft_label_info": soft_info,
        "recommended_threshold": rec_thr, "full_dataset_metrics_0p5": metrics(y, prob, 0.5),
        "full_dataset_metrics_recommended_threshold": metrics(y, prob, rec_thr),
        "full_dataset_pr_auc": float(average_precision_score(y, prob)), "full_dataset_roc_auc": float(roc_auc_score(y, prob)),
        "selected_cv_reference": ref,
    }
    with open(out / "final_training_summary.json", "w", encoding="utf-8") as f: json.dump(s, f, indent=2)
    report(out, s)
    print("="*70); print("FINAL TRAINING COMPLETE"); print("Report:", out / "final_training_report.md"); print("Recommended threshold:", rec_thr); print("="*70)

if __name__ == "__main__": main()

#!/usr/bin/env python3
# ==============================================================================
# train_student_5s_kd_binary_v1.py
# ------------------------------------------------------------------------------
# 5-second binary KD Student v1.
#
# Purpose:
#   Fair comparison against the stronger hard-label baseline v2.
#
# Fixed Student pipeline:
#   5 s / 16 kHz / 40-bin log-mel / compact DS-CNN v2 architecture.
#
# Training:
#   balanced batches + feature augmentation + binary KD loss.
#
# Loss:
#   total_loss =
#     hard_weight * focal_loss(y_hard, p_student)
#     +
#     kd_weight   * BCE(p_teacher_bird, p_student)
#
# Default:
#   hard_weight = 0.5
#   kd_weight   = 0.5
#
# Run:
#   cd /media/armin/External/AhmadWorks/audioclassification
#   mkdir -p student/results/5s_kd_binary_v1
#   "/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3" \
#     student/train_student_5s_kd_binary_v1.py \
#     2>&1 | tee student/results/5s_kd_binary_v1/train_console.log
# ==============================================================================

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold

# Reuse the already committed v1/v2 Student code for feature extraction,
# augmentation and architecture.
REPO_ROOT_GUESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT_GUESS / "student"))

import train_student_5s_hardlabel_baseline as v1  # noqa: E402
import train_student_5s_hardlabel_baseline_v2 as v2  # noqa: E402


RUN_NAME = "5s_kd_binary_v1"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train 5 s binary KD Student v1.")
    p.add_argument("--repo-root", default=".", help="Repository root.")
    p.add_argument(
        "--soft-label-csv",
        default="teacher_kd/soft_labels/fsc22_soft_labels_binary.csv",
        help="Binary teacher soft-label CSV.",
    )
    p.add_argument("--epochs", type=int, default=90)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--patience", type=int, default=14)
    p.add_argument("--seed", type=int, default=44)
    p.add_argument("--force-cache", action="store_true")
    p.add_argument("--cpu-only", action="store_true")
    p.add_argument("--hard-weight", type=float, default=0.5)
    p.add_argument("--kd-weight", type=float, default=0.5)
    p.add_argument("--focal-alpha", type=float, default=0.75)
    p.add_argument("--focal-gamma", type=float, default=2.0)
    p.add_argument("--steps-per-epoch", type=int, default=0,
                   help="0 = auto: balanced coverage based on negative count.")
    p.add_argument("--target-fpr", type=float, default=0.02)
    return p.parse_args()


def set_determinism(seed: int, cpu_only: bool = False) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)

    if cpu_only:
        tf.config.set_visible_devices([], "GPU")
        print("CPU-only mode enabled.")
        return

    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        for gpu in gpus:
            try:
                tf.config.experimental.set_memory_growth(gpu, True)
            except Exception:
                pass
        print(f"TensorFlow GPUs visible: {len(gpus)}")
    else:
        print("TensorFlow GPU not visible; using CPU.")


def metrics_at_threshold(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> Dict[str, float]:
    y_pred = (y_prob >= threshold).astype(np.int32)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "fpr": float(fp / (fp + tn)) if (fp + tn) else 0.0,
    }


def threshold_for_target_fpr(y_true: np.ndarray, y_prob: np.ndarray, target_fpr: float) -> Dict[str, float]:
    fpr, tpr, thr = roc_curve(y_true, y_prob)
    valid = np.where(fpr <= target_fpr)[0]
    if len(valid) == 0:
        chosen = int(np.argmin(fpr))
    else:
        best_tpr = np.max(tpr[valid])
        tied = valid[np.where(tpr[valid] == best_tpr)[0]]
        chosen = int(tied[-1])
    threshold = float(thr[chosen])
    if math.isinf(threshold):
        threshold = 1.0
    m = metrics_at_threshold(y_true, y_prob, threshold)
    m["target_fpr"] = float(target_fpr)
    return m


def safe_auc(y_true: np.ndarray, y_prob: np.ndarray, kind: str) -> float:
    try:
        if kind == "roc":
            return float(roc_auc_score(y_true, y_prob))
        if kind == "pr":
            return float(average_precision_score(y_true, y_prob))
    except Exception:
        return float("nan")
    raise ValueError(kind)


def per_folder_metrics(folders: List[str], y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> pd.DataFrame:
    rows = []
    y_pred = (y_prob >= threshold).astype(np.int32)
    folders_arr = np.array(folders)
    for folder in sorted(set(folders)):
        mask = folders_arr == folder
        yt = y_true[mask]
        yp = y_pred[mask]
        prob = y_prob[mask]
        n = int(mask.sum())
        is_bird_folder = folder in v1.BIRD_FOLDERS
        rows.append({
            "source_folder": folder,
            "is_bird_folder": bool(is_bird_folder),
            "n": n,
            "mean_p_bird": float(np.mean(prob)) if n else np.nan,
            "min_p_bird": float(np.min(prob)) if n else np.nan,
            "max_p_bird": float(np.max(prob)) if n else np.nan,
            "positive_predictions": int(np.sum(yp == 1)),
            "correct": int(np.sum(yp == yt)),
            "accuracy": float(np.mean(yp == yt)) if n else np.nan,
            "recall_if_bird": float(recall_score(yt, yp, zero_division=0)) if is_bird_folder else np.nan,
            "fp_rate_if_nonbird": float(np.mean(yp == 1)) if not is_bird_folder else np.nan,
        })
    return pd.DataFrame(rows)


def infer_soft_probability_column(df: pd.DataFrame) -> str:
    candidates = [
        "p_bird", "teacher_p_bird", "soft_p_bird", "prob_bird",
        "p_bird_teacher", "binary_p_bird", "bird_probability",
    ]
    lower_to_col = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_to_col:
            return lower_to_col[cand.lower()]

    # Fallback: a numeric column containing both "bird" and "p"/"prob".
    for col in df.columns:
        lc = col.lower()
        if "bird" in lc and ("p" in lc or "prob" in lc or "soft" in lc):
            if pd.api.types.is_numeric_dtype(df[col]):
                return col

    # Last fallback: numeric column with values in [0,1] and not obviously a hard label.
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    bounded = []
    for col in numeric_cols:
        vals = df[col].dropna().astype(float)
        if len(vals) and vals.min() >= -1e-6 and vals.max() <= 1.0 + 1e-6:
            if "label" not in col.lower() and "hard" not in col.lower() and "target" not in col.lower():
                bounded.append(col)
    if len(bounded) == 1:
        return bounded[0]

    raise RuntimeError(
        "Could not infer teacher P(bird) column from soft-label CSV. "
        f"Columns found: {list(df.columns)}"
    )


def infer_soft_path_column(df: pd.DataFrame) -> str | None:
    candidates = [
        "file_path", "path", "audio_path", "rel_path", "relative_path",
        "filename", "file", "wav", "clip", "clip_path",
    ]
    lower_to_col = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_to_col:
            return lower_to_col[cand.lower()]

    for col in df.columns:
        lc = col.lower()
        if any(tok in lc for tok in ["path", "file", "wav", "clip"]):
            return col
    return None


def load_teacher_soft_labels(
    soft_csv: Path,
    rel_paths: List[str],
    n_expected: int,
) -> Tuple[np.ndarray, Dict]:
    if not soft_csv.exists():
        raise FileNotFoundError(
            f"Soft-label CSV not found: {soft_csv}\n"
            "Expected output from teacher_kd/generate_soft_labels.py"
        )

    df = pd.read_csv(soft_csv)
    prob_col = infer_soft_probability_column(df)
    path_col = infer_soft_path_column(df)

    probs = df[prob_col].astype(float).clip(0.0, 1.0).to_numpy(dtype=np.float32)

    if path_col is None:
        if len(df) != n_expected:
            raise RuntimeError(
                "Soft-label CSV has no path/filename column and length does not match dataset.\n"
                f"CSV rows={len(df)}, expected={n_expected}"
            )
        print("Soft-label CSV has no path column; using row order fallback.")
        return probs, {
            "soft_csv": str(soft_csv),
            "prob_col": prob_col,
            "path_col": None,
            "match_mode": "row_order",
            "n_soft_rows": int(len(df)),
        }

    # Match by basename. FSC22 generated names are expected to be unique.
    key_to_prob = {}
    duplicate_keys = set()
    for _, row in df.iterrows():
        raw = str(row[path_col])
        base = Path(raw).name
        if base in key_to_prob:
            duplicate_keys.add(base)
        key_to_prob[base] = float(row[prob_col])

    if duplicate_keys:
        raise RuntimeError(
            "Duplicate basenames in soft-label CSV; refusing ambiguous match. "
            f"Examples: {sorted(list(duplicate_keys))[:10]}"
        )

    matched = []
    missing = []
    for rp in rel_paths:
        base = Path(str(rp)).name
        if base not in key_to_prob:
            missing.append(rp)
            matched.append(np.nan)
        else:
            matched.append(key_to_prob[base])

    if missing:
        raise RuntimeError(
            f"Could not match {len(missing)} dataset clips to teacher soft labels. "
            f"Examples: {missing[:10]}\n"
            f"Soft CSV columns: {list(df.columns)}"
        )

    matched_arr = np.asarray(matched, dtype=np.float32)
    matched_arr = np.clip(matched_arr, 0.0, 1.0)

    return matched_arr, {
        "soft_csv": str(soft_csv),
        "prob_col": prob_col,
        "path_col": path_col,
        "match_mode": "basename",
        "n_soft_rows": int(len(df)),
        "n_matched": int(len(matched_arr)),
        "mean_teacher_p_bird": float(np.mean(matched_arr)),
    }


def kd_loss_factory(
    hard_weight: float,
    kd_weight: float,
    focal_alpha: float,
    focal_gamma: float,
):
    hard_weight = float(hard_weight)
    kd_weight = float(kd_weight)

    if hard_weight < 0 or kd_weight < 0:
        raise ValueError("hard_weight and kd_weight must be non-negative.")
    denom = hard_weight + kd_weight
    if denom <= 0:
        raise ValueError("hard_weight + kd_weight must be > 0.")

    hard_weight = hard_weight / denom
    kd_weight = kd_weight / denom

    def loss(y_true, y_pred):
        # y_true columns: [hard_label, teacher_p_bird]
        y_hard = tf.cast(y_true[:, 0:1], tf.float32)
        y_soft = tf.cast(y_true[:, 1:2], tf.float32)
        y_pred_f = tf.clip_by_value(tf.cast(y_pred, tf.float32), 1e-7, 1.0 - 1e-7)

        # Focal hard-label term.
        p_t = y_hard * y_pred_f + (1.0 - y_hard) * (1.0 - y_pred_f)
        alpha_t = y_hard * focal_alpha + (1.0 - y_hard) * (1.0 - focal_alpha)
        hard_focal = -alpha_t * tf.pow(1.0 - p_t, focal_gamma) * tf.math.log(p_t)
        hard_focal = tf.reduce_mean(hard_focal)

        # Soft teacher BCE term.
        soft_bce = tf.keras.backend.binary_crossentropy(y_soft, y_pred_f)
        soft_bce = tf.reduce_mean(soft_bce)

        return hard_weight * hard_focal + kd_weight * soft_bce

    return loss


class BalancedKDAugmentedSequence(tf.keras.utils.Sequence):
    def __init__(
        self,
        X: np.ndarray,
        y_hard: np.ndarray,
        y_soft: np.ndarray,
        batch_size: int,
        steps_per_epoch: int,
        seed: int,
        augment: bool = True,
    ):
        self.X = X
        self.y_hard = y_hard.astype(np.int32)
        self.y_soft = y_soft.astype(np.float32)
        self.batch_size = int(batch_size)
        self.steps_per_epoch = int(steps_per_epoch)
        self.augment = bool(augment)
        self.pos_idx = np.where(self.y_hard == 1)[0]
        self.neg_idx = np.where(self.y_hard == 0)[0]
        if len(self.pos_idx) == 0 or len(self.neg_idx) == 0:
            raise ValueError("Balanced sequence requires both positive and negative samples.")
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return self.steps_per_epoch

    def __getitem__(self, idx):
        n_pos = self.batch_size // 2
        n_neg = self.batch_size - n_pos

        pos = self.rng.choice(self.pos_idx, size=n_pos, replace=True)
        neg = self.rng.choice(self.neg_idx, size=n_neg, replace=True)
        inds = np.concatenate([pos, neg])
        self.rng.shuffle(inds)

        xb = []
        yb = []
        for sample_idx in inds:
            x = self.X[sample_idx]
            is_pos = bool(self.y_hard[sample_idx] == 1)
            if self.augment:
                x = v2.augment_logmel(x, self.rng, is_pos)
            xb.append(x)
            yb.append([float(self.y_hard[sample_idx]), float(self.y_soft[sample_idx])])

        xb = np.stack(xb, axis=0)[..., np.newaxis].astype(np.float32)
        yb = np.asarray(yb, dtype=np.float32)
        return xb, yb

    def on_epoch_end(self):
        pass


class HardValidationMetricsCallback(tf.keras.callbacks.Callback):
    def __init__(
        self,
        X_val: np.ndarray,
        y_val_hard: np.ndarray,
        target_fpr: float,
        batch_size: int,
    ):
        super().__init__()
        self.X_val = X_val
        self.y_val_hard = y_val_hard.astype(np.int32)
        self.target_fpr = float(target_fpr)
        self.batch_size = int(batch_size)

    def on_epoch_end(self, epoch, logs=None):
        logs = logs if logs is not None else {}
        y_prob = self.model.predict(self.X_val, batch_size=self.batch_size, verbose=0).reshape(-1)

        m05 = metrics_at_threshold(self.y_val_hard, y_prob, 0.5)
        mt = threshold_for_target_fpr(self.y_val_hard, y_prob, self.target_fpr)
        pr_auc = safe_auc(self.y_val_hard, y_prob, "pr")
        roc_auc = safe_auc(self.y_val_hard, y_prob, "roc")

        logs["val_hard_pr_auc"] = pr_auc
        logs["val_hard_roc_auc"] = roc_auc
        logs["val_hard_recall_0p5"] = m05["recall"]
        logs["val_hard_precision_0p5"] = m05["precision"]
        logs["val_hard_recall_at_fpr"] = mt["recall"]
        logs["val_hard_fpr_at_target"] = mt["fpr"]

        print(
            " - val_hard_pr_auc: "
            f"{pr_auc:.4f} - val_hard_roc_auc: {roc_auc:.4f} "
            f"- val_hard_recall_0p5: {m05['recall']:.4f} "
            f"- val_hard_precision_0p5: {m05['precision']:.4f} "
            f"- val_hard_recall_at_fpr: {mt['recall']:.4f}"
        )


def load_summary(repo_root: Path, run_name: str) -> Dict:
    p = repo_root / "student" / "results" / run_name / "metrics_summary.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def write_report(
    report_path: Path,
    cfg: v1.Config,
    args: argparse.Namespace,
    summary: Dict,
    fold_df: pd.DataFrame,
    folder_df: pd.DataFrame,
    output_dir: Path,
    baseline_v2: Dict,
) -> None:
    L = []
    A = L.append

    A("# Student 5 s Binary KD v1 Report")
    A("")
    A("Binary KD experiment. Uses Teacher P(bird) soft labels and hard labels.")
    A("")
    A("## Design")
    A("")
    A("```text")
    A("input = 5 s / 16 kHz / 40-bin log-mel")
    A("model = same compact DS-CNN v2 architecture")
    A("sampling = balanced positive/negative batches")
    A("augmentation = same feature-level augmentation as hard-label v2")
    A(f"hard loss = focal loss alpha={args.focal_alpha}, gamma={args.focal_gamma}")
    A(f"KD loss = BCE(teacher_p_bird, student_p_bird)")
    A(f"hard_weight = {args.hard_weight}")
    A(f"kd_weight = {args.kd_weight}")
    A("```")
    A("")
    A("## Teacher soft-label source")
    A("")
    A("```text")
    A(f"soft_label_csv = {args.soft_label_csv}")
    A(f"prob_col = {summary['soft_label_info'].get('prob_col')}")
    A(f"path_col = {summary['soft_label_info'].get('path_col')}")
    A(f"match_mode = {summary['soft_label_info'].get('match_mode')}")
    A("```")
    A("")
    A("## Summary")
    A("")
    A(f"- Total clips: {summary['n_clips']}")
    A(f"- Bird clips: {summary['n_bird']}")
    A(f"- Non-bird clips: {summary['n_nonbird']}")
    A(f"- Feature shape: {summary['feature_shape']}")
    A(f"- Parameter count: {summary['param_count']}")
    A(f"- Mean teacher P(bird), bird clips: {summary['teacher_mean_p_bird_true_bird']:.4f}")
    A(f"- Mean teacher P(bird), non-bird clips: {summary['teacher_mean_p_bird_true_nonbird']:.4f}")
    A(f"- Teacher binary accuracy @0.5 against hard labels: {summary['teacher_binary_acc_0p5']:.4f}")
    A("")
    A("## Cross-Validation Metrics")
    A("")
    for metric in [
        "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
        "roc_auc", "pr_auc", "recall_at_fpr_target", "fpr_at_target",
    ]:
        A(f"- {metric}: {summary[f'{metric}_mean']:.4f} ± {summary[f'{metric}_std']:.4f}")
    A("")

    if baseline_v2:
        A("## Comparison against hard-label v2")
        A("")
        A("| metric | hard-label v2 | KD v1 | delta |")
        A("|---|---:|---:|---:|")
        for metric in [
            "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
            "pr_auc", "roc_auc", "recall_at_fpr_target",
        ]:
            k = f"{metric}_mean"
            if k in baseline_v2:
                base = float(baseline_v2[k])
                kd = float(summary[k])
                A(f"| {metric} | {base:.4f} | {kd:.4f} | {kd - base:+.4f} |")
        A("")

    A("## Fold Metrics")
    A("")
    A(fold_df.to_markdown(index=False))
    A("")
    A("## Per-Folder Metrics @ Threshold 0.5")
    A("")
    show_cols = [
        "source_folder", "is_bird_folder", "n", "mean_p_bird",
        "positive_predictions", "accuracy", "recall_if_bird", "fp_rate_if_nonbird"
    ]
    A(folder_df[show_cols].to_markdown(index=False))
    A("")
    A("## Interpretation guide")
    A("")
    A("- KD is useful only if it improves PR-AUC, recall at FPR <= 2%, or false-positive behavior over hard-label v2.")
    A("- If KD does not improve, this supports the earlier hypothesis that binary soft labels are too close to hard labels.")
    A("- If KD improves mainly on `24wingflapping` or reduces rain/insect/squirrel false positives, keep it for the next stage.")
    A("")
    A("## Output Files")
    A("")
    rel = lambda p: str(Path(p).relative_to(output_dir.parent.parent))
    for name in [
        "metrics_summary.json",
        "fold_metrics.csv",
        "per_folder_metrics.csv",
        "predictions_all_folds.csv",
        "student_5s_kd_binary_v1_report.md",
    ]:
        A(f"- `{rel(output_dir / name)}`")
    A("")

    report_path.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    args = parse_args()
    cfg = v1.Config(
        epochs=args.epochs,
        batch_size=args.batch_size,
        patience=args.patience,
        seed=args.seed,
        target_fpr=args.target_fpr,
    )

    repo_root = Path(args.repo_root).resolve()
    dataset_root = repo_root / "Dataset" / "fsc22"
    soft_csv = (repo_root / args.soft_label_csv).resolve()
    output_dir = repo_root / "student" / "results" / RUN_NAME
    cache_dir = repo_root / "student" / "cache"
    model_dir = output_dir / "models"
    fold_dir = output_dir / "folds"

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    fold_dir.mkdir(parents=True, exist_ok=True)

    set_determinism(cfg.seed, cpu_only=args.cpu_only)

    print("=" * 70)
    print("STUDENT 5S BINARY KD V1")
    print("=" * 70)
    print(f"Repo root    : {repo_root}")
    print(f"Dataset root : {dataset_root}")
    print(f"Soft labels  : {soft_csv}")
    print(f"Output dir   : {output_dir}")
    print(f"TensorFlow   : {tf.__version__}")
    print(f"KD weights   : hard={args.hard_weight}, kd={args.kd_weight}")
    print("=" * 70)

    df = v1.collect_dataset(dataset_root)
    print(f"Total clips: {len(df)} | bird={int(df.binary_hard_label.sum())} | nonbird={int((df.binary_hard_label == 0).sum())}")

    cache_path = cache_dir / f"fsc22_logmel_{int(cfg.duration_s)}s_{cfg.sample_rate}hz_{cfg.n_mels}mel_{int(cfg.hop_ms)}ms.npz"
    X, y_hard, rel_paths, folders = v1.load_or_build_cache(df, cache_path, cfg, args.force_cache)

    y_soft, soft_info = load_teacher_soft_labels(soft_csv, rel_paths, n_expected=len(y_hard))

    teacher_pred = (y_soft >= 0.5).astype(np.int32)
    teacher_binary_acc = float(np.mean(teacher_pred == y_hard))
    print("Teacher soft-label summary:")
    print(json.dumps({
        "soft_info": soft_info,
        "teacher_mean_p_bird_true_bird": float(np.mean(y_soft[y_hard == 1])),
        "teacher_mean_p_bird_true_nonbird": float(np.mean(y_soft[y_hard == 0])),
        "teacher_binary_acc_0p5": teacher_binary_acc,
    }, indent=2))

    manifest = pd.DataFrame({
        "file_path": rel_paths,
        "source_folder": folders,
        "binary_hard_label": y_hard,
        "teacher_p_bird": y_soft,
    })
    manifest.to_csv(output_dir / "manifest_with_soft_labels.csv", index=False)

    print(f"Feature tensor: {X.shape} dtype={X.dtype}")
    input_shape = (X.shape[1], X.shape[2], 1)
    probe_model = v2.build_model_v2(input_shape, cfg.learning_rate, args.focal_alpha, args.focal_gamma)
    param_count = int(probe_model.count_params())
    print(f"Model input shape: {input_shape}")
    print(f"Parameter count: {param_count}")
    del probe_model
    tf.keras.backend.clear_session()

    stratify_labels = np.array(folders)
    skf = StratifiedKFold(n_splits=cfg.n_splits, shuffle=True, random_state=cfg.seed)

    fold_rows = []
    pred_rows = []
    folder_metric_dfs = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, stratify_labels)):
        print("")
        print("=" * 70)
        print(f"Fold {fold + 1}/{cfg.n_splits}")
        print("=" * 70)

        tf.keras.backend.clear_session()
        set_determinism(cfg.seed + fold, cpu_only=args.cpu_only)

        X_train_raw = X[train_idx]
        X_val_raw = X[val_idx]
        yh_train = y_hard[train_idx]
        yh_val = y_hard[val_idx]
        ys_train = y_soft[train_idx]
        ys_val = y_soft[val_idx]

        X_train, X_val, norm = v1.normalize_fold(X_train_raw, X_val_raw)

        n_pos = int(np.sum(yh_train == 1))
        n_neg = int(np.sum(yh_train == 0))

        auto_steps = int(math.ceil((2 * n_neg) / cfg.batch_size))
        steps_per_epoch = args.steps_per_epoch if args.steps_per_epoch > 0 else auto_steps

        print(f"Train: {len(train_idx)} clips | pos={n_pos} neg={n_neg}")
        print(f"Val  : {len(val_idx)} clips | pos={int(np.sum(yh_val == 1))} neg={int(np.sum(yh_val == 0))}")
        print(f"Balanced steps/epoch: {steps_per_epoch}")

        train_seq = BalancedKDAugmentedSequence(
            X_train,
            yh_train,
            ys_train,
            batch_size=cfg.batch_size,
            steps_per_epoch=steps_per_epoch,
            seed=cfg.seed + 2000 + fold,
            augment=True,
        )

        X_val_in = X_val[..., np.newaxis].astype(np.float32)
        y_val_target = np.stack([yh_val.astype(np.float32), ys_val.astype(np.float32)], axis=1)

        model = v2.build_model_v2(input_shape, cfg.learning_rate, args.focal_alpha, args.focal_gamma)
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=cfg.learning_rate),
            loss=kd_loss_factory(
                hard_weight=args.hard_weight,
                kd_weight=args.kd_weight,
                focal_alpha=args.focal_alpha,
                focal_gamma=args.focal_gamma,
            ),
        )

        fold_weights_path = model_dir / f"student_5s_kd_binary_v1_fold{fold}.weights.h5"
        hard_metrics_cb = HardValidationMetricsCallback(
            X_val_in,
            yh_val,
            target_fpr=cfg.target_fpr,
            batch_size=cfg.batch_size,
        )

        callbacks = [
            hard_metrics_cb,
            tf.keras.callbacks.EarlyStopping(
                monitor="val_hard_pr_auc",
                mode="max",
                patience=cfg.patience,
                restore_best_weights=True,
                verbose=1,
            ),
            tf.keras.callbacks.ModelCheckpoint(
                filepath=str(fold_weights_path),
                monitor="val_hard_pr_auc",
                mode="max",
                save_best_only=True,
                save_weights_only=True,
                verbose=0,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_hard_pr_auc",
                mode="max",
                factor=0.5,
                patience=max(4, cfg.patience // 3),
                min_lr=1e-5,
                verbose=1,
            ),
        ]

        hist = model.fit(
            train_seq,
            validation_data=(X_val_in, y_val_target),
            epochs=cfg.epochs,
            callbacks=callbacks,
            verbose=2,
        )

        hist_df = pd.DataFrame(hist.history)
        hist_df.to_csv(fold_dir / f"history_kd_binary_v1_fold{fold}.csv", index=False)

        y_prob = model.predict(X_val_in, batch_size=cfg.batch_size, verbose=0).reshape(-1)
        m05 = metrics_at_threshold(yh_val, y_prob, 0.5)
        mt = threshold_for_target_fpr(yh_val, y_prob, cfg.target_fpr)
        roc_auc = safe_auc(yh_val, y_prob, "roc")
        pr_auc = safe_auc(yh_val, y_prob, "pr")

        fold_row = {
            "fold": fold,
            "n_train": int(len(train_idx)),
            "n_val": int(len(val_idx)),
            "train_pos": n_pos,
            "train_neg": n_neg,
            "val_pos": int(np.sum(yh_val == 1)),
            "val_neg": int(np.sum(yh_val == 0)),
            "steps_per_epoch": steps_per_epoch,
            "epochs_ran": int(len(hist_df)),
            "best_val_hard_pr_auc": float(np.max(hist_df["val_hard_pr_auc"])) if "val_hard_pr_auc" in hist_df else float("nan"),
            "accuracy_0p5": m05["accuracy"],
            "precision_0p5": m05["precision"],
            "recall_0p5": m05["recall"],
            "f1_0p5": m05["f1"],
            "tp_0p5": m05["tp"],
            "fn_0p5": m05["fn"],
            "fp_0p5": m05["fp"],
            "tn_0p5": m05["tn"],
            "roc_auc": roc_auc,
            "pr_auc": pr_auc,
            "target_fpr": cfg.target_fpr,
            "threshold_at_fpr_target": mt["threshold"],
            "recall_at_fpr_target": mt["recall"],
            "precision_at_fpr_target": mt["precision"],
            "fpr_at_target": mt["fpr"],
            "normalizer_mean": norm["mean"],
            "normalizer_std": norm["std"],
            "weights_path": str(fold_weights_path.relative_to(repo_root)),
            "loss": f"hard_focal*{args.hard_weight}+soft_bce*{args.kd_weight}",
        }
        fold_rows.append(fold_row)

        print("Fold metrics @0.5:")
        print(json.dumps({k: fold_row[k] for k in ["accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5", "roc_auc", "pr_auc"]}, indent=2))
        print("Fold metrics @target FPR:")
        print(json.dumps({k: fold_row[k] for k in ["threshold_at_fpr_target", "recall_at_fpr_target", "precision_at_fpr_target", "fpr_at_target"]}, indent=2))

        val_folders = [folders[i] for i in val_idx]
        val_rel_paths = [rel_paths[i] for i in val_idx]
        y_pred_05 = (y_prob >= 0.5).astype(np.int32)
        for j, idx in enumerate(val_idx):
            pred_rows.append({
                "fold": fold,
                "file_path": val_rel_paths[j],
                "source_folder": val_folders[j],
                "binary_hard_label": int(yh_val[j]),
                "teacher_p_bird": float(ys_val[j]),
                "student_p_bird": float(y_prob[j]),
                "pred_0p5": int(y_pred_05[j]),
                "correct_0p5": int(y_pred_05[j] == yh_val[j]),
            })

        pf = per_folder_metrics(val_folders, yh_val, y_prob, 0.5)
        pf.insert(0, "fold", fold)
        folder_metric_dfs.append(pf)

        with open(fold_dir / f"normalizer_kd_binary_v1_fold{fold}.json", "w", encoding="utf-8") as fh:
            json.dump(norm, fh, indent=2)

    fold_df = pd.DataFrame(fold_rows)
    pred_df = pd.DataFrame(pred_rows)
    folder_df = pd.concat(folder_metric_dfs, ignore_index=True)

    oof_folder_df = per_folder_metrics(
        pred_df["source_folder"].tolist(),
        pred_df["binary_hard_label"].to_numpy(dtype=np.int32),
        pred_df["student_p_bird"].to_numpy(dtype=np.float32),
        0.5,
    )

    fold_df.to_csv(output_dir / "fold_metrics.csv", index=False)
    pred_df.to_csv(output_dir / "predictions_all_folds.csv", index=False)
    folder_df.to_csv(output_dir / "per_folder_metrics_by_fold.csv", index=False)
    oof_folder_df.to_csv(output_dir / "per_folder_metrics.csv", index=False)

    summary = {
        "run_name": RUN_NAME,
        "decision_context": "5 s binary KD v1 compared against hard-label v2",
        "n_clips": int(len(df)),
        "n_bird": int(np.sum(y_hard == 1)),
        "n_nonbird": int(np.sum(y_hard == 0)),
        "param_count": param_count,
        "config": asdict(cfg),
        "hard_weight": float(args.hard_weight),
        "kd_weight": float(args.kd_weight),
        "focal_alpha": float(args.focal_alpha),
        "focal_gamma": float(args.focal_gamma),
        "feature_shape": list(X.shape[1:]),
        "input_shape": list(input_shape),
        "tensorflow_version": tf.__version__,
        "output_dir": str(output_dir.relative_to(repo_root)),
        "soft_label_info": soft_info,
        "teacher_mean_p_bird_true_bird": float(np.mean(y_soft[y_hard == 1])),
        "teacher_mean_p_bird_true_nonbird": float(np.mean(y_soft[y_hard == 0])),
        "teacher_binary_acc_0p5": teacher_binary_acc,
    }

    for key in [
        "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
        "roc_auc", "pr_auc", "recall_at_fpr_target",
        "precision_at_fpr_target", "fpr_at_target",
    ]:
        summary[f"{key}_mean"] = float(fold_df[key].mean())
        summary[f"{key}_std"] = float(fold_df[key].std(ddof=0))

    y_oof = pred_df["binary_hard_label"].to_numpy(dtype=np.int32)
    p_oof = pred_df["student_p_bird"].to_numpy(dtype=np.float32)
    summary["oof_metrics_0p5"] = metrics_at_threshold(y_oof, p_oof, 0.5)
    summary["oof_metrics_target_fpr"] = threshold_for_target_fpr(y_oof, p_oof, cfg.target_fpr)
    summary["oof_roc_auc"] = safe_auc(y_oof, p_oof, "roc")
    summary["oof_pr_auc"] = safe_auc(y_oof, p_oof, "pr")

    baseline_v2 = load_summary(repo_root, "5s_hardlabel_baseline_v2")
    if baseline_v2:
        summary["hardlabel_v2_comparison"] = {}
        for metric in [
            "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
            "roc_auc", "pr_auc", "recall_at_fpr_target",
        ]:
            k = f"{metric}_mean"
            if k in baseline_v2:
                summary["hardlabel_v2_comparison"][metric] = {
                    "hardlabel_v2": float(baseline_v2[k]),
                    "kd_v1": float(summary[k]),
                    "delta": float(summary[k] - baseline_v2[k]),
                }

    with open(output_dir / "metrics_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    write_report(
        output_dir / "student_5s_kd_binary_v1_report.md",
        cfg,
        args,
        summary,
        fold_df,
        oof_folder_df,
        output_dir,
        baseline_v2,
    )

    print("")
    print("=" * 70)
    print("STUDENT 5S BINARY KD V1 - SUMMARY")
    print("=" * 70)
    print(f"Feature shape          : {X.shape[1:]}")
    print(f"Model parameters       : {param_count}")
    print(f"Clips                  : {summary['n_clips']}  (bird={summary['n_bird']}, non-bird={summary['n_nonbird']})")
    print(f"CV accuracy @0.5       : {summary['accuracy_0p5_mean']:.4f} ± {summary['accuracy_0p5_std']:.4f}")
    print(f"CV bird recall @0.5    : {summary['recall_0p5_mean']:.4f} ± {summary['recall_0p5_std']:.4f}")
    print(f"CV bird precision @0.5 : {summary['precision_0p5_mean']:.4f} ± {summary['precision_0p5_std']:.4f}")
    print(f"CV PR-AUC              : {summary['pr_auc_mean']:.4f} ± {summary['pr_auc_std']:.4f}")
    print(f"CV ROC-AUC             : {summary['roc_auc_mean']:.4f} ± {summary['roc_auc_std']:.4f}")
    print(f"Recall @FPR<={cfg.target_fpr:.2f} : {summary['recall_at_fpr_target_mean']:.4f} ± {summary['recall_at_fpr_target_std']:.4f}")

    if baseline_v2:
        print("Delta vs hard-label v2:")
        for metric, vals in summary["hardlabel_v2_comparison"].items():
            print(f"  {metric}: {vals['delta']:+.4f}")

    print("Output files:")
    for name in [
        "metrics_summary.json",
        "fold_metrics.csv",
        "per_folder_metrics.csv",
        "predictions_all_folds.csv",
        "student_5s_kd_binary_v1_report.md",
    ]:
        print(f"  - {output_dir.relative_to(repo_root) / name}")
    print("=" * 70)


if __name__ == "__main__":
    main()


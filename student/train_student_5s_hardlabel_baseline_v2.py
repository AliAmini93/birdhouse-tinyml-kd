#!/usr/bin/env python3
# ==============================================================================
# train_student_5s_hardlabel_baseline_v2.py
# ------------------------------------------------------------------------------
# 5-second hard-label baseline Student v2.
#
# Compared to v1:
# - Still 5 s / 16 kHz / 40-bin log-mel / binary hard labels.
# - Uses a slightly wider compact DS-CNN.
# - Uses balanced batches with positive oversampling.
# - Uses feature-level augmentation.
# - Uses focal loss.
#
# Purpose:
#   Improve hard-label baseline before testing KD.
#
# Run:
#   cd /media/armin/External/AhmadWorks/audioclassification
#   mkdir -p student/results/5s_hardlabel_baseline_v2
#   "/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3" \
#     student/train_student_5s_hardlabel_baseline_v2.py \
#     2>&1 | tee student/results/5s_hardlabel_baseline_v2/train_console.log
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

# Import v1 utilities instead of duplicating feature extraction / metrics logic.
REPO_ROOT_GUESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT_GUESS / "student"))

import train_student_5s_hardlabel_baseline as v1  # noqa: E402


RUN_NAME = "5s_hardlabel_baseline_v2"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train 5 s hard-label Student baseline v2.")
    p.add_argument("--repo-root", default=".", help="Repository root.")
    p.add_argument("--epochs", type=int, default=90)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--patience", type=int, default=14)
    p.add_argument("--seed", type=int, default=43)
    p.add_argument("--force-cache", action="store_true")
    p.add_argument("--cpu-only", action="store_true")
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


def binary_focal_loss(alpha: float = 0.75, gamma: float = 2.0):
    def loss(y_true, y_pred):
        y_true_f = tf.cast(y_true, tf.float32)
        y_pred_f = tf.clip_by_value(tf.cast(y_pred, tf.float32), 1e-7, 1.0 - 1e-7)
        p_t = y_true_f * y_pred_f + (1.0 - y_true_f) * (1.0 - y_pred_f)
        alpha_t = y_true_f * alpha + (1.0 - y_true_f) * (1.0 - alpha)
        focal = tf.pow(1.0 - p_t, gamma)
        return tf.reduce_mean(-alpha_t * focal * tf.math.log(p_t))
    return loss


def ds_block(x, pointwise_filters: int, stride: Tuple[int, int] = (1, 1), name: str = "ds"):
    x = tf.keras.layers.DepthwiseConv2D(
        kernel_size=(3, 3),
        strides=stride,
        padding="same",
        use_bias=False,
        name=f"{name}_dw",
    )(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_dw_bn")(x)
    x = tf.keras.layers.ReLU(max_value=6.0, name=f"{name}_dw_relu6")(x)

    x = tf.keras.layers.Conv2D(
        filters=pointwise_filters,
        kernel_size=(1, 1),
        padding="same",
        use_bias=False,
        name=f"{name}_pw",
    )(x)
    x = tf.keras.layers.BatchNormalization(name=f"{name}_pw_bn")(x)
    x = tf.keras.layers.ReLU(max_value=6.0, name=f"{name}_pw_relu6")(x)
    return x


def build_model_v2(input_shape: Tuple[int, int, int], learning_rate: float,
                   focal_alpha: float, focal_gamma: float) -> tf.keras.Model:
    inp = tf.keras.Input(shape=input_shape, name="logmel")

    x = tf.keras.layers.Conv2D(24, (3, 3), strides=(2, 2), padding="same", use_bias=False, name="stem_conv")(inp)
    x = tf.keras.layers.BatchNormalization(name="stem_bn")(x)
    x = tf.keras.layers.ReLU(max_value=6.0, name="stem_relu6")(x)

    x = ds_block(x, 32, stride=(1, 1), name="block1")
    x = ds_block(x, 48, stride=(2, 2), name="block2")
    x = ds_block(x, 64, stride=(1, 1), name="block3")
    x = ds_block(x, 96, stride=(2, 2), name="block4")
    x = ds_block(x, 96, stride=(1, 1), name="block5")

    x = tf.keras.layers.GlobalAveragePooling2D(name="gap")(x)
    x = tf.keras.layers.Dense(64, activation="relu", name="dense64")(x)
    x = tf.keras.layers.Dropout(0.25, name="dropout")(x)
    out = tf.keras.layers.Dense(1, activation="sigmoid", name="p_bird")(x)

    model = tf.keras.Model(inp, out, name="student_5s_logmel_dscnn_v2")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=binary_focal_loss(alpha=focal_alpha, gamma=focal_gamma),
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name="bin_acc", threshold=0.5),
            tf.keras.metrics.AUC(name="roc_auc", curve="ROC"),
            tf.keras.metrics.AUC(name="pr_auc", curve="PR"),
            tf.keras.metrics.Precision(name="precision", thresholds=0.5),
            tf.keras.metrics.Recall(name="recall", thresholds=0.5),
        ],
    )
    return model


def augment_logmel(x: np.ndarray, rng: np.random.Generator, is_positive: bool) -> np.ndarray:
    # x shape: (mels, frames), already normalized.
    y = np.array(x, copy=True)

    # Time shift. More useful for bird positives but applied to all classes.
    if rng.random() < (0.90 if is_positive else 0.50):
        max_shift = max(1, int(0.08 * y.shape[1]))
        shift = int(rng.integers(-max_shift, max_shift + 1))
        if shift > 0:
            y[:, shift:] = y[:, :-shift]
            y[:, :shift] = 0.0
        elif shift < 0:
            s = -shift
            y[:, :-s] = y[:, s:]
            y[:, -s:] = 0.0

    # Log-energy gain jitter: adding a scalar in normalized log-mel space.
    if rng.random() < 0.85:
        y += rng.normal(0.0, 0.10 if is_positive else 0.06)

    # Small Gaussian feature noise.
    if rng.random() < 0.70:
        y += rng.normal(0.0, 0.025 if is_positive else 0.015, size=y.shape).astype(np.float32)

    # Time masking.
    if rng.random() < (0.75 if is_positive else 0.35):
        max_w = max(1, int(0.10 * y.shape[1]))
        w = int(rng.integers(1, max_w + 1))
        t0 = int(rng.integers(0, max(1, y.shape[1] - w + 1)))
        y[:, t0:t0 + w] = np.mean(y)

    # Frequency masking.
    if rng.random() < (0.55 if is_positive else 0.25):
        max_w = max(1, int(0.15 * y.shape[0]))
        w = int(rng.integers(1, max_w + 1))
        f0 = int(rng.integers(0, max(1, y.shape[0] - w + 1)))
        y[f0:f0 + w, :] = np.mean(y)

    return y.astype(np.float32)


class BalancedAugmentedSequence(tf.keras.utils.Sequence):
    def __init__(
        self,
        X: np.ndarray,
        y: np.ndarray,
        batch_size: int,
        steps_per_epoch: int,
        seed: int,
        augment: bool = True,
    ):
        self.X = X
        self.y = y.astype(np.int32)
        self.batch_size = int(batch_size)
        self.steps_per_epoch = int(steps_per_epoch)
        self.augment = bool(augment)
        self.pos_idx = np.where(self.y == 1)[0]
        self.neg_idx = np.where(self.y == 0)[0]
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
        yb = self.y[inds].astype(np.float32)
        for sample_idx in inds:
            x = self.X[sample_idx]
            if self.augment:
                x = augment_logmel(x, self.rng, bool(self.y[sample_idx] == 1))
            xb.append(x)

        xb = np.stack(xb, axis=0)[..., np.newaxis].astype(np.float32)
        return xb, yb

    def on_epoch_end(self):
        pass


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


def load_v1_summary(repo_root: Path) -> Dict:
    p = repo_root / "student" / "results" / "5s_hardlabel_baseline" / "metrics_summary.json"
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
    v1_summary: Dict,
) -> None:
    L = []
    A = L.append

    A("# Student 5 s Hard-Label Baseline v2 Report")
    A("")
    A("Hard-label baseline v2. No Teacher/KD loss used in training.")
    A("")
    A("## What changed from v1")
    A("")
    A("```text")
    A("same 5 s / 16 kHz / 40-bin log-mel input")
    A("slightly wider compact DS-CNN")
    A("balanced batches with positive oversampling")
    A("feature-level augmentation")
    A(f"focal loss: alpha={args.focal_alpha}, gamma={args.focal_gamma}")
    A("```")
    A("")
    A("## Summary")
    A("")
    A(f"- Total clips: {summary['n_clips']}")
    A(f"- Bird clips: {summary['n_bird']}")
    A(f"- Non-bird clips: {summary['n_nonbird']}")
    A(f"- Feature shape: {summary['feature_shape']}")
    A(f"- Parameter count: {summary['param_count']}")
    A("")
    A("## Cross-Validation Metrics")
    A("")
    for metric in [
        "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
        "roc_auc", "pr_auc", "recall_at_fpr_target", "fpr_at_target",
    ]:
        A(f"- {metric}: {summary[f'{metric}_mean']:.4f} ± {summary[f'{metric}_std']:.4f}")
    A("")

    if v1_summary:
        A("## Comparison against v1")
        A("")
        A("| metric | v1 mean | v2 mean | delta |")
        A("|---|---:|---:|---:|")
        for metric in [
            "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
            "pr_auc", "roc_auc", "recall_at_fpr_target",
        ]:
            v1_key = f"{metric}_mean"
            if v1_key in v1_summary:
                v1v = float(v1_summary[v1_key])
                v2v = float(summary[v1_key])
                A(f"| {metric} | {v1v:.4f} | {v2v:.4f} | {v2v - v1v:+.4f} |")
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
    A("## Interpretation")
    A("")
    A("- v2 should primarily improve bird recall, especially `24wingflapping`.")
    A("- If v2 improves recall but creates too many false positives, threshold tuning or focal parameters should be adjusted.")
    A("- If v2 still misses many wingflapping clips, the next hard-label iteration should focus on feature resolution or targeted augmentation before KD.")
    A("- KD should only be tested after this hard-label baseline is understood.")
    A("")
    A("## Output Files")
    A("")
    rel = lambda p: str(Path(p).relative_to(output_dir.parent.parent))
    for name in [
        "metrics_summary.json",
        "fold_metrics.csv",
        "per_folder_metrics.csv",
        "predictions_all_folds.csv",
        "student_5s_hardlabel_baseline_v2_report.md",
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
    print("STUDENT 5S HARD-LABEL BASELINE V2")
    print("=" * 70)
    print(f"Repo root    : {repo_root}")
    print(f"Dataset root : {dataset_root}")
    print(f"Output dir   : {output_dir}")
    print(f"TensorFlow   : {tf.__version__}")
    print(f"V2 changes   : balanced batches + augmentation + focal loss")
    print("=" * 70)

    df = v1.collect_dataset(dataset_root)
    print(f"Total clips: {len(df)} | bird={int(df.binary_hard_label.sum())} | nonbird={int((df.binary_hard_label == 0).sum())}")

    manifest_path = output_dir / "manifest.csv"
    df.assign(file_path=df["file_path"].map(lambda p: str(Path(p).relative_to(repo_root)))).to_csv(manifest_path, index=False)

    cache_path = cache_dir / f"fsc22_logmel_{int(cfg.duration_s)}s_{cfg.sample_rate}hz_{cfg.n_mels}mel_{int(cfg.hop_ms)}ms.npz"
    X, y, rel_paths, folders = v1.load_or_build_cache(df, cache_path, cfg, args.force_cache)

    print(f"Feature tensor: {X.shape} dtype={X.dtype}")
    input_shape = (X.shape[1], X.shape[2], 1)
    probe_model = build_model_v2(input_shape, cfg.learning_rate, args.focal_alpha, args.focal_gamma)
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
        y_train = y[train_idx]
        y_val = y[val_idx]

        X_train, X_val, norm = v1.normalize_fold(X_train_raw, X_val_raw)

        n_pos = int(np.sum(y_train == 1))
        n_neg = int(np.sum(y_train == 0))

        auto_steps = int(math.ceil((2 * n_neg) / cfg.batch_size))
        steps_per_epoch = args.steps_per_epoch if args.steps_per_epoch > 0 else auto_steps

        print(f"Train: {len(train_idx)} clips | pos={n_pos} neg={n_neg}")
        print(f"Val  : {len(val_idx)} clips | pos={int(np.sum(y_val == 1))} neg={int(np.sum(y_val == 0))}")
        print(f"Balanced steps/epoch: {steps_per_epoch}")

        train_seq = BalancedAugmentedSequence(
            X_train,
            y_train,
            batch_size=cfg.batch_size,
            steps_per_epoch=steps_per_epoch,
            seed=cfg.seed + 1000 + fold,
            augment=True,
        )

        X_val_in = X_val[..., np.newaxis].astype(np.float32)

        model = build_model_v2(input_shape, cfg.learning_rate, args.focal_alpha, args.focal_gamma)

        fold_model_path = model_dir / f"student_5s_hardlabel_v2_fold{fold}.keras"
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_pr_auc",
                mode="max",
                patience=cfg.patience,
                restore_best_weights=True,
                verbose=1,
            ),
            tf.keras.callbacks.ModelCheckpoint(
                filepath=str(fold_model_path),
                monitor="val_pr_auc",
                mode="max",
                save_best_only=True,
                verbose=0,
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_pr_auc",
                mode="max",
                factor=0.5,
                patience=max(4, cfg.patience // 3),
                min_lr=1e-5,
                verbose=1,
            ),
        ]

        hist = model.fit(
            train_seq,
            validation_data=(X_val_in, y_val),
            epochs=cfg.epochs,
            callbacks=callbacks,
            verbose=2,
        )

        hist_df = pd.DataFrame(hist.history)
        hist_df.to_csv(fold_dir / f"history_v2_fold{fold}.csv", index=False)

        y_prob = model.predict(X_val_in, batch_size=cfg.batch_size, verbose=0).reshape(-1)
        m05 = metrics_at_threshold(y_val, y_prob, 0.5)
        mt = threshold_for_target_fpr(y_val, y_prob, cfg.target_fpr)
        roc_auc = safe_auc(y_val, y_prob, "roc")
        pr_auc = safe_auc(y_val, y_prob, "pr")

        fold_row = {
            "fold": fold,
            "n_train": int(len(train_idx)),
            "n_val": int(len(val_idx)),
            "train_pos": n_pos,
            "train_neg": n_neg,
            "val_pos": int(np.sum(y_val == 1)),
            "val_neg": int(np.sum(y_val == 0)),
            "steps_per_epoch": steps_per_epoch,
            "epochs_ran": int(len(hist_df)),
            "best_val_pr_auc": float(np.max(hist_df["val_pr_auc"])) if "val_pr_auc" in hist_df else float("nan"),
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
            "model_path": str(fold_model_path.relative_to(repo_root)),
            "loss": f"focal(alpha={args.focal_alpha}, gamma={args.focal_gamma})",
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
                "binary_hard_label": int(y_val[j]),
                "p_bird": float(y_prob[j]),
                "pred_0p5": int(y_pred_05[j]),
                "correct_0p5": int(y_pred_05[j] == y_val[j]),
            })

        pf = per_folder_metrics(val_folders, y_val, y_prob, 0.5)
        pf.insert(0, "fold", fold)
        folder_metric_dfs.append(pf)

        with open(fold_dir / f"normalizer_v2_fold{fold}.json", "w", encoding="utf-8") as fh:
            json.dump(norm, fh, indent=2)

    fold_df = pd.DataFrame(fold_rows)
    pred_df = pd.DataFrame(pred_rows)
    folder_df = pd.concat(folder_metric_dfs, ignore_index=True)

    oof_folder_df = per_folder_metrics(
        pred_df["source_folder"].tolist(),
        pred_df["binary_hard_label"].to_numpy(dtype=np.int32),
        pred_df["p_bird"].to_numpy(dtype=np.float32),
        0.5,
    )

    fold_df.to_csv(output_dir / "fold_metrics.csv", index=False)
    pred_df.to_csv(output_dir / "predictions_all_folds.csv", index=False)
    folder_df.to_csv(output_dir / "per_folder_metrics_by_fold.csv", index=False)
    oof_folder_df.to_csv(output_dir / "per_folder_metrics.csv", index=False)

    summary = {
        "run_name": RUN_NAME,
        "decision_context": "5 s hard-label baseline v2 before KD",
        "v2_changes": [
            "balanced positive/negative batches",
            "feature-level augmentation",
            "binary focal loss",
            "slightly wider compact DS-CNN",
        ],
        "n_clips": int(len(df)),
        "n_bird": int(np.sum(y == 1)),
        "n_nonbird": int(np.sum(y == 0)),
        "param_count": param_count,
        "config": asdict(cfg),
        "focal_alpha": float(args.focal_alpha),
        "focal_gamma": float(args.focal_gamma),
        "feature_shape": list(X.shape[1:]),
        "input_shape": list(input_shape),
        "tensorflow_version": tf.__version__,
        "output_dir": str(output_dir.relative_to(repo_root)),
    }

    for key in [
        "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
        "roc_auc", "pr_auc", "recall_at_fpr_target",
        "precision_at_fpr_target", "fpr_at_target",
    ]:
        summary[f"{key}_mean"] = float(fold_df[key].mean())
        summary[f"{key}_std"] = float(fold_df[key].std(ddof=0))

    y_oof = pred_df["binary_hard_label"].to_numpy(dtype=np.int32)
    p_oof = pred_df["p_bird"].to_numpy(dtype=np.float32)
    summary["oof_metrics_0p5"] = metrics_at_threshold(y_oof, p_oof, 0.5)
    summary["oof_metrics_target_fpr"] = threshold_for_target_fpr(y_oof, p_oof, cfg.target_fpr)
    summary["oof_roc_auc"] = safe_auc(y_oof, p_oof, "roc")
    summary["oof_pr_auc"] = safe_auc(y_oof, p_oof, "pr")

    v1_summary = load_v1_summary(repo_root)
    if v1_summary:
        summary["v1_comparison"] = {}
        for metric in [
            "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
            "roc_auc", "pr_auc", "recall_at_fpr_target",
        ]:
            k = f"{metric}_mean"
            if k in v1_summary:
                summary["v1_comparison"][metric] = {
                    "v1": float(v1_summary[k]),
                    "v2": float(summary[k]),
                    "delta": float(summary[k] - v1_summary[k]),
                }

    with open(output_dir / "metrics_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    write_report(
        output_dir / "student_5s_hardlabel_baseline_v2_report.md",
        cfg,
        args,
        summary,
        fold_df,
        oof_folder_df,
        output_dir,
        v1_summary,
    )

    print("")
    print("=" * 70)
    print("STUDENT 5S HARD-LABEL BASELINE V2 - SUMMARY")
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
    if v1_summary:
        print("Delta vs v1:")
        for metric, vals in summary["v1_comparison"].items():
            print(f"  {metric}: {vals['delta']:+.4f}")
    print("Output files:")
    for name in [
        "metrics_summary.json",
        "fold_metrics.csv",
        "per_folder_metrics.csv",
        "predictions_all_folds.csv",
        "student_5s_hardlabel_baseline_v2_report.md",
    ]:
        print(f"  - {output_dir.relative_to(repo_root) / name}")
    print("=" * 70)


if __name__ == "__main__":
    main()


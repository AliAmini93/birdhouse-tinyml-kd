#!/usr/bin/env python3
# ==============================================================================
# train_student_5s_hardlabel_baseline.py
# ------------------------------------------------------------------------------
# 5-second hard-label baseline Student for Birdhouse TinyML KD.
#
# This script:
# - Does NOT train or modify the Teacher.
# - Does NOT modify Dataset/, Codes/, output_*/ or venv/.
# - Trains a binary 5 s Student using hard labels only.
# - Uses TensorFlow/Keras to keep the deployment path close to TFLite Micro.
#
# Target Student v1:
#   5 s, 16 kHz mono, 40-bin log-mel, compact DS-CNN, binary bird/non-bird.
#
# Run:
#   cd /media/armin/External/AhmadWorks/audioclassification
#   "/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3" \
#     student/train_student_5s_hardlabel_baseline.py \
#     2>&1 | tee student/results/5s_hardlabel_baseline/train_console.log
# ==============================================================================

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

# Keep TensorFlow logs less noisy.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")

REQUIRED_PACKAGES = [
    "numpy", "pandas", "librosa", "sklearn", "tensorflow"
]


def check_environment() -> None:
    problems = {}
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except Exception as exc:
            problems[pkg] = f"{type(exc).__name__}: {exc}"

    if problems:
        print("=" * 70)
        print("ENVIRONMENT CHECK FAILED")
        print("Missing or unimportable packages:")
        for pkg, msg in problems.items():
            print(f"  [FAIL] {pkg:12s} -> {msg}")
        print("=" * 70)
        sys.exit(1)


check_environment()

import librosa
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


BIRD_FOLDERS = {"23birdchirping", "24wingflapping"}
RUN_NAME = "5s_hardlabel_baseline"


@dataclass
class Config:
    sample_rate: int = 16000
    duration_s: float = 5.0
    n_mels: int = 40
    frame_ms: float = 25.0
    hop_ms: float = 20.0
    n_fft: int = 512
    fmin: float = 50.0
    fmax: float = 8000.0
    eps: float = 1e-6
    batch_size: int = 32
    epochs: int = 80
    patience: int = 12
    learning_rate: float = 1e-3
    n_splits: int = 5
    seed: int = 42
    threshold_default: float = 0.5
    target_fpr: float = 0.02


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train 5 s hard-label Student baseline.")
    p.add_argument("--repo-root", default=".", help="Repository root.")
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--patience", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--force-cache", action="store_true",
                   help="Recompute log-mel cache even if it exists.")
    p.add_argument("--cpu-only", action="store_true",
                   help="Disable GPU visibility for TensorFlow.")
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


def collect_dataset(dataset_root: Path) -> pd.DataFrame:
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"Dataset root not found: {dataset_root}")

    audio_exts = {".wav", ".flac", ".mp3", ".ogg"}
    rows = []
    folders = sorted([p for p in dataset_root.iterdir() if p.is_dir()])
    for class_index, folder_path in enumerate(folders):
        folder = folder_path.name
        files = sorted([
            p for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() in audio_exts
        ])
        for p in files:
            y = 1 if folder in BIRD_FOLDERS else 0
            rows.append({
                "file_path": str(p),
                "rel_path": str(p.relative_to(dataset_root.parent.parent)),
                "source_folder": folder,
                "folder_index_sorted": class_index,
                "binary_hard_label": y,
                "is_true_bird": bool(y),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f"No audio files found under {dataset_root}")

    return df


def expected_frames(cfg: Config) -> int:
    target_samples = int(round(cfg.sample_rate * cfg.duration_s))
    hop_length = int(round(cfg.sample_rate * cfg.hop_ms / 1000.0))
    # center=False in librosa, n_fft=512.
    return 1 + max(0, (target_samples - cfg.n_fft) // hop_length)


def fix_audio_length(y: np.ndarray, target_samples: int) -> np.ndarray:
    if len(y) > target_samples:
        return y[:target_samples]
    if len(y) < target_samples:
        return np.pad(y, (0, target_samples - len(y)), mode="constant")
    return y


def extract_logmel(audio_path: str, cfg: Config) -> np.ndarray:
    target_samples = int(round(cfg.sample_rate * cfg.duration_s))
    win_length = int(round(cfg.sample_rate * cfg.frame_ms / 1000.0))
    hop_length = int(round(cfg.sample_rate * cfg.hop_ms / 1000.0))

    y, _ = librosa.load(audio_path, sr=cfg.sample_rate, mono=True)
    y = fix_audio_length(y, target_samples)

    mel = librosa.feature.melspectrogram(
        y=y,
        sr=cfg.sample_rate,
        n_fft=cfg.n_fft,
        win_length=win_length,
        hop_length=hop_length,
        n_mels=cfg.n_mels,
        fmin=cfg.fmin,
        fmax=cfg.fmax,
        power=2.0,
        center=False,
    )
    logmel = np.log(mel + cfg.eps).astype(np.float32)

    # Hard check expected shape. Pad/truncate only if a backend/librosa version differs.
    exp = expected_frames(cfg)
    if logmel.shape[1] < exp:
        logmel = np.pad(logmel, ((0, 0), (0, exp - logmel.shape[1])), mode="constant")
    elif logmel.shape[1] > exp:
        logmel = logmel[:, :exp]

    return logmel.astype(np.float32)


def load_or_build_cache(df: pd.DataFrame, cache_path: Path, cfg: Config, force: bool) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
    if cache_path.exists() and not force:
        print(f"Loading feature cache: {cache_path}")
        z = np.load(cache_path, allow_pickle=True)
        X = z["X"].astype(np.float32)
        y = z["y"].astype(np.int32)
        rel_paths = [str(x) for x in z["rel_paths"]]
        folders = [str(x) for x in z["source_folders"]]
        return X, y, rel_paths, folders

    print("Building 5 s log-mel feature cache...")
    print(f"  Clips: {len(df)}")
    print(f"  Expected feature shape: ({cfg.n_mels}, {expected_frames(cfg)})")

    feats = []
    start = time.time()
    for i, row in df.iterrows():
        if (i + 1) % 100 == 0 or i == 0:
            print(f"  [{i+1:4d}/{len(df)}] {row['source_folder']} / {Path(row['file_path']).name}")
        feats.append(extract_logmel(row["file_path"], cfg))

    X = np.stack(feats, axis=0).astype(np.float32)
    y = df["binary_hard_label"].to_numpy(dtype=np.int32)
    rel_paths = df["rel_path"].tolist()
    folders = df["source_folder"].tolist()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        cache_path,
        X=X,
        y=y,
        rel_paths=np.array(rel_paths, dtype=object),
        source_folders=np.array(folders, dtype=object),
        config=json.dumps(asdict(cfg), sort_keys=True),
    )
    print(f"Saved feature cache: {cache_path}")
    print(f"Feature cache build time: {time.time() - start:.1f} s")
    return X, y, rel_paths, folders


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


def build_model(input_shape: Tuple[int, int, int], learning_rate: float) -> tf.keras.Model:
    inp = tf.keras.Input(shape=input_shape, name="logmel")

    x = tf.keras.layers.Conv2D(16, (3, 3), strides=(2, 2), padding="same", use_bias=False, name="stem_conv")(inp)
    x = tf.keras.layers.BatchNormalization(name="stem_bn")(x)
    x = tf.keras.layers.ReLU(max_value=6.0, name="stem_relu6")(x)

    x = ds_block(x, 24, stride=(1, 1), name="block1")
    x = ds_block(x, 32, stride=(2, 2), name="block2")
    x = ds_block(x, 48, stride=(1, 1), name="block3")
    x = ds_block(x, 64, stride=(2, 2), name="block4")

    x = tf.keras.layers.GlobalAveragePooling2D(name="gap")(x)
    x = tf.keras.layers.Dense(32, activation="relu", name="dense32")(x)
    x = tf.keras.layers.Dropout(0.2, name="dropout")(x)
    out = tf.keras.layers.Dense(1, activation="sigmoid", name="p_bird")(x)

    model = tf.keras.Model(inp, out, name="student_5s_logmel_dscnn")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=tf.keras.losses.BinaryCrossentropy(),
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name="bin_acc", threshold=0.5),
            tf.keras.metrics.AUC(name="roc_auc", curve="ROC"),
            tf.keras.metrics.AUC(name="pr_auc", curve="PR"),
            tf.keras.metrics.Precision(name="precision", thresholds=0.5),
            tf.keras.metrics.Recall(name="recall", thresholds=0.5),
        ],
    )
    return model


def normalize_fold(X_train: np.ndarray, X_val: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
    # Global mean/std computed only from the training fold to avoid leakage.
    mean = float(np.mean(X_train))
    std = float(np.std(X_train) + 1e-6)
    Xtr = (X_train - mean) / std
    Xva = (X_val - mean) / std
    return Xtr.astype(np.float32), Xva.astype(np.float32), {"mean": mean, "std": std}


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
        # Among thresholds satisfying FPR, maximize recall/TPR. Break ties by lower threshold.
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
        is_bird_folder = folder in BIRD_FOLDERS
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


def write_report(
    report_path: Path,
    cfg: Config,
    summary: Dict,
    fold_df: pd.DataFrame,
    folder_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    lines = []
    A = lines.append

    A("# Student 5 s Hard-Label Baseline Report")
    A("")
    A("Hard-label baseline only. No Teacher/KD loss used in training.")
    A("")
    A("## Configuration")
    A("")
    A("```text")
    A(f"sample_rate = {cfg.sample_rate}")
    A(f"duration_s = {cfg.duration_s}")
    A(f"feature = log-mel")
    A(f"n_mels = {cfg.n_mels}")
    A(f"frame_ms = {cfg.frame_ms}")
    A(f"hop_ms = {cfg.hop_ms}")
    A(f"n_fft = {cfg.n_fft}")
    A(f"batch_size = {cfg.batch_size}")
    A(f"epochs = {cfg.epochs}")
    A(f"patience = {cfg.patience}")
    A(f"folds = {cfg.n_splits}")
    A("model = compact DS-CNN")
    A("loss = weighted binary crossentropy")
    A("```")
    A("")
    A("## Summary")
    A("")
    A(f"- Total clips: {summary['n_clips']}")
    A(f"- Bird clips: {summary['n_bird']}")
    A(f"- Non-bird clips: {summary['n_nonbird']}")
    A(f"- Parameter count: {summary['param_count']}")
    A("")
    A("## Cross-Validation Metrics")
    A("")
    for metric in [
        "accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5",
        "roc_auc", "pr_auc", "recall_at_fpr_target", "fpr_at_target",
    ]:
        mean_key = f"{metric}_mean"
        std_key = f"{metric}_std"
        if mean_key in summary:
            A(f"- {metric}: {summary[mean_key]:.4f} ± {summary[std_key]:.4f}")
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
    A("## Output Files")
    A("")
    rel = lambda p: str(Path(p).relative_to(output_dir.parent.parent))
    for name in [
        "metrics_summary.json",
        "fold_metrics.csv",
        "per_folder_metrics.csv",
        "predictions_all_folds.csv",
        "student_5s_hardlabel_baseline_report.md",
    ]:
        A(f"- `{rel(output_dir / name)}`")
    A("")
    A("## Interpretation Notes")
    A("")
    A("- This is the mandatory hard-label baseline. KD is only useful if it beats this baseline.")
    A("- Metrics should be judged primarily by bird recall at low non-bird false-positive rate, PR-AUC, and per-class false positives.")
    A("- If 5 s accuracy is good, the next step is KD comparison. If 5 s is too expensive on-device, then test a 2 s fallback.")
    A("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    cfg = Config(
        epochs=args.epochs,
        batch_size=args.batch_size,
        patience=args.patience,
        seed=args.seed,
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
    print("STUDENT 5S HARD-LABEL BASELINE")
    print("=" * 70)
    print(f"Repo root    : {repo_root}")
    print(f"Dataset root : {dataset_root}")
    print(f"Output dir   : {output_dir}")
    print(f"TensorFlow   : {tf.__version__}")
    print("=" * 70)

    df = collect_dataset(dataset_root)
    print("Dataset summary:")
    print(df.groupby(["source_folder", "binary_hard_label"]).size().to_string())
    print(f"Total clips: {len(df)} | bird={int(df.binary_hard_label.sum())} | nonbird={int((df.binary_hard_label == 0).sum())}")

    manifest_path = output_dir / "manifest.csv"
    df.assign(file_path=df["file_path"].map(lambda p: str(Path(p).relative_to(repo_root)))).to_csv(manifest_path, index=False)

    cache_path = cache_dir / f"fsc22_logmel_{int(cfg.duration_s)}s_{cfg.sample_rate}hz_{cfg.n_mels}mel_{int(cfg.hop_ms)}ms.npz"
    X, y, rel_paths, folders = load_or_build_cache(df, cache_path, cfg, args.force_cache)

    print(f"Feature tensor: {X.shape} dtype={X.dtype}")
    input_shape = (X.shape[1], X.shape[2], 1)
    probe_model = build_model(input_shape, cfg.learning_rate)
    param_count = int(probe_model.count_params())
    print(f"Model input shape: {input_shape}")
    print(f"Parameter count: {param_count}")
    del probe_model
    tf.keras.backend.clear_session()

    # Stratify by original 27-class folder, not just binary label.
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

        X_train, X_val, norm = normalize_fold(X_train_raw, X_val_raw)
        X_train = X_train[..., np.newaxis]
        X_val = X_val[..., np.newaxis]

        n_pos = int(np.sum(y_train == 1))
        n_neg = int(np.sum(y_train == 0))
        pos_weight = float(n_neg / max(1, n_pos))
        class_weight = {0: 1.0, 1: pos_weight}
        print(f"Train: {len(train_idx)} clips | pos={n_pos} neg={n_neg} pos_weight={pos_weight:.3f}")
        print(f"Val  : {len(val_idx)} clips | pos={int(np.sum(y_val == 1))} neg={int(np.sum(y_val == 0))}")

        model = build_model(input_shape, cfg.learning_rate)

        fold_model_path = model_dir / f"student_5s_hardlabel_fold{fold}.keras"
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
                patience=max(3, cfg.patience // 3),
                min_lr=1e-5,
                verbose=1,
            ),
        ]

        hist = model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=cfg.epochs,
            batch_size=cfg.batch_size,
            class_weight=class_weight,
            callbacks=callbacks,
            verbose=2,
        )

        hist_df = pd.DataFrame(hist.history)
        hist_df.to_csv(fold_dir / f"history_fold{fold}.csv", index=False)

        y_prob = model.predict(X_val, batch_size=cfg.batch_size, verbose=0).reshape(-1)
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
            "pos_weight": pos_weight,
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
        }
        fold_rows.append(fold_row)

        print("Fold metrics @0.5:")
        print(json.dumps({k: fold_row[k] for k in ["accuracy_0p5", "precision_0p5", "recall_0p5", "f1_0p5", "roc_auc", "pr_auc"]}, indent=2))
        print("Fold metrics @target FPR:")
        print(json.dumps({k: fold_row[k] for k in ["threshold_at_fpr_target", "recall_at_fpr_target", "precision_at_fpr_target", "fpr_at_target"]}, indent=2))

        # Save predictions.
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

        # Save fold normalizer.
        with open(fold_dir / f"normalizer_fold{fold}.json", "w", encoding="utf-8") as fh:
            json.dump(norm, fh, indent=2)

    fold_df = pd.DataFrame(fold_rows)
    pred_df = pd.DataFrame(pred_rows)
    folder_df = pd.concat(folder_metric_dfs, ignore_index=True)

    # Aggregate per-folder metrics across folds from OOF predictions.
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
        "decision_context": "5 s hard-label baseline before KD",
        "n_clips": int(len(df)),
        "n_bird": int(np.sum(y == 1)),
        "n_nonbird": int(np.sum(y == 0)),
        "param_count": param_count,
        "config": asdict(cfg),
        "feature_shape": list(X.shape[1:]),
        "input_shape": list(input_shape),
        "tensorflow_version": tf.__version__,
        "output_dir": str(output_dir.relative_to(repo_root)),
    }

    metric_map = {
        "accuracy_0p5": "accuracy_0p5",
        "precision_0p5": "precision_0p5",
        "recall_0p5": "recall_0p5",
        "f1_0p5": "f1_0p5",
        "roc_auc": "roc_auc",
        "pr_auc": "pr_auc",
        "recall_at_fpr_target": "recall_at_fpr_target",
        "precision_at_fpr_target": "precision_at_fpr_target",
        "fpr_at_target": "fpr_at_target",
    }
    for key in metric_map:
        summary[f"{key}_mean"] = float(fold_df[key].mean())
        summary[f"{key}_std"] = float(fold_df[key].std(ddof=0))

    # OOF metrics over all validation predictions.
    y_oof = pred_df["binary_hard_label"].to_numpy(dtype=np.int32)
    p_oof = pred_df["p_bird"].to_numpy(dtype=np.float32)
    m05_oof = metrics_at_threshold(y_oof, p_oof, 0.5)
    mt_oof = threshold_for_target_fpr(y_oof, p_oof, cfg.target_fpr)
    summary["oof_metrics_0p5"] = m05_oof
    summary["oof_metrics_target_fpr"] = mt_oof
    summary["oof_roc_auc"] = safe_auc(y_oof, p_oof, "roc")
    summary["oof_pr_auc"] = safe_auc(y_oof, p_oof, "pr")

    with open(output_dir / "metrics_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    write_report(
        output_dir / "student_5s_hardlabel_baseline_report.md",
        cfg,
        summary,
        fold_df,
        oof_folder_df,
        output_dir,
    )

    print("")
    print("=" * 70)
    print("STUDENT 5S HARD-LABEL BASELINE - SUMMARY")
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
    print("Output files:")
    for name in [
        "metrics_summary.json",
        "fold_metrics.csv",
        "per_folder_metrics.csv",
        "predictions_all_folds.csv",
        "student_5s_hardlabel_baseline_report.md",
    ]:
        print(f"  - {output_dir.relative_to(repo_root) / name}")
    print("=" * 70)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# ======================================================================================
# verify_teacher_labelmap.py  --  VERIFICATION ONLY. THIS SCRIPT DOES NOT TRAIN ANYTHING.
# --------------------------------------------------------------------------------------
# Purpose:
#   Confirm that the existing 27-class FSC22 "mel-spectrogram + Swint_LSTM" checkpoint can
#   be reused as a Teacher for a binary bird / non-bird knowledge-distillation project.
#
#   It rebuilds the ORIGINAL preprocessing + model + label mapping exactly as in
#     Codes/torch/melspectrogram_fsc22/swintlstm.py
#   (class definitions are re-implemented here, NOT imported, so that importing this file
#    never triggers the training loop in the original script), loads a fold-0 checkpoint,
#   runs inference on the fold-0 evaluation split, and checks:
#       * overall accuracy is close to the recorded fold-0 result (~0.83)
#       * folder "23birdchirping"  -> class index 2
#       * folder "24wingflapping"  -> class index 6
#
# What it MODIFIES: nothing outside teacher_kd/.  It only READS the dataset + checkpoints.
#
# Important architectural note (do not "simplify" away):
#   In the original model, swin_t outputs a 2-D tensor of shape (B, 768). Feeding a 2-D
#   tensor to nn.LSTM makes PyTorch treat it as an *unbatched* sequence of length B, i.e.
#   the batch dimension is consumed as the time dimension. Consequently the predictions
#   depend on the batch size and the sample ordering. To reproduce the recorded ~0.83
#   accuracy we therefore replicate the ORIGINAL eval configuration: batch_size = 32,
#   shuffle = False, and the exact folder-grouped ordering of the original eval split.
#   (The task text suggested batch size 8/16; we deliberately use 32 for fidelity.)
#
#   The label map (which folder gets which index) is derived purely from the LOCAL
#   Dataset/fsc22 via unsorted os.listdir(); it is the SAME for every checkpoint. What
#   distinguishes a compatible checkpoint from an incompatible one is therefore the
#   ACCURACY: a checkpoint trained with a different folder order collapses to ~1/27.
# ======================================================================================

import os
import sys
import json
import glob
import importlib

# --------------------------------------------------------------------------------------
# 0) LIGHTWEIGHT ENVIRONMENT CHECK  (runs before any heavy import / any real work)
#    Reports exactly which required package is missing or unimportable, then stops.
#    Does NOT install anything.
# --------------------------------------------------------------------------------------
REQUIRED_PACKAGES = ["torch", "torchvision", "librosa", "sklearn", "pandas", "numpy"]


def check_environment():
    """Try to import every required package. Return {pkg: error_message} for failures.

    We really import (not just find_spec) so that an interpreter/ABI mismatch — e.g. a
    cp313-built torch loaded under python3.12 — is caught and reported instead of crashing
    later with an obscure C-extension error.
    """
    problems = {}
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
        except Exception as exc:  # ImportError, or C-extension ABI errors, etc.
            problems[pkg] = f"{type(exc).__name__}: {exc}"
    return problems


_env_problems = check_environment()
if _env_problems:
    print("=" * 70)
    print("ENVIRONMENT CHECK FAILED - verification did NOT run.")
    print("The following required packages are missing or cannot be imported")
    print("by this Python interpreter (%s):" % sys.version.split()[0])
    print("-" * 70)
    for pkg, msg in _env_problems.items():
        print(f"  [MISSING] {pkg:12s} -> {msg}")
    print("-" * 70)
    print("No packages were installed (per task constraints). Fix the environment,")
    print("then re-run:  python3 teacher_kd/verify_teacher_labelmap.py")
    print("=" * 70)
    sys.exit(1)

# Safe to import now (all present).
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import librosa
from torchvision import models
from sklearn.model_selection import KFold
from sklearn.metrics import confusion_matrix, accuracy_score

# --------------------------------------------------------------------------------------
# 1) CONFIGURATION
# --------------------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "teacher_kd")

DATASET_ROOT = os.path.join(REPO_ROOT, "Dataset", "fsc22")

# Primary teacher checkpoint (dissertation run).
PRIMARY_CKPT = os.path.join(
    REPO_ROOT, "output_for_dissertation", "fsc22", "model", "melspectrogram",
    "Swint_LSTM", "2025_07_21_16_06_03_Swint_LSTM_0.pth")

# Backup fold-0 checkpoint (trained locally on this machine); resolved by glob so we
# pick the *_0.pth file regardless of its exact timestamp prefix.
BACKUP_DIR = os.path.join(
    REPO_ROOT, "output_p_10", "fsc22", "model", "melspectrogram", "Swint_LSTM")

K_FOLDS = 5
CURRENT_FOLD = 0
MAX_LENGTH = 432          # time frames fed to the model (128 x 432)
EVAL_BATCH_SIZE = 32      # MUST match original for accuracy reproduction (see header note)

# PASS thresholds
ACC_THRESHOLD = 0.75      # "reasonably close to ~0.83"; incompatible order collapses to ~0.04
RECORDED_FOLD0_ACC = 0.8370  # from output_for_dissertation/.../excel_melspectrogram (fold 0)

BIRD_FOLDERS = ["23birdchirping", "24wingflapping"]
EXPECTED_BIRD_INDICES = {"23birdchirping": 2, "24wingflapping": 6}

PREPROCESSING_SUMMARY = {
    "loader": "librosa.load(path, sr=None)",
    "sample_rate": "native (44100 Hz kept, no resample)",
    "channels": "mono (librosa default mono=True)",
    "feature": "librosa.feature.melspectrogram(y=y, sr=sr)  [library defaults]",
    "n_fft": 2048,
    "hop_length": 512,
    "n_mels": 128,
    "power": 2.0,
    "power_to_db": False,
    "log_scaling": False,
    "normalization": False,
    "time_frames": MAX_LENGTH,
    "length_handling": "if <432 tile/repeat along time axis then truncate; if >432 truncate",
    "model_input_shape": "[B, 128, 432]",
    "channel_expansion": "1 -> 3 channels via repeat(1,3,1,1) inside model.forward",
    "resize_to_224": False,
    "imagenet_mean_std_norm": False,
    "eval_batch_size": EVAL_BATCH_SIZE,
    "eval_batch_note": ("swin_t output is 2-D (B,768); nn.LSTM treats it as an unbatched "
                        "sequence of length B, so batch size/order affect predictions. "
                        "batch_size=32 + shuffle=False replicate the original eval."),
}


# --------------------------------------------------------------------------------------
# 2) PREPROCESSING  (reimplemented verbatim from the original fsc22Dataset.__getitem__)
# --------------------------------------------------------------------------------------
def extract_feature(audio_path, max_length=MAX_LENGTH):
    """Reproduce the exact eval-time feature of the original code (no augmentation)."""
    y, sr = librosa.load(audio_path, sr=None)                      # native 44.1kHz, mono
    feature = librosa.feature.melspectrogram(y=y, sr=sr)           # defaults; power mel
    # NOTE: intentionally NO power_to_db, NO log, NO normalization.
    if feature.shape[1] > max_length:
        feature = feature[:, :max_length]
    else:
        while feature.shape[1] < max_length:
            feature = np.concatenate((feature, feature), axis=1)   # tile along time
        feature = feature[:, :max_length]
    return feature.astype(np.float32)                              # (128, 432)


# --------------------------------------------------------------------------------------
# 3) MODEL  (reimplemented verbatim from the original Swint_LSTM class)
# --------------------------------------------------------------------------------------
class Swint_LSTM(nn.Module):
    def __init__(self, num_classes):
        super(Swint_LSTM, self).__init__()
        # weights=None: architecture is identical; the checkpoint supplies ALL weights
        # (swint.*, lstm.*, fc.*), so we avoid an unnecessary ImageNet download.
        self.swint = models.swin_t(weights=None)
        in_features = self.swint.head.in_features
        self.swint.head = nn.Identity()
        self.lstm = nn.LSTM(input_size=in_features, hidden_size=in_features,
                            num_layers=2, batch_first=True, bidirectional=True, dropout=0.2)
        self.fc = nn.Sequential(
            nn.Linear(in_features=in_features * 2, out_features=num_classes)
        )

    def forward(self, x):
        x = x.unsqueeze(1).float().repeat(1, 3, 1, 1)   # (B,128,432) -> (B,3,128,432)
        x = self.swint(x)                               # (B, 768)
        x, _ = self.lstm(x)                             # (B, 1536)  (batch-as-sequence)
        x = self.fc(x)                                  # (B, num_classes)
        return x


# --------------------------------------------------------------------------------------
# 4) LABEL MAP + FOLD-0 EVAL SPLIT
#    Reproduces fsc22Dataset._get_data() ordering exactly:
#      * folders iterated in unsorted os.listdir() order (class index = discovery order)
#      * files iterated in unsorted os.listdir() order
#      * KFold(n_splits=5, shuffle=False) applied PER folder; take fold-0 eval indices
# --------------------------------------------------------------------------------------
def build_labelmap_and_eval_split(dataset_root, k_folds=K_FOLDS, current_fold=CURRENT_FOLD):
    label_dict = {}          # folder -> class index (discovery order)
    counter = 0
    eval_samples = []        # list of (file_path, label_index, folder)

    for folder in os.listdir(dataset_root):                  # UNSORTED (matches original)
        folder_path = os.path.join(dataset_root, folder)
        if not os.path.isdir(folder_path):
            continue
        files = os.listdir(folder_path)                      # UNSORTED (matches original)
        data = []
        for file_name in files:
            file_path = os.path.join(folder_path, file_name)
            if folder not in label_dict:
                label_dict[folder] = counter
                counter += 1
            data.append((file_path, label_dict[folder], folder))
        kf = KFold(n_splits=k_folds)                         # shuffle=False (matches original)
        folds = list(kf.split(range(len(data))))
        _, eval_indices = folds[current_fold]
        eval_samples.extend(data[i] for i in eval_indices)

    return label_dict, eval_samples


# --------------------------------------------------------------------------------------
# 5) INFERENCE FOR ONE CHECKPOINT
# --------------------------------------------------------------------------------------
def run_attempt(checkpoint_path, label_dict, eval_samples, device):
    """Load one checkpoint, run fold-0 eval inference, return a result dict.

    Never raises for expected failures (missing file / load error): these are captured
    and reported so the caller can fall back to the backup checkpoint.
    """
    num_classes = len(label_dict)
    idx_to_folder = {v: k for k, v in label_dict.items()}
    folder_names_by_index = [idx_to_folder[i] for i in range(num_classes)]
    bird_indices = sorted(label_dict[f] for f in BIRD_FOLDERS if f in label_dict)

    result = {
        "checkpoint": checkpoint_path,
        "exists": os.path.isfile(checkpoint_path),
        "loaded": False,
        "error": None,
        "num_classes": num_classes,
        "bird_indices": bird_indices,
    }

    if not result["exists"]:
        result["error"] = "checkpoint file not found"
        return result

    # ---- build model + load weights (state_dict only) ----
    try:
        model = Swint_LSTM(num_classes=num_classes)
        try:
            state = torch.load(checkpoint_path, map_location=device, weights_only=True)
        except TypeError:
            state = torch.load(checkpoint_path, map_location=device)  # older torch
        model.load_state_dict(state, strict=True)
        model.to(device).eval()
        result["loaded"] = True
    except Exception as exc:
        result["error"] = f"load failed: {type(exc).__name__}: {exc}"
        return result

    # ---- inference over fold-0 eval split, preserving original order + batch size ----
    y_true, y_pred, p_bird_list, max_prob_list = [], [], [], []
    rows = []
    try:
        with torch.no_grad():
            for start in range(0, len(eval_samples), EVAL_BATCH_SIZE):
                batch = eval_samples[start:start + EVAL_BATCH_SIZE]
                feats = np.stack([extract_feature(fp) for fp, _, _ in batch], axis=0)
                x = torch.from_numpy(feats).to(device)          # (b,128,432)
                logits = model(x)                               # (b, num_classes)
                probs = F.softmax(logits, dim=1)
                preds = torch.argmax(probs, dim=1)
                p_bird = probs[:, bird_indices].sum(dim=1) if bird_indices else torch.zeros(len(batch))
                maxp = probs.max(dim=1).values

                probs_cpu = probs.cpu().numpy()
                for j, (fp, lab, folder) in enumerate(batch):
                    pred_idx = int(preds[j].item())
                    pb = float(p_bird[j].item())
                    y_true.append(int(lab))
                    y_pred.append(pred_idx)
                    p_bird_list.append(pb)
                    max_prob_list.append(float(maxp[j].item()))
                    rows.append({
                        "file_path": os.path.relpath(fp, REPO_ROOT),
                        "true_folder": folder,
                        "true_index": int(lab),
                        "pred_index": pred_idx,
                        "pred_folder": folder_names_by_index[pred_idx],
                        "correct": int(pred_idx == lab),
                        "p_bird": round(pb, 6),
                        "p_non_bird": round(1.0 - pb, 6),
                        "max_prob": round(float(maxp[j].item()), 6),
                    })
    except Exception as exc:
        result["error"] = f"inference failed: {type(exc).__name__}: {exc}"
        return result

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    overall_acc = float(accuracy_score(y_true, y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=list(range(num_classes)))

    # per-class accuracy + predicted-distribution per true folder
    per_class = {}
    pred_distribution = {}
    for idx in range(num_classes):
        folder = folder_names_by_index[idx]
        row = cm[idx]
        total = int(row.sum())
        correct = int(row[idx])
        per_class[folder] = {
            "index": idx,
            "n_eval": total,
            "correct": correct,
            "accuracy": round(correct / total, 4) if total else None,
        }
        dist = {folder_names_by_index[j]: int(row[j]) for j in range(num_classes) if row[j] > 0}
        pred_distribution[folder] = dict(sorted(dist.items(), key=lambda kv: -kv[1]))

    # bird-probability sanity: mean P(bird) on true-bird vs true-non-bird clips
    p_bird_arr = np.array(p_bird_list)
    true_bird_mask = np.isin(y_true, bird_indices)
    mean_pbird_on_bird = float(p_bird_arr[true_bird_mask].mean()) if true_bird_mask.any() else None
    mean_pbird_on_nonbird = float(p_bird_arr[~true_bird_mask].mean()) if (~true_bird_mask).any() else None

    # index checks (checkpoint-independent: derived from local dataset order)
    birdchirping_index = label_dict.get("23birdchirping")
    wingflapping_index = label_dict.get("24wingflapping")
    index_checks = {
        "23birdchirping": {"got": birdchirping_index, "expected": 2,
                           "ok": birdchirping_index == 2},
        "24wingflapping": {"got": wingflapping_index, "expected": 6,
                           "ok": wingflapping_index == 6},
    }
    labelmap_ok = all(c["ok"] for c in index_checks.values())
    accuracy_ok = overall_acc >= ACC_THRESHOLD
    status = "PASS" if (labelmap_ok and accuracy_ok) else "FAIL"

    result.update({
        "overall_accuracy": round(overall_acc, 4),
        "recorded_fold0_accuracy": RECORDED_FOLD0_ACC,
        "accuracy_ok": accuracy_ok,
        "labelmap_ok": labelmap_ok,
        "index_checks": index_checks,
        "verification_status": status,
        "n_eval_samples": int(len(y_true)),
        "per_class_accuracy": per_class,
        "pred_distribution": pred_distribution,
        "mean_p_bird_on_true_bird": None if mean_pbird_on_bird is None else round(mean_pbird_on_bird, 4),
        "mean_p_bird_on_true_nonbird": None if mean_pbird_on_nonbird is None else round(mean_pbird_on_nonbird, 4),
        "_rows": rows,                 # for CSV (stripped before JSON dump)
        "_cm": cm,                     # for CSV (stripped before JSON dump)
        "_folder_names_by_index": folder_names_by_index,
    })
    return result


# --------------------------------------------------------------------------------------
# 6) OUTPUT WRITERS
# --------------------------------------------------------------------------------------
def write_predictions_csv(result, path):
    pd.DataFrame(result["_rows"]).to_csv(path, index=False)


def write_confusion_csv(result, path):
    names = result["_folder_names_by_index"]
    df = pd.DataFrame(result["_cm"], index=names, columns=names)
    df.index.name = "true\\pred"
    df.to_csv(path)


def write_verified_label_map(final_result, label_dict, checkpoint_used, path):
    idx_to_folder = {v: k for k, v in label_dict.items()}
    num_classes = len(label_dict)
    bird_indices = sorted(label_dict[f] for f in BIRD_FOLDERS if f in label_dict)
    non_bird_indices = [i for i in range(num_classes) if i not in bird_indices]
    obj = {
        "class_index_to_folder": {str(i): idx_to_folder[i] for i in range(num_classes)},
        "folder_to_class_index": {k: v for k, v in sorted(label_dict.items(), key=lambda kv: kv[1])},
        "bird_indices": bird_indices,
        "bird_folders": [f for f in BIRD_FOLDERS if f in label_dict],
        "non_bird_indices": non_bird_indices,
        "checkpoint_used": checkpoint_used,
        "preprocessing_summary": PREPROCESSING_SUMMARY,
        "verification_status": final_result.get("verification_status", "FAIL"),
        "binary_collapse": {
            "P_bird": "softmax(logits)[:, bird_indices].sum(dim=1)",
            "P_non_bird": "1 - P_bird",
            "bird_indices_used": bird_indices,
        },
    }
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)


def _clean_for_json(result):
    """Strip non-serializable helper keys from a result dict copy."""
    return {k: v for k, v in result.items() if not k.startswith("_")}


def write_json_report(report, path):
    with open(path, "w") as fh:
        json.dump(report, fh, indent=2)


def write_md_report(report, path):
    L = []
    A = L.append
    A("# Teacher Label-Map Verification Report")
    A("")
    A("**Verification-only** — no training was performed; existing files were only read.")
    A("")
    A(f"- Date: {report['timestamp']}")
    A(f"- Interpreter: {report['python_version']}")
    A(f"- Torch: {report['torch_version']}  |  Device: {report['device']}  |  "
      f"CUDA available: {report['cuda_available']}")
    A(f"- Dataset root: `{os.path.relpath(DATASET_ROOT, REPO_ROOT)}`  "
      f"({report['num_classes']} classes, {report['n_eval_samples']} fold-0 eval clips)")
    A(f"- Eval config: batch_size={EVAL_BATCH_SIZE}, shuffle=False "
      f"(replicates original for accuracy fidelity)")
    A("")
    A(f"## Final decision: **{report['final_status']}**  "
      f"(checkpoint: `{os.path.relpath(report['checkpoint_used'], REPO_ROOT)}`)")
    A("")
    A(report["decision_note"])
    A("")

    def attempt_block(title, res):
        A(f"## {title}")
        A("")
        if res is None:
            A("_Not attempted._")
            A("")
            return
        A(f"- Checkpoint: `{os.path.relpath(res['checkpoint'], REPO_ROOT)}`")
        A(f"- File exists: {res['exists']}  |  Loaded: {res.get('loaded')}")
        if res.get("error"):
            A(f"- **Error:** {res['error']}")
            A("")
            return
        A(f"- Overall accuracy: **{res['overall_accuracy']}** "
          f"(recorded fold-0 ~{res['recorded_fold0_accuracy']}; threshold {ACC_THRESHOLD})")
        A(f"- 23birdchirping -> index {res['index_checks']['23birdchirping']['got']} "
          f"(expected 2) : {'OK' if res['index_checks']['23birdchirping']['ok'] else 'MISMATCH'}")
        A(f"- 24wingflapping -> index {res['index_checks']['24wingflapping']['got']} "
          f"(expected 6) : {'OK' if res['index_checks']['24wingflapping']['ok'] else 'MISMATCH'}")
        A(f"- Bird indices used for collapse: {res['bird_indices']}")
        A(f"- Mean P(bird) on true-bird clips: {res['mean_p_bird_on_true_bird']}  |  "
          f"on true-non-bird clips: {res['mean_p_bird_on_true_nonbird']}")
        A(f"- Status: **{res['verification_status']}**")
        A("")
        A("### Per-class accuracy")
        A("")
        A("| idx | folder | n | correct | acc |")
        A("|----:|--------|--:|--------:|----:|")
        pc = res["per_class_accuracy"]
        for folder, info in sorted(pc.items(), key=lambda kv: kv[1]["index"]):
            A(f"| {info['index']} | {folder} | {info['n_eval']} | "
              f"{info['correct']} | {info['accuracy']} |")
        A("")

    attempt_block("Primary checkpoint attempt", report["attempts"].get("primary"))
    attempt_block("Backup checkpoint attempt", report["attempts"].get("backup"))

    A("## Output files")
    A("")
    for f in report["output_files"]:
        A(f"- `{f}`")
    A("")
    with open(path, "w") as fh:
        fh.write("\n".join(L))


# --------------------------------------------------------------------------------------
# 7) MAIN
# --------------------------------------------------------------------------------------
def main():
    import datetime
    os.makedirs(OUT_DIR, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.isdir(DATASET_ROOT):
        print(f"ERROR: dataset root not found: {DATASET_ROOT}")
        sys.exit(1)

    label_dict, eval_samples = build_labelmap_and_eval_split(DATASET_ROOT)
    num_classes = len(label_dict)

    # Resolve backup checkpoint by glob (*_0.pth).
    backup_matches = sorted(glob.glob(os.path.join(BACKUP_DIR, "*_0.pth")))
    backup_ckpt = backup_matches[0] if backup_matches else os.path.join(BACKUP_DIR, "MISSING_0.pth")

    attempts = {}

    # --- primary ---
    print(f"[1/2] Primary checkpoint attempt: {os.path.relpath(PRIMARY_CKPT, REPO_ROOT)}")
    primary = run_attempt(PRIMARY_CKPT, label_dict, eval_samples, device)
    attempts["primary"] = primary
    primary_ok = primary.get("verification_status") == "PASS"
    if primary.get("error"):
        print(f"      -> error: {primary['error']}")
    else:
        print(f"      -> acc={primary.get('overall_accuracy')}  status={primary.get('verification_status')}")

    # --- backup (only if primary did not PASS) ---
    backup = None
    if not primary_ok:
        print(f"[2/2] Primary did not PASS -> backup attempt: {os.path.relpath(backup_ckpt, REPO_ROOT)}")
        backup = run_attempt(backup_ckpt, label_dict, eval_samples, device)
        attempts["backup"] = backup
        if backup.get("error"):
            print(f"      -> error: {backup['error']}")
        else:
            print(f"      -> acc={backup.get('overall_accuracy')}  status={backup.get('verification_status')}")
    else:
        print("[2/2] Primary PASSed -> backup not needed.")

    # --- decide which result is final ---
    if primary_ok:
        final_result, checkpoint_used, final_status = primary, PRIMARY_CKPT, "PASS (primary)"
        decision_note = "Primary dissertation checkpoint PASSED. Use it as the Teacher."
    elif backup is not None and backup.get("verification_status") == "PASS":
        final_result, checkpoint_used, final_status = backup, backup_ckpt, "PASS (backup)"
        decision_note = ("Primary FAILED but the locally-trained backup checkpoint PASSED. "
                         "Use the backup checkpoint as the Teacher.")
    else:
        # neither passed: keep the more informative (loaded) attempt for the label map file
        final_result = primary if primary.get("loaded") else (backup or primary)
        checkpoint_used = PRIMARY_CKPT
        final_status = "FAIL (both)"
        decision_note = ("Neither the primary nor the backup checkpoint passed verification. "
                         "Do NOT retrain automatically; investigate label order / checkpoint "
                         "integrity / preprocessing before proceeding.")

    # --- write CSV outputs for the final (best available loaded) result ---
    output_files = []
    pred_csv = os.path.join(OUT_DIR, "fold0_predictions.csv")
    cm_csv = os.path.join(OUT_DIR, "confusion_matrix.csv")
    if "_rows" in final_result:
        write_predictions_csv(final_result, pred_csv)
        write_confusion_csv(final_result, cm_csv)
        output_files += [os.path.relpath(pred_csv, REPO_ROOT), os.path.relpath(cm_csv, REPO_ROOT)]

    # --- verified label map ---
    labelmap_json = os.path.join(OUT_DIR, "verified_label_map.json")
    write_verified_label_map(final_result, label_dict, checkpoint_used, labelmap_json)
    output_files.append(os.path.relpath(labelmap_json, REPO_ROOT))

    # --- assemble machine-readable report ---
    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "device": str(device),
        "dataset_root": os.path.relpath(DATASET_ROOT, REPO_ROOT),
        "num_classes": num_classes,
        "n_eval_samples": len(eval_samples),
        "eval_batch_size": EVAL_BATCH_SIZE,
        "acc_threshold": ACC_THRESHOLD,
        "final_status": final_status,
        "checkpoint_used": checkpoint_used,
        "decision_note": decision_note,
        "attempts": {k: _clean_for_json(v) for k, v in attempts.items()},
        "output_files": output_files,
    }

    report_json = os.path.join(OUT_DIR, "teacher_labelmap_verification_report.json")
    report_md = os.path.join(OUT_DIR, "teacher_labelmap_verification_report.md")
    write_json_report(report, report_json)
    report["output_files"] = output_files + [
        os.path.relpath(report_json, REPO_ROOT), os.path.relpath(report_md, REPO_ROOT)]
    write_md_report(report, report_md)
    output_files += [os.path.relpath(report_json, REPO_ROOT), os.path.relpath(report_md, REPO_ROOT)]

    # --- terminal summary ---
    fr = final_result
    print("")
    print("=" * 70)
    print("TEACHER LABEL-MAP VERIFICATION - SUMMARY")
    print("=" * 70)
    print(f"  Checkpoint used : {os.path.relpath(checkpoint_used, REPO_ROOT)}")
    if fr.get("loaded") and "overall_accuracy" in fr:
        print(f"  Overall accuracy: {fr['overall_accuracy']}  (recorded fold-0 ~{RECORDED_FOLD0_ACC})")
        print(f"  Bird indices    : {fr['bird_indices']}  "
              f"(23birdchirping={label_dict.get('23birdchirping')}, "
              f"24wingflapping={label_dict.get('24wingflapping')})")
    else:
        print(f"  Overall accuracy: n/a  ({fr.get('error')})")
        print(f"  Bird indices    : {sorted(label_dict[f] for f in BIRD_FOLDERS if f in label_dict)}")
    print(f"  Result          : {final_status}")
    print("  Output files:")
    for f in output_files:
        print(f"    - {f}")
    print("=" * 70)


if __name__ == "__main__":
    main()

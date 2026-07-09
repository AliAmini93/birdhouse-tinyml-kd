#!/usr/bin/env python3
# ======================================================================================
# generate_soft_labels.py  --  DETERMINISTIC teacher soft-label generation. NO TRAINING.
# --------------------------------------------------------------------------------------
# Produces 27-class + binary bird/non-bird soft labels for every FSC22 clip using the
# recovered 27-class Swint_LSTM teacher, for knowledge distillation into a TinyML student.
#
# WHY DETERMINISM MATTERS:
#   The Swint_LSTM teacher feeds swin_t's 2-D output (B,768) into nn.LSTM, which treats
#   the batch dimension as a *sequence*. Predictions therefore depend on batch size and
#   ordering. To make soft labels reproducible we pin: batch_size=32, shuffle=False, a
#   fixed file order, model.eval(), torch.no_grad(), no augmentation, deterministic cudnn.
#
# RECOVERED TEACHER MAPPING (from teacher_kd/recovered_teacher_label_map.json):
#   output index 12 -> 23birdchirping ; output index 20 -> 24wingflapping
#   bird_indices = [12, 20] ; P_bird = P[12] + P[20] ; P_non_bird = 1 - P_bird
#   The LOCAL os.listdir indices [2, 6] are INVALID for this checkpoint and are NOT used.
#
# Writes ONLY into teacher_kd/soft_labels/. Reads dataset + checkpoint; never modifies them.
# ======================================================================================

import os
import sys
import json
import warnings

# Reuse the exact model + preprocessing from the verifier (its top-level env-check runs on
# import and exits with the missing package name if anything is unavailable).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_teacher_labelmap as V  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

# The mel default (fmax=sr/2, n_mels=128 @44.1kHz) emits an "empty filters" UserWarning.
# This is IDENTICAL to the original training preprocessing; silence it for a clean log.
warnings.filterwarnings("ignore", message="Empty filters detected in mel frequency basis")

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
REPO_ROOT = V.REPO_ROOT
DATASET_ROOT = V.DATASET_ROOT
CKPT = V.PRIMARY_CKPT
BATCH_SIZE = V.EVAL_BATCH_SIZE            # 32 (must match training regime; deterministic)

LABEL_MAP_JSON = os.path.join(REPO_ROOT, "teacher_kd", "recovered_teacher_label_map.json")
OUT_DIR = os.path.join(REPO_ROOT, "teacher_kd", "soft_labels")

EXPECTED_BIRD_INDICES = [12, 20]
BIRD_FOLDERS = ["23birdchirping", "24wingflapping"]

ACC_PASS = 0.85
ACC_CAUTION = 0.75


# --------------------------------------------------------------------------------------
# Deterministic clip ordering
# --------------------------------------------------------------------------------------
def build_ordered_clips(label_map):
    """Deterministic file order.

    Priority (requirement #6):
      1. exact order saved by the recovery script  -> NOT saved, unavailable.
      2. folder order from recovered_teacher_label_map.json ('local_dataset_label_map',
         i.e. the os.listdir discovery order that produced the recovered mapping).
      3. files: sorted() within each folder (the raw os.listdir file order was never
         persisted, so sorted() is the reproducible choice).

    Returns (clips, ordering_desc) where clips = [(rel_path, folder, local_index), ...].
    """
    local_map = label_map.get("local_dataset_label_map")
    if local_map:
        folders = [f for f, _ in sorted(local_map.items(), key=lambda kv: kv[1])]
        folder_order_src = "recovered_teacher_label_map.json:local_dataset_label_map (discovery order)"
    else:
        folders = sorted(d for d in os.listdir(DATASET_ROOT)
                         if os.path.isdir(os.path.join(DATASET_ROOT, d)))
        local_map = {f: i for i, f in enumerate(folders)}
        folder_order_src = "sorted(os.listdir) fallback"

    clips = []
    for folder in folders:
        folder_path = os.path.join(DATASET_ROOT, folder)
        if not os.path.isdir(folder_path):
            continue
        for fn in sorted(os.listdir(folder_path)):          # deterministic file order
            fp = os.path.join(folder_path, fn)
            clips.append((os.path.relpath(fp, REPO_ROOT), folder, local_map.get(folder)))
    ordering_desc = (f"folders: {folder_order_src}; files: sorted() within each folder; "
                     f"batch_size={BATCH_SIZE}, shuffle=False")
    return clips, ordering_desc


def load_model(checkpoint_path, num_classes, device):
    model = V.Swint_LSTM(num_classes=num_classes)
    try:
        state = torch.load(checkpoint_path, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    return model


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def main():
    import datetime
    os.makedirs(OUT_DIR, exist_ok=True)

    # Deterministic execution.
    torch.manual_seed(0)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ---- load + validate recovered mapping ----
    with open(LABEL_MAP_JSON) as fh:
        label_map = json.load(fh)

    bird_indices = label_map.get("recommended_bird_indices")
    assert bird_indices == EXPECTED_BIRD_INDICES, (
        f"bird_indices in {LABEL_MAP_JSON} = {bird_indices}, expected {EXPECTED_BIRD_INDICES}. "
        "Refusing to generate soft labels with an unexpected mapping.")
    decision = label_map.get("verification_status")
    assert decision != "FAIL", (
        f"recovered mapping verification_status = {decision!r}; refusing to proceed on a FAILed map.")

    output_index_to_folder = {int(k): v for k, v in label_map["output_index_to_folder"].items()}
    num_classes = int(label_map["num_classes"])
    # sanity: the recovered bird indices really point at the bird folders
    assert output_index_to_folder.get(12) == "23birdchirping", "output 12 is not 23birdchirping"
    assert output_index_to_folder.get(20) == "24wingflapping", "output 20 is not 24wingflapping"

    clips, ordering_desc = build_ordered_clips(label_map)
    n = len(clips)
    print(f"Checkpoint : {os.path.relpath(CKPT, REPO_ROOT)}")
    print(f"Device     : {device} | clips: {n} | classes: {num_classes} | "
          f"bird_indices: {bird_indices} | recovery decision: {decision}")
    print(f"Ordering   : {ordering_desc}")

    model = load_model(CKPT, num_classes, device)

    # ---- deterministic inference ----
    logits_all = np.zeros((n, num_classes), dtype=np.float32)
    probs_all = np.zeros((n, num_classes), dtype=np.float32)
    print("Running deterministic inference ...")
    with torch.no_grad():
        for start in range(0, n, BATCH_SIZE):
            chunk = clips[start:start + BATCH_SIZE]
            feats = np.stack([V.extract_feature(os.path.join(REPO_ROOT, rp))
                              for rp, _, _ in chunk], axis=0)
            x = torch.from_numpy(feats).to(device)          # (b,128,432)
            logits = model(x)
            probs = F.softmax(logits, dim=1)
            logits_all[start:start + len(chunk)] = logits.cpu().numpy()
            probs_all[start:start + len(chunk)] = probs.cpu().numpy()

    # ---- derived quantities ----
    file_paths = np.array([c[0] for c in clips])
    source_folders = np.array([c[1] for c in clips])
    local_indices = np.array([(-1 if c[2] is None else c[2]) for c in clips], dtype=int)

    p_bird = probs_all[:, bird_indices].sum(axis=1).astype(np.float32)
    p_non_bird = (1.0 - p_bird).astype(np.float32)
    top1_raw = probs_all.argmax(axis=1)
    pred_prob_max = probs_all.max(axis=1)
    is_true_bird = np.isin(source_folders, BIRD_FOLDERS)
    binary_hard = is_true_bird.astype(int)
    pred_bird_at_0p5 = (p_bird >= 0.5)
    correct_binary = (pred_bird_at_0p5 == is_true_bird)

    top3_idx = np.argsort(-probs_all, axis=1)[:, :3]
    top3_prob = np.take_along_axis(probs_all, top3_idx, axis=1)

    # ---- rows for CSV ----
    rows = []
    for i in range(n):
        rows.append({
            "file_path": file_paths[i],
            "source_folder": source_folders[i],
            "local_dataset_index": int(local_indices[i]),
            "teacher_pred_index_raw": int(top1_raw[i]),
            "teacher_pred_folder_recovered": output_index_to_folder.get(int(top1_raw[i]), "UNKNOWN"),
            "teacher_pred_prob_max": round(float(pred_prob_max[i]), 6),
            "p_bird": round(float(p_bird[i]), 6),
            "p_non_bird": round(float(p_non_bird[i]), 6),
            "binary_soft_label_bird": round(float(p_bird[i]), 6),
            "binary_hard_label": int(binary_hard[i]),
            "is_true_bird": bool(is_true_bird[i]),
            "correct_binary_at_0p5": bool(correct_binary[i]),
            "top1_raw_index": int(top1_raw[i]),
            "top3_raw_indices": "|".join(str(int(j)) for j in top3_idx[i]),
            "top3_probs": "|".join(f"{float(p):.6f}" for p in top3_prob[i]),
        })
    df = pd.DataFrame(rows)

    # ---- metrics ----
    N = n
    n_bird = int(is_true_bird.sum())
    n_nonbird = int((~is_true_bird).sum())
    mean_pbird_bird = float(p_bird[is_true_bird].mean()) if n_bird else None
    mean_pbird_nonbird = float(p_bird[~is_true_bird].mean()) if n_nonbird else None

    TP = int(np.sum(is_true_bird & pred_bird_at_0p5))
    FN = int(np.sum(is_true_bird & ~pred_bird_at_0p5))
    FP = int(np.sum(~is_true_bird & pred_bird_at_0p5))
    TN = int(np.sum(~is_true_bird & ~pred_bird_at_0p5))
    binary_acc = (TP + TN) / N if N else 0.0
    bird_recall = TP / (TP + FN) if (TP + FN) else None
    bird_precision = TP / (TP + FP) if (TP + FP) else None
    nonbird_recall = TN / (TN + FP) if (TN + FP) else None

    # p_bird distribution (deciles)
    bins = np.linspace(0.0, 1.0, 11)
    hist, _ = np.histogram(p_bird, bins=bins)
    p_bird_distribution = {f"[{bins[k]:.1f},{bins[k+1]:.1f})": int(hist[k]) for k in range(10)}

    # uncertain samples: 0.4 <= p_bird <= 0.6
    uncertain_mask = (p_bird >= 0.4) & (p_bird <= 0.6)
    n_uncertain = int(uncertain_mask.sum())
    unc_idx = np.where(uncertain_mask)[0]
    unc_sorted = unc_idx[np.argsort(np.abs(p_bird[unc_idx] - 0.5))]  # closest to 0.5 first
    top_uncertain = [{
        "file_path": file_paths[i], "source_folder": source_folders[i],
        "p_bird": round(float(p_bird[i]), 6),
        "teacher_pred_folder_recovered": output_index_to_folder.get(int(top1_raw[i]), "UNKNOWN"),
        "is_true_bird": bool(is_true_bird[i]),
    } for i in unc_sorted[:20]]

    # ---- safety decision ----
    fail_reasons = []
    if mean_pbird_bird is not None and mean_pbird_nonbird is not None and \
            mean_pbird_bird < mean_pbird_nonbird:
        fail_reasons.append(
            f"mean P(bird) on true-bird ({mean_pbird_bird:.4f}) < on true-non-bird "
            f"({mean_pbird_nonbird:.4f}) -> mapping/collapse looks inverted or broken.")
    if binary_acc < ACC_CAUTION:
        fail_reasons.append(f"binary accuracy {binary_acc:.4f} < {ACC_CAUTION}.")

    if fail_reasons:
        status = "FAIL"
    elif binary_acc >= ACC_PASS:
        status = "PASS"
    else:
        status = "CAUTION"

    # ---- write outputs ----
    npz_path = os.path.join(OUT_DIR, "fsc22_teacher_outputs_27class.npz")
    np.savez_compressed(
        npz_path,
        file_paths=file_paths,
        source_folders=source_folders,
        logits_27=logits_all,
        probs_27=probs_all,
        p_bird=p_bird,
        p_non_bird=p_non_bird,
        binary_hard_label=binary_hard.astype(np.int64),
        bird_indices=np.array(bird_indices, dtype=np.int64),
    )

    csv_path = os.path.join(OUT_DIR, "fsc22_soft_labels_binary.csv")
    df.to_csv(csv_path, index=False)

    summary = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "fail_reasons": fail_reasons,
        "checkpoint": CKPT,
        "device": str(device),
        "torch_version": torch.__version__,
        "num_classes": num_classes,
        "bird_indices": bird_indices,
        "P_bird_formula": "P[12] + P[20]",
        "recovery_decision": decision,
        "ordering": ordering_desc,
        "batch_size": BATCH_SIZE,
        "deterministic": {"shuffle": False, "augmentation": False,
                          "torch_no_grad": True, "model_eval": True,
                          "cudnn_deterministic": True},
        "counts": {"clips": N, "bird_clips": n_bird, "non_bird_clips": n_nonbird},
        "mean_p_bird_true_bird": None if mean_pbird_bird is None else round(mean_pbird_bird, 6),
        "mean_p_bird_true_non_bird": None if mean_pbird_nonbird is None else round(mean_pbird_nonbird, 6),
        "binary_at_0p5": {
            "accuracy": round(binary_acc, 6),
            "bird_recall": None if bird_recall is None else round(bird_recall, 6),
            "bird_precision": None if bird_precision is None else round(bird_precision, 6),
            "non_bird_recall": None if nonbird_recall is None else round(nonbird_recall, 6),
            "confusion": {"TP": TP, "FN": FN, "FP": FP, "TN": TN},
        },
        "p_bird_distribution_deciles": p_bird_distribution,
        "n_uncertain_0p4_0p6": n_uncertain,
        "top20_uncertain": top_uncertain,
        "preprocessing_summary": V.PREPROCESSING_SUMMARY,
        "output_files": [os.path.relpath(p, REPO_ROOT) for p in (npz_path, csv_path)],
    }
    summary_path = os.path.join(OUT_DIR, "soft_label_generation_summary.json")
    with open(summary_path, "w") as fh:
        json.dump(summary, fh, indent=2)

    report_path = os.path.join(OUT_DIR, "soft_label_generation_report.md")
    _write_md(report_path, summary, [os.path.relpath(p, REPO_ROOT) for p in
                                     (npz_path, csv_path, summary_path, report_path)])

    # ---- terminal summary ----
    print("")
    print("=" * 74)
    print("FSC22 TEACHER SOFT-LABEL GENERATION - SUMMARY")
    print("=" * 74)
    print(f"  Checkpoint          : {os.path.relpath(CKPT, REPO_ROOT)}")
    print(f"  Device              : {device}")
    print(f"  Clips               : {N}  (bird={n_bird}, non-bird={n_nonbird})")
    print(f"  Bird indices        : {bird_indices}   P(bird) = P[12] + P[20]")
    print(f"  Mean P(bird) bird   : {mean_pbird_bird:.4f}")
    print(f"  Mean P(bird) nonbird: {mean_pbird_nonbird:.4f}")
    print(f"  Binary acc @0.5     : {binary_acc:.4f}")
    print(f"  Bird recall/prec    : {bird_recall:.4f} / {bird_precision:.4f}")
    print(f"  Non-bird recall     : {nonbird_recall:.4f}")
    print(f"  Uncertain (0.4-0.6) : {n_uncertain}")
    print(f"  DECISION            : {status}")
    if fail_reasons:
        for r in fail_reasons:
            print(f"    - FAIL: {r}")
    print("  Output files:")
    for p in (npz_path, csv_path, summary_path, report_path):
        print(f"    - {os.path.relpath(p, REPO_ROOT)}")
    print("=" * 74)


def _write_md(path, s, out_files):
    b = s["binary_at_0p5"]
    L = []
    A = L.append
    A("# FSC22 Teacher Soft-Label Generation Report")
    A("")
    A("**Deterministic inference only** — no training; dataset/checkpoint read-only.")
    A("")
    A(f"- Date: {s['timestamp']}")
    A(f"- Checkpoint: `{os.path.relpath(s['checkpoint'], REPO_ROOT)}`")
    A(f"- Torch: {s['torch_version']} | Device: {s['device']}")
    A(f"- Classes: {s['num_classes']} | bird_indices: {s['bird_indices']} "
      f"| P(bird) = {s['P_bird_formula']}")
    A(f"- Recovery decision inherited: {s['recovery_decision']}")
    A(f"- Determinism: {s['ordering']}; no augmentation; model.eval(); torch.no_grad(); "
      f"cudnn.deterministic=True")
    A("")
    A(f"## Decision: **{s['status']}**")
    A("")
    if s["fail_reasons"]:
        for r in s["fail_reasons"]:
            A(f"- FAIL: {r}")
    else:
        A("- Soft labels generated successfully; teacher separates bird vs non-bird well.")
        if s["status"] == "CAUTION":
            A("- CAUTION: binary accuracy is between 0.75 and 0.85 — usable but review before KD.")
    A("")
    A("## Counts")
    A("")
    A(f"- Total clips: {s['counts']['clips']}")
    A(f"- Bird clips (23birdchirping + 24wingflapping): {s['counts']['bird_clips']}")
    A(f"- Non-bird clips: {s['counts']['non_bird_clips']}")
    A("")
    A("## Binary bird/non-bird metrics @ threshold 0.5")
    A("")
    A("| metric | value |")
    A("|---|---:|")
    A(f"| Mean P(bird) on true-bird | {s['mean_p_bird_true_bird']} |")
    A(f"| Mean P(bird) on true-non-bird | {s['mean_p_bird_true_non_bird']} |")
    A(f"| Binary accuracy | {b['accuracy']} |")
    A(f"| Bird recall | {b['bird_recall']} |")
    A(f"| Bird precision | {b['bird_precision']} |")
    A(f"| Non-bird recall | {b['non_bird_recall']} |")
    A(f"| Confusion (TP/FN/FP/TN) | {b['confusion']['TP']} / {b['confusion']['FN']} / "
      f"{b['confusion']['FP']} / {b['confusion']['TN']} |")
    A("")
    A("## Distribution of P(bird) (deciles)")
    A("")
    A("| bin | count |")
    A("|---|---:|")
    for k, v in s["p_bird_distribution_deciles"].items():
        A(f"| {k} | {v} |")
    A("")
    A(f"## Uncertain samples (0.4 <= P(bird) <= 0.6): {s['n_uncertain_0p4_0p6']}")
    A("")
    if s["top20_uncertain"]:
        A("Top 20 closest to 0.5:")
        A("")
        A("| file | true folder | P(bird) | teacher pred (recovered) | is_true_bird |")
        A("|---|---|---:|---|:--:|")
        for u in s["top20_uncertain"]:
            A(f"| `{os.path.basename(u['file_path'])}` | {u['source_folder']} | "
              f"{u['p_bird']:.4f} | {u['teacher_pred_folder_recovered']} | {u['is_true_bird']} |")
    else:
        A("None — no samples fell in the [0.4, 0.6] band.")
    A("")
    A("## Output files")
    A("")
    for f in out_files:
        A(f"- `{f}`")
    A("")
    A("## Notes for the KD pipeline")
    A("")
    A("- Use `binary_soft_label_bird` (= P(bird) = P[12]+P[20]) as the distillation target; "
      "`binary_hard_label` is the folder-derived ground truth.")
    A("- The 27-class `logits_27` / `probs_27` in the NPZ allow temperature-scaled KD over the "
      "full teacher distribution if you prefer soft targets richer than the binary collapse.")
    A("- These labels are tied to THIS fixed ordering + batch_size=32. Regenerate identically "
      "(same script) if the dataset changes; do not shuffle or change batch size, because the "
      "Swint_LSTM teacher is batch-order sensitive.")
    A("")
    with open(path, "w") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()

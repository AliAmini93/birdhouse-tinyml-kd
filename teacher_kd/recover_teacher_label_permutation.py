#!/usr/bin/env python3
# ======================================================================================
# recover_teacher_label_permutation.py  --  RECOVERY / INSPECTION ONLY. NO TRAINING.
# --------------------------------------------------------------------------------------
# Context:
#   verify_teacher_labelmap.py found the fold-0 accuracy was only 0.0691 when using the
#   LOCAL os.listdir() label order, but the confusion matrix is a clean permutation
#   (each true folder concentrates on ONE raw output index). That means the checkpoint is
#   fine; only the output-index -> folder mapping differs from this disk's folder order.
#
# This script RECOVERS the checkpoint's true  output_index -> folder  mapping.
#
# It REUSES (imports, does not copy) the model, preprocessing, dataset loading, batch
# size, and checkpoint-loading code from teacher_kd/verify_teacher_labelmap.py.
#
# Writes ONLY into teacher_kd/. Reads dataset + checkpoint; never modifies them.
#
# Reminder about the batch-as-sequence quirk (why the stability test in step 6 exists):
#   swin_t emits (B,768); nn.LSTM treats a 2-D input as an unbatched sequence of length B.
#   Predictions therefore depend on batch size + ordering. We keep batch_size=32 +
#   shuffle=False (matching training) for the count matrix, and separately quantify how
#   much P(bird) moves across batch sizes.
# ======================================================================================

import os
import sys
import json
import glob

# Reuse the verifier module (its top-level environment check runs on import; if a package
# is missing it prints exactly which and exits). We rely on its model/preproc/config.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_teacher_labelmap as V  # noqa: E402  (import after sys.path tweak, by design)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

# Optional: scipy for optimal assignment; greedy fallback if absent.
try:
    from scipy.optimize import linear_sum_assignment
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False

# --------------------------------------------------------------------------------------
# Config (inherited from the verifier where possible)
# --------------------------------------------------------------------------------------
REPO_ROOT = V.REPO_ROOT
OUT_DIR = V.OUT_DIR
DATASET_ROOT = V.DATASET_ROOT
K_FOLDS = V.K_FOLDS
BATCH_SIZE = V.EVAL_BATCH_SIZE            # 32, matches training
CKPT = V.PRIMARY_CKPT                     # recover the selected (dissertation) teacher

BIRD_FOLDERS = ["23birdchirping", "24wingflapping"]
ACC_PASS = 0.75                          # remapped-accuracy PASS threshold
STABILITY_TOL = 0.05                     # max |ΔP(bird)| across batch sizes for "acceptable"

# 30-clip stability probe: these folders must be represented if present.
STABILITY_FOLDERS = ["23birdchirping", "24wingflapping", "05wind",
                     "02rain", "21insect", "22frog", "06silence"]


# --------------------------------------------------------------------------------------
# Dataset: ALL 2025 FSC22 clips, in the same folder/label discovery order as the original,
# each tagged with whether it belongs to the fold-0 eval split (first 15 files per folder).
# --------------------------------------------------------------------------------------
def build_all_samples(dataset_root):
    label_dict = {}
    counter = 0
    samples = []  # (path, local_label, folder, is_fold0)
    for folder in os.listdir(dataset_root):                 # UNSORTED (matches original)
        fp = os.path.join(dataset_root, folder)
        if not os.path.isdir(fp):
            continue
        files = os.listdir(fp)                              # UNSORTED (matches original)
        if folder not in label_dict:
            label_dict[folder] = counter
            counter += 1
        fold_size = len(files) // K_FOLDS                   # KFold(5,shuffle=False) fold-0 = first block
        for k, fn in enumerate(files):
            samples.append((os.path.join(fp, fn), label_dict[folder], folder, k < fold_size))
    return label_dict, samples


def load_model(checkpoint_path, num_classes, device):
    model = V.Swint_LSTM(num_classes=num_classes)
    try:
        state = torch.load(checkpoint_path, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    return model


def run_inference(model, sample_paths, batch_size, device, num_classes):
    """Return softmax probs (N, num_classes) for the given list of file paths, in order."""
    all_probs = np.zeros((len(sample_paths), num_classes), dtype=np.float32)
    with torch.no_grad():
        for start in range(0, len(sample_paths), batch_size):
            chunk = sample_paths[start:start + batch_size]
            feats = np.stack([V.extract_feature(p) for p in chunk], axis=0)
            x = torch.from_numpy(feats).to(device)
            logits = model(x)
            probs = F.softmax(logits, dim=1).cpu().numpy()
            all_probs[start:start + len(chunk)] = probs
    return all_probs


# --------------------------------------------------------------------------------------
# Permutation recovery
# --------------------------------------------------------------------------------------
def recover_mapping(count_matrix):
    """count_matrix[i, j] = # clips of true folder i predicted as raw output j.
    Returns row_to_col: array where row_to_col[i] = assigned raw output index for folder i.
    Uses Hungarian (max total) if scipy available, else greedy.
    """
    n = count_matrix.shape[0]
    if _HAVE_SCIPY:
        # maximize assignment => minimize negative
        row_ind, col_ind = linear_sum_assignment(-count_matrix)
        row_to_col = np.empty(n, dtype=int)
        row_to_col[row_ind] = col_ind
        return row_to_col, "hungarian (scipy.linear_sum_assignment)"
    # greedy fallback: repeatedly take the largest remaining count.
    row_to_col = -np.ones(n, dtype=int)
    used_rows, used_cols = set(), set()
    flat = sorted(((count_matrix[i, j], i, j) for i in range(n) for j in range(n)),
                  key=lambda t: -t[0])
    for _, i, j in flat:
        if i in used_rows or j in used_cols:
            continue
        row_to_col[i] = j
        used_rows.add(i)
        used_cols.add(j)
        if len(used_rows) == n:
            break
    return row_to_col, "greedy (largest-count-first)"


def main():
    import datetime
    os.makedirs(OUT_DIR, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    label_dict, samples = build_all_samples(DATASET_ROOT)
    num_classes = len(label_dict)
    folders_by_local_idx = [None] * num_classes
    for folder, idx in label_dict.items():
        folders_by_local_idx[idx] = folder

    paths = [s[0] for s in samples]
    local_labels = np.array([s[1] for s in samples])
    folders = [s[2] for s in samples]
    is_fold0 = np.array([s[3] for s in samples])

    print(f"Recovering mapping for: {os.path.relpath(CKPT, REPO_ROOT)}")
    print(f"Clips: {len(samples)} total ({int(is_fold0.sum())} fold-0 eval) | "
          f"classes: {num_classes} | batch_size={BATCH_SIZE} | device={device}")

    model = load_model(CKPT, num_classes, device)

    # ---- main inference over ALL clips (batch_size=32, order preserved) ----
    print("Running inference over all clips ...")
    probs = run_inference(model, paths, BATCH_SIZE, device, num_classes)
    raw_pred = probs.argmax(axis=1)

    # ---- count matrix: rows = true folder (local idx), cols = raw output idx ----
    C = np.zeros((num_classes, num_classes), dtype=int)
    for lab, pred in zip(local_labels, raw_pred):
        C[lab, pred] += 1

    # ---- recover output_index -> folder ----
    row_to_col, method = recover_mapping(C.astype(float))
    # row_to_col[i] = raw output index assigned to true folder i  => that output means folder i
    output_index_to_folder = {}
    folder_to_output_index = {}
    for i in range(num_classes):
        j = int(row_to_col[i])
        output_index_to_folder[j] = folders_by_local_idx[i]
        folder_to_output_index[folders_by_local_idx[i]] = j

    # ---- accuracies (raw local map vs recovered map) ----
    def acc(mask):
        if mask.sum() == 0:
            return None
        # raw: does raw_pred equal the LOCAL index of the true folder?
        raw_ok = (raw_pred[mask] == local_labels[mask]).mean()
        # remapped: does the recovered folder for raw_pred match the true folder?
        remap_ok = np.mean([output_index_to_folder.get(int(p)) == f
                            for p, f in zip(raw_pred[mask], np.array(folders)[mask])])
        return float(raw_ok), float(remap_ok)

    raw_all, remap_all = acc(np.ones(len(samples), dtype=bool))
    fold0_res = acc(is_fold0)
    raw_fold0, remap_fold0 = fold0_res

    # ---- recovered bird indices ----
    bird_out_idx = {f: folder_to_output_index[f] for f in BIRD_FOLDERS if f in folder_to_output_index}
    recommended_bird_indices = sorted(bird_out_idx.values())
    p_bird_formula = " + ".join(f"P[{i}]" for i in recommended_bird_indices)

    # ---- top-3 raw output indices per true folder ----
    top3 = {}
    for i in range(num_classes):
        order = np.argsort(-C[i])[:3]
        top3[folders_by_local_idx[i]] = [
            {"out_index": int(j), "count": int(C[i, j]),
             "recovered_folder": output_index_to_folder.get(int(j))}
            for j in order
        ]

    # ---- ambiguity / contested-column detection ----
    ambiguities = []
    CONTESTED = 5  # >=5 of 15(+) votes from two different folders on the same raw column
    for j in range(num_classes):
        claimants = [(folders_by_local_idx[i], int(C[i, j])) for i in range(num_classes)
                     if C[i, j] >= CONTESTED]
        if len(claimants) > 1:
            ambiguities.append({"out_index": j, "claimants": sorted(claimants, key=lambda t: -t[1])})
    # also flag any folder whose assigned column has a very weak count (weak recovery)
    weak = []
    for i in range(num_classes):
        j = int(row_to_col[i])
        n_i = int(C[i].sum())
        if n_i and C[i, j] < 0.5 * n_i:
            weak.append({"folder": folders_by_local_idx[i], "assigned_out_index": j,
                         "count": int(C[i, j]), "n": n_i,
                         "argmax_out_index": int(C[i].argmax()),
                         "argmax_count": int(C[i].max())})

    # ---- P(bird) sanity on all clips using recovered indices ----
    p_bird_all = probs[:, recommended_bird_indices].sum(axis=1) if recommended_bird_indices else np.zeros(len(samples))
    true_bird_mask = np.isin(local_labels, [label_dict[f] for f in BIRD_FOLDERS if f in label_dict])
    mean_pbird_bird = float(p_bird_all[true_bird_mask].mean()) if true_bird_mask.any() else None
    mean_pbird_nonbird = float(p_bird_all[~true_bird_mask].mean()) if (~true_bird_mask).any() else None

    # ------------------------------------------------------------------------------
    # Stability test: 30 clips, batch_size 1 / 8 / 32, compare P(bird)
    # ------------------------------------------------------------------------------
    stab_paths, stab_folders = [], []
    # gather up to a fixed per-folder quota to reach ~30 clips, biased to bird folders
    quota = {f: (5 if f in BIRD_FOLDERS else 4) for f in STABILITY_FOLDERS}
    by_folder = {}
    for p, lab, f, _ in samples:
        by_folder.setdefault(f, []).append(p)
    for f in STABILITY_FOLDERS:
        if f in by_folder:
            for p in by_folder[f][:quota[f]]:
                stab_paths.append(p)
                stab_folders.append(f)
    stability = {"n_clips": len(stab_paths), "folders": STABILITY_FOLDERS,
                 "bird_indices": recommended_bird_indices}
    pbird_by_bs = {}
    for bs in (1, 8, 32):
        pr = run_inference(model, stab_paths, bs, device, num_classes)
        pbird_by_bs[bs] = pr[:, recommended_bird_indices].sum(axis=1) if recommended_bird_indices else np.zeros(len(stab_paths))
    ref = pbird_by_bs[32]
    diffs = {}
    for bs in (1, 8):
        d = np.abs(pbird_by_bs[bs] - ref)
        diffs[f"bs{bs}_vs_bs32"] = {"mean_abs_diff": float(d.mean()), "max_abs_diff": float(d.max())}
    d18 = np.abs(pbird_by_bs[1] - pbird_by_bs[8])
    diffs["bs1_vs_bs8"] = {"mean_abs_diff": float(d18.mean()), "max_abs_diff": float(d18.max())}
    overall_max_diff = max(v["max_abs_diff"] for v in diffs.values())
    overall_mean_diff = float(np.mean([v["mean_abs_diff"] for v in diffs.values()]))
    # Data-driven batching recommendation (which batch size, if any, is the outlier).
    bs8_stable = diffs["bs8_vs_bs32"]["max_abs_diff"] <= STABILITY_TOL
    bs1_outlier = diffs["bs1_vs_bs32"]["max_abs_diff"] > STABILITY_TOL
    if bs8_stable and bs1_outlier:
        batching_reco = (
            "P(bird) is stable for batch_size >= 8 (bs8-vs-bs32 max|Δ|="
            f"{diffs['bs8_vs_bs32']['max_abs_diff']:.3f}), but batch_size=1 is an "
            "out-of-distribution OUTLIER (bs1-vs-bs32 max|Δ|="
            f"{diffs['bs1_vs_bs32']['max_abs_diff']:.3f}) because the LSTM was trained on "
            "length-32 batch-sequences. RECOMMENDATION: generate teacher soft labels at "
            "batch_size=32 (matches training) with a fixed clip order; do NOT use batch_size=1.")
    elif not bs8_stable:
        batching_reco = (
            "P(bird) varies even between batch_size 8 and 32; soft labels are batch-order "
            "sensitive at every size. Pin one exact batch size AND clip ordering when "
            "generating labels and reuse it identically for teacher and any re-runs.")
    else:
        batching_reco = "P(bird) is stable across all tested batch sizes; batching choice is safe."
    stability.update({"diffs": diffs, "overall_max_abs_diff": overall_max_diff,
                      "overall_mean_abs_diff": overall_mean_diff,
                      "acceptable": overall_max_diff <= STABILITY_TOL,
                      "batch_size_stable_ge_8": bool(bs8_stable),
                      "batch_size_1_is_outlier": bool(bs1_outlier),
                      "recommendation": batching_reco,
                      "tolerance": STABILITY_TOL})

    # ------------------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------------------
    remap_ref = remap_fold0 if remap_fold0 is not None else remap_all
    if remap_ref is not None and remap_ref > ACC_PASS and stability["acceptable"]:
        decision = "PASS"
        decision_note = ("Recovered permutation restores high accuracy and P(bird) is stable "
                         "across batch sizes. Use the recovered mapping and recommended bird indices.")
    elif remap_ref is not None and remap_ref > ACC_PASS:
        decision = "CAUTION"
        decision_note = ("Recovered permutation restores high accuracy, BUT P(bird) varies with "
                         "batch size (LSTM consumes the batch as a sequence). " + batching_reco)
    else:
        decision = "FAIL"
        decision_note = ("Remapped accuracy is still low; a simple permutation does not explain the "
                         "behavior. Investigate checkpoint/preprocessing before using as Teacher. Do NOT retrain automatically.")

    # ------------------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------------------
    # raw confusion CSV (rows true folder, cols raw output index 0..26)
    raw_cols = [f"out_{j}" for j in range(num_classes)]
    df_raw = pd.DataFrame(C, index=folders_by_local_idx, columns=raw_cols)
    df_raw.index.name = "true_folder"
    raw_csv = os.path.join(OUT_DIR, "recovered_confusion_raw.csv")
    df_raw.to_csv(raw_csv)

    # remapped confusion CSV (cols relabeled to recovered folder, reordered to diagonal)
    col_folder = [output_index_to_folder.get(j, f"UNMAPPED_out_{j}") for j in range(num_classes)]
    df_remap = pd.DataFrame(C, index=folders_by_local_idx, columns=col_folder)
    # reorder columns to match row order where possible (diagonal-dominant view)
    ordered_cols = [f for f in folders_by_local_idx if f in df_remap.columns]
    ordered_cols += [c for c in df_remap.columns if c not in ordered_cols]
    df_remap = df_remap[ordered_cols]
    df_remap.index.name = "true_folder\\recovered_pred_folder"
    remap_csv = os.path.join(OUT_DIR, "recovered_confusion_remapped.csv")
    df_remap.to_csv(remap_csv)

    # recovered label map JSON
    label_map_json = {
        "checkpoint": CKPT,
        "method": method,
        "num_classes": num_classes,
        "output_index_to_folder": {str(j): output_index_to_folder.get(j) for j in range(num_classes)},
        "folder_to_output_index": dict(sorted(folder_to_output_index.items(), key=lambda kv: kv[1])),
        "bird_folders_output_index": bird_out_idx,
        "recommended_bird_indices": recommended_bird_indices,
        "P_bird_formula": p_bird_formula,
        "P_non_bird_formula": f"1 - ({p_bird_formula})",
        "local_dataset_label_map": dict(sorted(label_dict.items(), key=lambda kv: kv[1])),
        "accuracy": {
            "raw_all_clips": round(raw_all, 4),
            "remapped_all_clips": round(remap_all, 4),
            "raw_fold0_eval": None if raw_fold0 is None else round(raw_fold0, 4),
            "remapped_fold0_eval": None if remap_fold0 is None else round(remap_fold0, 4),
        },
        "mean_p_bird_on_true_bird": None if mean_pbird_bird is None else round(mean_pbird_bird, 4),
        "mean_p_bird_on_true_nonbird": None if mean_pbird_nonbird is None else round(mean_pbird_nonbird, 4),
        "ambiguous_output_indices": ambiguities,
        "weak_assignments": weak,
        "batch_size_stability": stability,
        "verification_status": decision,
        "preprocessing_summary": V.PREPROCESSING_SUMMARY,
    }
    map_path = os.path.join(OUT_DIR, "recovered_teacher_label_map.json")
    with open(map_path, "w") as fh:
        json.dump(label_map_json, fh, indent=2)

    # markdown report
    md_path = os.path.join(OUT_DIR, "recovered_permutation_report.md")
    _write_md(md_path, dict(
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        checkpoint=os.path.relpath(CKPT, REPO_ROOT), method=method, device=str(device),
        torch_version=torch.__version__, num_classes=num_classes,
        n_all=len(samples), n_fold0=int(is_fold0.sum()), batch_size=BATCH_SIZE,
        raw_all=raw_all, remap_all=remap_all, raw_fold0=raw_fold0, remap_fold0=remap_fold0,
        bird_out_idx=bird_out_idx, recommended_bird_indices=recommended_bird_indices,
        p_bird_formula=p_bird_formula, mean_pbird_bird=mean_pbird_bird,
        mean_pbird_nonbird=mean_pbird_nonbird, top3=top3, ambiguities=ambiguities, weak=weak,
        stability=stability, decision=decision, decision_note=decision_note,
        folders_by_local_idx=folders_by_local_idx, folder_to_output_index=folder_to_output_index,
        out_files=[os.path.relpath(p, REPO_ROOT) for p in
                   (map_path, md_path, raw_csv, remap_csv)],
    ))

    # ---- terminal summary ----
    print("")
    print("=" * 72)
    print("TEACHER LABEL-PERMUTATION RECOVERY - SUMMARY")
    print("=" * 72)
    print(f"  Checkpoint         : {os.path.relpath(CKPT, REPO_ROOT)}")
    print(f"  Method             : {method}")
    print(f"  Raw accuracy       : all={raw_all:.4f}  fold0={raw_fold0:.4f}  (local os.listdir order)")
    print(f"  Remapped accuracy  : all={remap_all:.4f}  fold0={remap_fold0:.4f}  (recovered mapping)")
    print(f"  23birdchirping     -> output index {bird_out_idx.get('23birdchirping')}")
    print(f"  24wingflapping     -> output index {bird_out_idx.get('24wingflapping')}")
    print(f"  Recommended bird   : {recommended_bird_indices}   P(bird) = {p_bird_formula}")
    print(f"  Stability P(bird)  : mean|Δ|={stability['overall_mean_abs_diff']:.4f} "
          f"max|Δ|={stability['overall_max_abs_diff']:.4f} "
          f"(tol {STABILITY_TOL}) -> {'ACCEPTABLE' if stability['acceptable'] else 'POOR'}")
    if ambiguities:
        print(f"  Ambiguous columns  : {[a['out_index'] for a in ambiguities]} (see report)")
    print(f"  DECISION           : {decision}")
    print("  Output files:")
    for p in (map_path, md_path, raw_csv, remap_csv):
        print(f"    - {os.path.relpath(p, REPO_ROOT)}")
    print("=" * 72)


def _write_md(path, d):
    L = []
    A = L.append
    A("# Teacher Label-Permutation Recovery Report")
    A("")
    A("**Recovery / inspection only** — no training; existing files only read.")
    A("")
    A(f"- Date: {d['timestamp']}")
    A(f"- Checkpoint: `{d['checkpoint']}`")
    A(f"- Torch: {d['torch_version']} | Device: {d['device']} | Assignment: {d['method']}")
    A(f"- Clips: {d['n_all']} total ({d['n_fold0']} fold-0 eval) | classes: {d['num_classes']} | "
      f"batch_size={d['batch_size']}")
    A("")
    A(f"## Decision: **{d['decision']}**")
    A("")
    A(d["decision_note"])
    A("")
    A("## Accuracy: local order vs recovered permutation")
    A("")
    A("| set | raw (local os.listdir order) | remapped (recovered) |")
    A("|-----|------:|------:|")
    A(f"| all clips ({d['n_all']}) | {d['raw_all']:.4f} | {d['remap_all']:.4f} |")
    A(f"| fold-0 eval ({d['n_fold0']}) | {d['raw_fold0']:.4f} | {d['remap_fold0']:.4f} |")
    A("")
    A("The raw column reproduces the ~0.069 failure; the remapped column is the true teacher "
      "quality once the output indices are relabeled. (All-clips is higher than fold-0 because "
      "60/75 clips per class were in training.)")
    A("")
    A("## Bird classes (for binary collapse)")
    A("")
    A(f"- `23birdchirping` -> **output index {d['bird_out_idx'].get('23birdchirping')}**")
    A(f"- `24wingflapping` -> **output index {d['bird_out_idx'].get('24wingflapping')}**")
    A(f"- **Recommended bird_indices = {d['recommended_bird_indices']}**")
    A(f"- **P(bird) = {d['p_bird_formula']}** ; P(non_bird) = 1 - P(bird)")
    A(f"- Mean P(bird) on true-bird clips: {None if d['mean_pbird_bird'] is None else round(d['mean_pbird_bird'],4)} "
      f"| on true-non-bird clips: {None if d['mean_pbird_nonbird'] is None else round(d['mean_pbird_nonbird'],4)}")
    A("")
    note = ("**Yes — P(bird) should be P[12]+P[20]**" if d['recommended_bird_indices'] == [12, 20]
            else f"**P(bird) should be {d['p_bird_formula']}** (NOT the local-order P[2]+P[6])")
    A(note + ". The local os.listdir indices (2, 6) are wrong for this checkpoint.")
    A("")
    A("## Batch-size stability of P(bird)  (LSTM treats batch as sequence)")
    A("")
    s = d["stability"]
    A(f"- Probe: {s['n_clips']} clips from {', '.join(s['folders'])}")
    A(f"- bird indices used: {s['bird_indices']}")
    A("")
    A("| comparison | mean |Δ P(bird)| | max |Δ P(bird)| |")
    A("|-----|------:|------:|")
    for k, v in s["diffs"].items():
        A(f"| {k} | {v['mean_abs_diff']:.4f} | {v['max_abs_diff']:.4f} |")
    A("")
    A(f"- Overall: mean|Δ|={s['overall_mean_abs_diff']:.4f}, max|Δ|={s['overall_max_abs_diff']:.4f} "
      f"(tolerance {s['tolerance']}) -> **{'ACCEPTABLE' if s['acceptable'] else 'POOR'}**")
    A("")
    if not s["acceptable"]:
        A("> " + s.get("recommendation", "P(bird) is batch-order sensitive; pin a fixed batching scheme."))
        A("")
    if d["ambiguities"]:
        A("## Ambiguity warnings")
        A("")
        for a in d["ambiguities"]:
            claim = ", ".join(f"{f} ({c})" for f, c in a["claimants"])
            A(f"- Output index **{a['out_index']}** contested by: {claim}")
        if d["weak"]:
            for w in d["weak"]:
                A(f"  - `{w['folder']}` was forced onto out {w['assigned_out_index']} "
                  f"(count {w['count']}/{w['n']}); its argmax was out {w['argmax_out_index']} "
                  f"(count {w['argmax_count']}). Verify this pair manually.")
        A("")
        A("These do not affect the bird indices, but double-check the contested non-bird classes if "
          "they matter downstream.")
        A("")
    else:
        A("## Ambiguity warnings")
        A("")
        A("None — every output index maps cleanly to a single folder.")
        A("")
    A("## Recovered mapping (output_index -> folder)")
    A("")
    A("| out idx | folder | | out idx | folder |")
    A("|--:|----|--|--:|----|")
    inv = {v: k for k, v in d["folder_to_output_index"].items()}
    half = (d["num_classes"] + 1) // 2
    for r in range(half):
        left = f"| {r} | {inv.get(r,'?')} |"
        r2 = r + half
        right = f" {r2} | {inv.get(r2,'?')} |" if r2 < d["num_classes"] else " | |"
        A(left + " |" + right)
    A("")
    A("## Top-3 raw output indices per true folder")
    A("")
    A("| true folder | 1st (count) | 2nd (count) | 3rd (count) |")
    A("|----|----|----|----|")
    for folder in d["folders_by_local_idx"]:
        t = d["top3"][folder]
        cells = " | ".join(f"out {e['out_index']} ({e['count']})" for e in t)
        A(f"| {folder} | {cells} |")
    A("")
    A("## Output files")
    A("")
    for f in d["out_files"]:
        A(f"- `{f}`")
    A("")
    with open(path, "w") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()

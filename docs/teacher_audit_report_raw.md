# Teacher Audit Report — FSC22 Dissertation Code for Bird/Non-Bird KD

**Audit date:** 2026-07-09
**Repository:** `/media/armin/External/AhmadWorks/audioclassification`
**Method:** Static inspection only (no training, no model execution, no source modification).

---

## 1. Executive Summary

**Verdict: B — Usable after small adaptation (one short inference script + one cheap verification run).**

- The best dissertation model — **mel-spectrogram + SWinT-BiLSTM (`Swint_LSTM`)** — exists as **trained PyTorch checkpoints**, 5 per k-fold run, in `output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/` (205 MB each, `state_dict` format).
- Recorded performance (from `output_for_dissertation/fsc22/excel_melspectrogram/tne_result.xlsx`): **mean 5-fold accuracy 83.16 %, weighted F1 0.8247** — the best single-feature FSC22 model in the repo, matching the dissertation's claim.
- Checkpoint contents were verified statically (pickle disassembly, no torch load): keys match the `Swint_LSTM` class exactly; final layer `fc.0.weight` has shape **[27, 1536]** → 27 classes.
- Preprocessing is fully recoverable from the training script and is simple: `librosa.load(sr=None)` (44.1 kHz, mono), `librosa.feature.melspectrogram` with **library defaults** (n_fft=2048, hop=512, n_mels=128, power mel — **no dB scaling, no normalization**), tile-padded to **128×432**, 1→3 channel repeat inside the model.
- Labels are **folder-order based** (`os.listdir`, *not* sorted, never saved to disk). Predicted indices on this machine: **bird-chirping = 2, wing-flapping = 6**. This is the single real risk (see §6/§8) and must be confirmed with one cheap inference run before distillation.
- There is **no standalone inference script** anywhere in `Codes/` (no `torch.load`/`load_state_dict` calls). All scripts are combined train+eval. A ~50-line teacher wrapper must be written (reusing the existing `fsc22Dataset` and `Swint_LSTM` classes verbatim).
- The project venv is **broken** (symlinks to a missing `/usr/bin/python3.13`), but its `site-packages` contains torch 2.9.0 / torchvision / librosa 0.11 for cp313. Installing `python3.13` restores it. GPU: RTX 5090 (32 GB) — ample for teacher inference.
- **No retraining is needed.**

---

## 2. Repository Structure Overview

```
audioclassification/
├── call_codes*.py, here_all_codies.py   # launcher scripts (subprocess-run training files)
├── testcuda.py                          # CUDA smoke test
├── Codes/
│   ├── torch/                           # dissertation training scripts, one dir per feature×dataset
│   │   ├── melspectrogram_fsc22/        #   ← code that produced the dissertation FSC22 mel models
│   │   │   ├── swintlstm.py  swintgru.py  swint.py
│   │   │   ├── efficientlstm.py  efficientgru.py  efficientnet.py
│   │   ├── mfcc_fsc22/, chroma_stft_fsc22/, stft_fsc22/, melspectrogram_cstft_fsc22/, ...
│   │   └── (same pattern for esc50 / mimii / feature-fusion variants)
│   └── revise/                          # journal-revision variants (write to output_for_revision)
│       └── fsc22_melspectrogram/ ...    #   same architectures, pretrained/original comparison
├── Dataset/
│   ├── fsc22/                           # 27 class folders × 75 WAVs (2,025 clips) ← FSC22
│   ├── esc50/                           # out of scope
│   └── MIMII/                           # out of scope
├── output_for_dissertation/             # ★ canonical dissertation outputs (models/excel/images/logs)
│   └── fsc22/{model,excel_*,image}/...  #   (tree copied onto this disk 2026-07-08, root-owned)
├── output_for_revision/                 # revision-run outputs incl. fusion features (Nov 2025)
├── output_p_10/                         # earlier July-2025 runs (locally trained, armin-owned)
├── output_p_10_lr_6/                    # May-2025 runs (stft feature)
├── output_side_project/                 # ViT / MaxViT side experiments (Aug 2025)
└── venv/                                # BROKEN: symlinks → missing /usr/bin/python3.13
```

There is no git history, no README, no requirements file. Everything is script-per-experiment; each training script is self-contained (dataset class + model class + train/eval loop + plotting + Excel logging + checkpoint save).

---

## 3. Candidate Teacher Models Found

All FSC22 mel-spectrogram candidates live in `Codes/torch/melspectrogram_fsc22/` (framework: **PyTorch**, backbones from **torchvision.models** — `timm` is not used). All take the same input: mel-spectrogram 128×432, 1-channel repeated to 3 channels inside `forward()`. `num_classes` is derived at runtime from the number of dataset folders (27).

| Script | Class | Architecture | FSC22 mel 5-fold mean acc | Checkpoints? |
|---|---|---|---|---|
| `swintlstm.py` | `Swint_LSTM` | torchvision `swin_t` (ImageNet `DEFAULT` weights), head→Identity, **2-layer bidirectional LSTM** (in=768, hidden=768, dropout 0.2), Linear(1536→27) | **0.8316** ★ best | ✅ 5 folds |
| `swintgru.py` | `Swint_GRU` | same but **bidirectional GRU** | 0.7748 | ✅ 5 folds |
| `swint.py` | `Swint` | plain `swin_t`, replaced head | 0.7575 | ✅ 5 folds |
| `efficientnet.py` | `EfficientNet` | `efficientnet_v2_m` | 0.4836 | ✅ 7 files |
| `efficientlstm.py` | `EfficientLSTM` | `efficientnet_v2_m` + BiLSTM | (no mel-only dissertation run; MFCC run: 0.7511) | mel-only: only in revision "pretrained/original" tree |
| `efficientgru.py` | `EfficientGRU` | `efficientnet_v2_m` + BiGRU | (MFCC run: 0.5832) | same as above |

Other feature variants for FSC22 (all with Swint_LSTM sheets in Excel): MFCC 0.7057, chroma-STFT 0.5042, mel+cstft fusion 0.8168, mel+MFCC fusion 0.8252 — **all below mel-only Swint_LSTM (0.8316)**. A "hybrid_all" EfficientLSTM run reached 0.8395, but it uses a fused-feature input pipeline that would complicate the student and is not the dissertation's headline model.

**Selected Teacher: `Swint_LSTM` + mel-spectrogram** — exactly the requested first-choice model (SWinT-BiLSTM). Note the LSTM/GRU are `bidirectional=True`, so "Swint_LSTM" in filenames *is* the SWinT-BiLSTM of the dissertation.

Side project models (ViT, MaxViT, mel, FSC22, Aug 2025) also have checkpoints in `output_side_project/` but underperform expectations for this task and were not the dissertation focus.

---

## 4. Checkpoints / Weights Found

**Trained weights DO exist.** All are `torch.save(model.state_dict())` → `.pth` zip archives (no optimizer state, no label map, no config inside).

### Primary teacher candidates (canonical, matches dissertation Excel)

`output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/` — 5 folds × 205,019,787 bytes:

| File | Fold | Excel accuracy |
|---|---|---|
| `2025_07_21_16_06_03_Swint_LSTM_0.pth` | 0 | 0.8370 |
| `2025_07_21_16_35_14_Swint_LSTM_1.pth` | 1 | 0.8296 |
| `2025_07_21_17_00_24_Swint_LSTM_2.pth` | 2 | 0.8321 |
| `2025_07_21_17_23_53_Swint_LSTM_3.pth` | 3 | 0.8346 |
| `2025_07_21_17_49_00_Swint_LSTM_4.pth` | 4 | 0.8247 |

Static verification (pickle disassembly of fold 0, no execution): 381 state-dict keys; `swint.features.*` (torchvision swin_t layout), `lstm.weight_ih_l0 … lstm.*_l1_reverse` (2 layers × 2 directions), `fc.0.weight` = **[27, 1536]**, `fc.0.bias` = [27]. File size also cross-checks: FSC22 (27-class) Swint_LSTM = 205,019,787 B vs ESC-50 (50-class) = 205,161,163 B; the ~141 KB delta ≈ 23 extra rows × 1536 floats.

### Secondary / backup FSC22 mel checkpoints

- `output_p_10/fsc22/model/melspectrogram/Swint_LSTM/` — 5 folds, trained **on this machine** 2025-07-11 (armin-owned, original mtimes). Excel mean acc 0.8202. Useful as a fallback whose label order is guaranteed tied to this disk's `Dataset/fsc22`.
- `output_for_revision/fsc22/model/pretrained/original/melspectrogram/{Swint_LSTM, Swint_GRU, Swint, EfficientNet, EfficientLSTM, EfficientGRU}/` — Sept 2025 revision runs, 5 folds each (includes the only mel-only **EfficientLSTM/EfficientGRU** FSC22 weights).
- `output_for_revision/fsc22/model/melspectrogram_mfcc/...` and `melspectrogram_cstft/...` — fusion-feature models (different input pipeline; not recommended).
- `output_for_dissertation/fsc22/model/melspectrogram/{Swint, Swint_GRU, EfficientNet}/` — the lower-scoring dissertation siblings.
- `output_p_10_lr_6/fsc22/model/stft/{Swint_LSTM, Swint_GRU}/` — STFT-feature models (May 2025), not mel.

**Matching load code:** none exists in the repo (no `torch.load` anywhere in `Codes/`), but the `Swint_LSTM` class in `Codes/torch/melspectrogram_fsc22/swintlstm.py` reconstructs the architecture exactly; `model.load_state_dict(torch.load(pth))` is all that is missing.

**Caveat:** `save_model()` runs once *after early stopping*, i.e. the saved weights are from the **final epoch, not the best-eval epoch** (log shows final-epoch accuracy ≈ 0.5–1 pt below the best epoch). Still an entirely serviceable teacher.

---

## 5. FSC22 Preprocessing Details

From `fsc22Dataset.__getitem__` in `Codes/torch/melspectrogram_fsc22/swintlstm.py` (identical across sibling scripts):

| Property | Value |
|---|---|
| Source audio | FSC22 WAVs: **5.00 s, 44,100 Hz, 16-bit stereo**, 75 per class (verified from RIFF headers) |
| Loading | `librosa.load(path, sr=None)` → **native 44.1 kHz kept** (no resampling), **converted to mono** (librosa default `mono=True`) |
| Windowing | **Whole 5-s clip used directly** — no dataset-level sliding window; only the STFT's internal framing |
| Feature | `librosa.feature.melspectrogram(y=y, sr=sr)` with **all defaults**: n_fft=2048, hop_length=512, win=2048 (Hann), **n_mels=128**, fmax=sr/2, **power=2.0 (power mel)** |
| Scaling | **None.** No `power_to_db`/log, no mean-std normalization, no min-max. Raw power-mel values go into the network. |
| Length handling | 5 s @44.1 kHz → 431 frames; `max_length=432`: longer → truncate, shorter → **tile (concatenate with itself) then truncate** → **128 × 432** |
| Tensor to model | `(batch, 128, 432)` float32; inside `forward()`: `unsqueeze(1)` then `.repeat(1,3,1,1)` → **(B, 3, 128, 432)** for the ImageNet backbone. **No resize to 224×224, no ImageNet mean/std normalization.** |
| Train-only augmentation | occasional Gaussian noise injection (irrelevant for teacher inference) |

Any distillation dataset fed to the teacher must reproduce exactly: 44.1 kHz mono, default librosa power-mel (librosa 0.11), tile-pad to 432 frames, **no dB conversion**. (If your TinyML student uses log-mel, apply log only on the student side, or regenerate teacher features accordingly — the teacher was trained on linear power mel.)

---

## 6. FSC22 Class List and Bird-Class Indices

**No metadata CSV / label map file exists.** Labels come from **folder names**, and — critically — indices are assigned in **`os.listdir()` order (unsorted, filesystem/readdir order)** by `fsc22Dataset._get_data()`. The mapping is never saved.

Current readdir order of `Dataset/fsc22` on this ext4 disk (directory unmodified since 2025-04-29, i.e. before all training runs) gives:

| Idx | Folder | Idx | Folder | Idx | Folder |
|---|---|---|---|---|---|
| 0 | 10axe | 9 | 17whistling | 18 | 03thunderstorm |
| 1 | 22frog | 10 | 06silence | 19 | 02rain |
| **2** | **23birdchirping** | 11 | 15gunshot | 20 | 01fire |
| 3 | 25lion | 12 | 13handsaw | 21 | 07treefalling |
| 4 | 18speaking | 13 | 08helicopter | 22 | 26wolfhowl |
| 5 | 19footsteps | 14 | 12generator | 23 | 21insect |
| **6** | **24wingflapping** | 15 | 16woodchop | 24 | 09vehicleengine |
| 7 | 05wind | 16 | 14firework | 25 | 27squirrel |
| 8 | 04waterdrops | 17 | 11chainsaw | 26 | 20clapping |

- **bird-chirping → index 2**, **bird-wing-flapping → index 6** (pending the verification in §8).
- 27 classes total; `num_classes` is computed at runtime as `len(label_dict)` = number of folders.
- Dataset root expected by code: relative path `Dataset/fsc22` (scripts must run from the repo root).
- Split: **5-fold `KFold` (no shuffle) applied per class folder**; fold index is baked into each checkpoint's filename suffix (`_0`…`_4`). No separate held-out test set; the train split is duplicated ×2 as implicit augmentation.

**Confidence assessment on the order:** ext4 readdir order is hash-based but stable while a directory is unmodified; `Dataset/fsc22` has not been touched since April 2025 and the July-11 `output_p_10` run was demonstrably trained on this machine against it. However, the `output_for_dissertation` tree was **copied onto this disk on 2026-07-08 (root-owned)** — if that July-21 training ran on a *different* machine with a *different copy* of the dataset, its readdir order (and hence class indices) could differ. This is the one thing that must be verified empirically (cheap — see §8/§10).

---

## 7. Inference / Evaluation Scripts Found

**None standalone.** Every script in `Codes/` is a monolithic train+eval program:

- Evaluation logic exists inside each script (`eval_model()`: computes accuracy/precision/recall/F1, `plot_confusion_matrix`, `plot_roc_auc` with **softmax probabilities** via `nn.functional.softmax(output, dim=1)`), but it is only reachable through the full training loop.
- `grep -r "torch.load\|load_state_dict" Codes/` → **zero hits**. No script loads a saved checkpoint.
- Launcher scripts (`call_codes*.py`, `here_all_codies.py`) merely subprocess-run the training files.

Therefore a small **teacher inference wrapper** must be written (see §8). It can copy `fsc22Dataset` and `Swint_LSTM` verbatim from `Codes/torch/melspectrogram_fsc22/swintlstm.py`; the only new code is `load_state_dict` + a forward pass. Logits are available (pre-softmax `fc` output), so both softened logits (for KD with temperature) and softmax probabilities are obtainable.

**Environment note:** the repo `venv` is broken — its interpreter symlinks point to `/usr/bin/python3.13`, which is not installed (system python is 3.12.3). The venv `site-packages` already contains cp313 builds of torch 2.9.0, torchvision, librosa 0.11, numpy 2.3, openpyxl. Fix = `apt install python3.13` (restores the venv as-is) or build a fresh venv for 3.12 and reinstall the four packages. GPU is an RTX 5090 (32 GB); torch 2.9 supports it. CPU-only inference would also suffice for verification.

---

## 8. Binary Bird / Non-Bird Collapse Plan

**Feasible.** Sketch of the wrapper (new file, e.g. `teacher_infer.py`; do not modify existing sources):

```python
# reuse fsc22Dataset + Swint_LSTM copied from Codes/torch/melspectrogram_fsc22/swintlstm.py
import torch, torch.nn.functional as F

BIRD_IDX = [2, 6]        # 23birdchirping, 24wingflapping  ← verify first (step 2 in §10)

model = Swint_LSTM(num_classes=27)
model.load_state_dict(torch.load(
    'output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/2025_07_21_16_06_03_Swint_LSTM_0.pth',
    map_location=device))
model.eval()

with torch.no_grad():
    logits = model(feature)                 # (B, 27) — raw logits, usable for KD w/ temperature
    probs  = F.softmax(logits, dim=1)       # (B, 27)
    p_bird = probs[:, BIRD_IDX].sum(dim=1)  # P(bird) = P(chirping) + P(wingflapping)
    # P(non-bird) = 1 - p_bird
```

- **Where:** new standalone script at repo root (or a `distillation/` folder); nothing in `Codes/` needs modification.
- **Logits vs probabilities:** both available; for knowledge distillation prefer temperature-softened logits over the 27 classes, then collapse; use `p_bird` for the binary target/label.
- **Risks:**
  1. **Class-index order** (§6) — must be verified once empirically before trusting `[2, 6]`. Verification: rebuild `fsc22Dataset(train=False)` for a fold, run the checkpoint over it, and check per-class accuracy; if the mapping is right, per-class accuracy will be uniformly ~0.8; if it were permuted, accuracy would collapse to ~0.04. Additionally spot-check that clips from `23birdchirping` argmax to 2.
  2. Checkpoints are final-epoch, not best-epoch (≈0.5–1 pt accuracy cost).
  3. Teacher input is *linear power mel* (no dB) — the student pipeline must feed the teacher its native format even if the student itself uses log-mel.
  4. Each fold's checkpoint saw 80 % of FSC22 in training; when generating soft labels **on FSC22 itself**, use fold *k*'s model only on fold *k*'s eval slice (or ensemble all five) to avoid teaching from memorized examples.

---

## 9. Final Decision

**B — Usable after small adaptation.**

| Requirement | Status |
|---|---|
| Trained weights exist | ✅ 5-fold SWinT-BiLSTM mel FSC22 checkpoints, statically verified (27-class head) |
| Label map exists | ⚠️ Recoverable (folder/readdir order, bird=2, wingflap=6) but never persisted — needs one-time empirical confirmation |
| Preprocessing known | ✅ Fully recoverable, simple (librosa defaults, no dB, 128×432, 3-ch repeat) |
| Inference script | ❌ Missing — trivial ~50-line wrapper required (reuses existing classes) |
| Bird class indices known | ⚠️ Predicted (2 and 6), pending verification run |
| Blockers | Broken venv (missing python3.13) — 5-minute fix; no retraining needed |

The repository **can** provide the exact requested Teacher (mel-spectrogram + SWinT-BiLSTM, 83.16 % 27-class accuracy) at essentially zero compute cost.

## 10. Minimal Next Steps (in order, cheapest first)

1. **Repair the environment** (minutes, no training): `sudo apt install python3.13` to revive `venv/` as-is, *or* create a fresh venv (py3.12) with `torch torchvision librosa openpyxl`.
2. **Verify the label map** (one CPU/GPU inference pass, ~minutes): write `teacher_infer.py` (per §8), run fold-0 checkpoint over fold-0 eval split, confirm per-class accuracy ≈ 0.83 and that `23birdchirping` clips argmax to index 2 and `24wingflapping` to 6. This simultaneously validates checkpoint integrity, preprocessing reproduction, and class order. If per-class accuracy is scrambled, fall back to the `output_p_10` July-11 checkpoints (provably trained on this disk) or brute-force the permutation from per-folder argmax votes — still no retraining.
3. **Freeze the verified label map to disk** (JSON) so it is never re-derived from `os.listdir` again.
4. **Generate soft labels for distillation**: fold-matched (model *k* → eval slice *k*) or 5-model ensemble; export 27-class logits/probs + collapsed `P(bird)` per clip.
5. Only if step 2 fails irrecoverably (it very likely won't): retrain SWinT-BiLSTM with the existing script (~2 h on the RTX 5090 for all 5 folds, per the training logs) — a heavier option to consider only after confirming GPU/time availability, and with a `sorted(os.listdir(...))` fix plus label-map export added.

# FSC22 Teacher Soft-Label Generation Report

**Deterministic inference only** — no training; dataset/checkpoint read-only.

- Date: 2026-07-09 18:24:34
- Checkpoint: `output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/2025_07_21_16_06_03_Swint_LSTM_0.pth`
- Torch: 2.9.1+cu128 | Device: cuda
- Classes: 27 | bird_indices: [12, 20] | P(bird) = P[12] + P[20]
- Recovery decision inherited: CAUTION
- Determinism: folders: recovered_teacher_label_map.json:local_dataset_label_map (discovery order); files: sorted() within each folder; batch_size=32, shuffle=False; no augmentation; model.eval(); torch.no_grad(); cudnn.deterministic=True

## Decision: **PASS**

- Soft labels generated successfully; teacher separates bird vs non-bird well.

## Counts

- Total clips: 2025
- Bird clips (23birdchirping + 24wingflapping): 150
- Non-bird clips: 1875

## Binary bird/non-bird metrics @ threshold 0.5

| metric | value |
|---|---:|
| Mean P(bird) on true-bird | 0.907487 |
| Mean P(bird) on true-non-bird | 0.005174 |
| Binary accuracy | 0.995556 |
| Bird recall | 0.953333 |
| Bird precision | 0.986207 |
| Non-bird recall | 0.998933 |
| Confusion (TP/FN/FP/TN) | 143 / 7 / 2 / 1873 |

## Distribution of P(bird) (deciles)

| bin | count |
|---|---:|
| [0.0,0.1) | 1857 |
| [0.1,0.2) | 10 |
| [0.2,0.3) | 4 |
| [0.3,0.4) | 6 |
| [0.4,0.5) | 3 |
| [0.5,0.6) | 2 |
| [0.6,0.7) | 3 |
| [0.7,0.8) | 4 |
| [0.8,0.9) | 12 |
| [0.9,1.0) | 124 |

## Uncertain samples (0.4 <= P(bird) <= 0.6): 5

Top 20 closest to 0.5:

| file | true folder | P(bird) | teacher pred (recovered) | is_true_bird |
|---|---|---:|---|:--:|
| `7_10708.wav` | 07treefalling | 0.4922 | 24wingflapping | False |
| `27_12771.wav` | 27squirrel | 0.5160 | 23birdchirping | False |
| `2_10249.wav` | 02rain | 0.5305 | 23birdchirping | False |
| `24_12412.wav` | 24wingflapping | 0.4497 | 24wingflapping | True |
| `2_10271.wav` | 02rain | 0.4312 | 02rain | False |

## Output files

- `teacher_kd/soft_labels/fsc22_teacher_outputs_27class.npz`
- `teacher_kd/soft_labels/fsc22_soft_labels_binary.csv`
- `teacher_kd/soft_labels/soft_label_generation_summary.json`
- `teacher_kd/soft_labels/soft_label_generation_report.md`

## Notes for the KD pipeline

- Use `binary_soft_label_bird` (= P(bird) = P[12]+P[20]) as the distillation target; `binary_hard_label` is the folder-derived ground truth.
- The 27-class `logits_27` / `probs_27` in the NPZ allow temperature-scaled KD over the full teacher distribution if you prefer soft targets richer than the binary collapse.
- These labels are tied to THIS fixed ordering + batch_size=32. Regenerate identically (same script) if the dataset changes; do not shuffle or change batch size, because the Swint_LSTM teacher is batch-order sensitive.

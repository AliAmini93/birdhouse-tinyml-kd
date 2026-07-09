# Teacher Label-Permutation Recovery Report

**Recovery / inspection only** — no training; existing files only read.

- Date: 2026-07-09 16:51:17
- Checkpoint: `output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/2025_07_21_16_06_03_Swint_LSTM_0.pth`
- Torch: 2.9.1+cu128 | Device: cuda | Assignment: hungarian (scipy.linear_sum_assignment)
- Clips: 2025 total (405 fold-0 eval) | classes: 27 | batch_size=32

## Decision: **CAUTION**

Recovered permutation restores high accuracy, BUT P(bird) varies with batch size (LSTM consumes the batch as a sequence). P(bird) varies even between batch_size 8 and 32; soft labels are batch-order sensitive at every size. Pin one exact batch size AND clip ordering when generating labels and reuse it identically for teacher and any re-runs.

## Accuracy: local order vs recovered permutation

| set | raw (local os.listdir order) | remapped (recovered) |
|-----|------:|------:|
| all clips (2025) | 0.0731 | 0.9467 |
| fold-0 eval (405) | 0.0691 | 0.9333 |

The raw column reproduces the ~0.069 failure; the remapped column is the true teacher quality once the output indices are relabeled. (All-clips is higher than fold-0 because 60/75 clips per class were in training.)

## Bird classes (for binary collapse)

- `23birdchirping` -> **output index 12**
- `24wingflapping` -> **output index 20**
- **Recommended bird_indices = [12, 20]**
- **P(bird) = P[12] + P[20]** ; P(non_bird) = 1 - P(bird)
- Mean P(bird) on true-bird clips: 0.912 | on true-non-bird clips: 0.0047

**Yes — P(bird) should be P[12]+P[20]**. The local os.listdir indices (2, 6) are wrong for this checkpoint.

## Batch-size stability of P(bird)  (LSTM treats batch as sequence)

- Probe: 30 clips from 23birdchirping, 24wingflapping, 05wind, 02rain, 21insect, 22frog, 06silence
- bird indices used: [12, 20]

| comparison | mean |Δ P(bird)| | max |Δ P(bird)| |
|-----|------:|------:|
| bs1_vs_bs32 | 0.0762 | 0.3154 |
| bs8_vs_bs32 | 0.0054 | 0.0662 |
| bs1_vs_bs8 | 0.0715 | 0.3162 |

- Overall: mean|Δ|=0.0510, max|Δ|=0.3162 (tolerance 0.05) -> **POOR**

> P(bird) varies even between batch_size 8 and 32; soft labels are batch-order sensitive at every size. Pin one exact batch size AND clip ordering when generating labels and reuse it identically for teacher and any re-runs.

## Ambiguity warnings

- Output index **6** contested by: 16woodchop (19), 10axe (5)
- Output index **21** contested by: 10axe (68), 16woodchop (55)
- Output index **24** contested by: 09vehicleengine (72), 08helicopter (7)
  - `16woodchop` was forced onto out 6 (count 19/75); its argmax was out 21 (count 55). Verify this pair manually.

These do not affect the bird indices, but double-check the contested non-bird classes if they matter downstream.

## Recovered mapping (output_index -> folder)

| out idx | folder | | out idx | folder |
|--:|----|--|--:|----|
| 0 | 27squirrel | | 14 | 01fire |
| 1 | 02rain | | 15 | 20clapping |
| 2 | 07treefalling | | 16 | 13handsaw |
| 3 | 11chainsaw | | 17 | 19footsteps |
| 4 | 22frog | | 18 | 21insect |
| 5 | 04waterdrops | | 19 | 17whistling |
| 6 | 16woodchop | | 20 | 24wingflapping |
| 7 | 05wind | | 21 | 10axe |
| 8 | 08helicopter | | 22 | 14firework |
| 9 | 25lion | | 23 | 06silence |
| 10 | 26wolfhowl | | 24 | 09vehicleengine |
| 11 | 03thunderstorm | | 25 | 15gunshot |
| 12 | 23birdchirping | | 26 | 18speaking |
| 13 | 12generator | | | |

## Top-3 raw output indices per true folder

| true folder | 1st (count) | 2nd (count) | 3rd (count) |
|----|----|----|----|
| 10axe | out 21 (68) | out 6 (5) | out 22 (1) |
| 22frog | out 4 (74) | out 19 (1) | out 0 (0) |
| 23birdchirping | out 12 (74) | out 0 (1) | out 24 (0) |
| 25lion | out 9 (74) | out 18 (1) | out 0 (0) |
| 18speaking | out 26 (74) | out 24 (1) | out 23 (0) |
| 19footsteps | out 17 (75) | out 0 (0) | out 24 (0) |
| 24wingflapping | out 20 (73) | out 5 (1) | out 14 (1) |
| 05wind | out 7 (75) | out 0 (0) | out 24 (0) |
| 04waterdrops | out 5 (74) | out 14 (1) | out 0 (0) |
| 17whistling | out 19 (75) | out 0 (0) | out 24 (0) |
| 06silence | out 23 (75) | out 0 (0) | out 24 (0) |
| 15gunshot | out 25 (71) | out 15 (2) | out 22 (1) |
| 13handsaw | out 16 (75) | out 0 (0) | out 24 (0) |
| 08helicopter | out 8 (68) | out 24 (7) | out 0 (0) |
| 12generator | out 13 (69) | out 24 (4) | out 3 (1) |
| 16woodchop | out 21 (55) | out 6 (19) | out 3 (1) |
| 14firework | out 22 (73) | out 25 (2) | out 0 (0) |
| 11chainsaw | out 3 (75) | out 0 (0) | out 24 (0) |
| 03thunderstorm | out 11 (75) | out 0 (0) | out 24 (0) |
| 02rain | out 1 (71) | out 11 (2) | out 12 (2) |
| 01fire | out 14 (73) | out 17 (2) | out 0 (0) |
| 07treefalling | out 2 (73) | out 20 (2) | out 0 (0) |
| 26wolfhowl | out 10 (75) | out 0 (0) | out 24 (0) |
| 21insect | out 18 (70) | out 0 (2) | out 23 (1) |
| 09vehicleengine | out 24 (72) | out 13 (1) | out 7 (1) |
| 27squirrel | out 0 (72) | out 7 (2) | out 12 (1) |
| 20clapping | out 15 (75) | out 0 (0) | out 24 (0) |

## Output files

- `teacher_kd/recovered_teacher_label_map.json`
- `teacher_kd/recovered_permutation_report.md`
- `teacher_kd/recovered_confusion_raw.csv`
- `teacher_kd/recovered_confusion_remapped.csv`

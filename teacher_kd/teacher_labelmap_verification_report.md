# Teacher Label-Map Verification Report

**Verification-only** — no training was performed; existing files were only read.

- Date: 2026-07-09 16:38:36
- Interpreter: 3.11.15
- Torch: 2.9.1+cu128  |  Device: cuda  |  CUDA available: True
- Dataset root: `Dataset/fsc22`  (27 classes, 405 fold-0 eval clips)
- Eval config: batch_size=32, shuffle=False (replicates original for accuracy fidelity)

## Final decision: **FAIL (both)**  (checkpoint: `output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/2025_07_21_16_06_03_Swint_LSTM_0.pth`)

Neither the primary nor the backup checkpoint passed verification. Do NOT retrain automatically; investigate label order / checkpoint integrity / preprocessing before proceeding.

## Primary checkpoint attempt

- Checkpoint: `output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/2025_07_21_16_06_03_Swint_LSTM_0.pth`
- File exists: True  |  Loaded: True
- Overall accuracy: **0.0691** (recorded fold-0 ~0.837; threshold 0.75)
- 23birdchirping -> index 2 (expected 2) : OK
- 24wingflapping -> index 6 (expected 6) : OK
- Bird indices used for collapse: [2, 6]
- Mean P(bird) on true-bird clips: 0.0088  |  on true-non-bird clips: 0.0717
- Status: **FAIL**

### Per-class accuracy

| idx | folder | n | correct | acc |
|----:|--------|--:|--------:|----:|
| 0 | 10axe | 15 | 0 | 0.0 |
| 1 | 22frog | 15 | 0 | 0.0 |
| 2 | 23birdchirping | 15 | 0 | 0.0 |
| 3 | 25lion | 15 | 0 | 0.0 |
| 4 | 18speaking | 15 | 0 | 0.0 |
| 5 | 19footsteps | 15 | 0 | 0.0 |
| 6 | 24wingflapping | 15 | 0 | 0.0 |
| 7 | 05wind | 15 | 15 | 1.0 |
| 8 | 04waterdrops | 15 | 0 | 0.0 |
| 9 | 17whistling | 15 | 0 | 0.0 |
| 10 | 06silence | 15 | 0 | 0.0 |
| 11 | 15gunshot | 15 | 0 | 0.0 |
| 12 | 13handsaw | 15 | 0 | 0.0 |
| 13 | 08helicopter | 15 | 0 | 0.0 |
| 14 | 12generator | 15 | 0 | 0.0 |
| 15 | 16woodchop | 15 | 0 | 0.0 |
| 16 | 14firework | 15 | 0 | 0.0 |
| 17 | 11chainsaw | 15 | 0 | 0.0 |
| 18 | 03thunderstorm | 15 | 0 | 0.0 |
| 19 | 02rain | 15 | 0 | 0.0 |
| 20 | 01fire | 15 | 0 | 0.0 |
| 21 | 07treefalling | 15 | 0 | 0.0 |
| 22 | 26wolfhowl | 15 | 0 | 0.0 |
| 23 | 21insect | 15 | 0 | 0.0 |
| 24 | 09vehicleengine | 15 | 13 | 0.8667 |
| 25 | 27squirrel | 15 | 0 | 0.0 |
| 26 | 20clapping | 15 | 0 | 0.0 |

## Backup checkpoint attempt

- Checkpoint: `output_p_10/fsc22/model/melspectrogram/Swint_LSTM/2025_07_11_14_36_59_Swint_LSTM_0.pth`
- File exists: True  |  Loaded: True
- Overall accuracy: **0.0691** (recorded fold-0 ~0.837; threshold 0.75)
- 23birdchirping -> index 2 (expected 2) : OK
- 24wingflapping -> index 6 (expected 6) : OK
- Bird indices used for collapse: [2, 6]
- Mean P(bird) on true-bird clips: 0.0097  |  on true-non-bird clips: 0.081
- Status: **FAIL**

### Per-class accuracy

| idx | folder | n | correct | acc |
|----:|--------|--:|--------:|----:|
| 0 | 10axe | 15 | 0 | 0.0 |
| 1 | 22frog | 15 | 0 | 0.0 |
| 2 | 23birdchirping | 15 | 0 | 0.0 |
| 3 | 25lion | 15 | 0 | 0.0 |
| 4 | 18speaking | 15 | 0 | 0.0 |
| 5 | 19footsteps | 15 | 0 | 0.0 |
| 6 | 24wingflapping | 15 | 0 | 0.0 |
| 7 | 05wind | 15 | 15 | 1.0 |
| 8 | 04waterdrops | 15 | 0 | 0.0 |
| 9 | 17whistling | 15 | 0 | 0.0 |
| 10 | 06silence | 15 | 0 | 0.0 |
| 11 | 15gunshot | 15 | 0 | 0.0 |
| 12 | 13handsaw | 15 | 0 | 0.0 |
| 13 | 08helicopter | 15 | 0 | 0.0 |
| 14 | 12generator | 15 | 0 | 0.0 |
| 15 | 16woodchop | 15 | 0 | 0.0 |
| 16 | 14firework | 15 | 0 | 0.0 |
| 17 | 11chainsaw | 15 | 0 | 0.0 |
| 18 | 03thunderstorm | 15 | 0 | 0.0 |
| 19 | 02rain | 15 | 0 | 0.0 |
| 20 | 01fire | 15 | 0 | 0.0 |
| 21 | 07treefalling | 15 | 0 | 0.0 |
| 22 | 26wolfhowl | 15 | 0 | 0.0 |
| 23 | 21insect | 15 | 0 | 0.0 |
| 24 | 09vehicleengine | 15 | 13 | 0.8667 |
| 25 | 27squirrel | 15 | 0 | 0.0 |
| 26 | 20clapping | 15 | 0 | 0.0 |

## Output files

- `teacher_kd/fold0_predictions.csv`
- `teacher_kd/confusion_matrix.csv`
- `teacher_kd/verified_label_map.json`
- `teacher_kd/teacher_labelmap_verification_report.json`
- `teacher_kd/teacher_labelmap_verification_report.md`

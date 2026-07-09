# Student

Student model experiments for the Birdhouse TinyML bird / non-bird detector.

## Current baseline

```text
student/train_student_5s_hardlabel_baseline.py
```

Purpose:

```text
5 s audio
16 kHz mono
40-bin log-mel
small DS-CNN / compact CNN
binary bird / non-bird
hard labels only
weighted BCE
5-fold cross-validation
```

This is the mandatory hard-label baseline before any KD comparison.

## Run

```bash
cd /media/armin/External/AhmadWorks/audioclassification

"/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3" \
  student/train_student_5s_hardlabel_baseline.py \
  2>&1 | tee student/results/5s_hardlabel_baseline/train_console.log
```

## Do not commit generated outputs

Generated files under:

```text
student/cache/
student/results/
```

should remain local unless a lightweight report is explicitly selected for commit.


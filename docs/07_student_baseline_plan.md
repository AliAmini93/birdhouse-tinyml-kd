# 07 - Student 5 s Hard-Label Baseline Plan

This document defines the first Student implementation step.

## Goal

Train the mandatory hard-label baseline before testing KD.

```text
5 s audio
16 kHz mono
40-bin log-mel
small DS-CNN / compact CNN
binary bird / non-bird output
hard labels only
weighted BCE
5-fold cross-validation
```

## Why this comes first

The project already decided to start with 5-second Student models. This avoids the weak-label
risk introduced by slicing 5-second clips into shorter windows.

The hard-label baseline is required because the Teacher's binary soft labels are nearly hard.
KD is only worth keeping if it improves over this baseline.

## Labels

```text
bird = 1:
  23birdchirping
  24wingflapping

non-bird = 0:
  all other FSC22 folders
```

## Feature pipeline

```text
librosa.load(path, sr=16000, mono=True)
duration fixed to 5 s
frame length = 25 ms
hop = 20 ms
n_fft = 512
n_mels = 40
feature = log(mel + eps)
center = False
expected shape = 40 x 249
```

## Model

A compact Keras DS-CNN:

```text
Conv2D stem
DepthwiseConv2D + PointwiseConv2D blocks
GlobalAveragePooling2D
Dense 32
Dense 1 sigmoid
```

## Evaluation

Report:

```text
binary accuracy
bird recall
bird precision
F1
PR-AUC
ROC-AUC
recall at FPR <= 2%
per-folder false-positive analysis
```

## Next after baseline

If the baseline is strong:

```text
Compare KD variants against it.
```

If the baseline is weak:

```text
Check feature quality, class imbalance, architecture size, and per-folder failure modes
before adding KD complexity.
```


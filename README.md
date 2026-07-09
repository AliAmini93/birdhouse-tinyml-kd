# Birdhouse TinyML KD

TinyML bird / non-bird sound detection project for a low-power Birdhouse edge node.

## Goal

The deployment target is a binary acoustic classifier:

```text
bird / non-bird
```

The intended embedded platform is:

```text
Seeed Studio XIAO ESP32S3
```

The current training strategy is knowledge distillation:

```text
27-class FSC22 Teacher
-> collapse to binary bird / non-bird probability
-> train a small binary Student
-> quantize Student to INT8
-> deploy Student on XIAO ESP32S3
```

## Current Teacher Decision

The selected Teacher candidate is:

```text
FSC22 27-class mel-spectrogram + SWinT-BiLSTM
Repository class name: Swint_LSTM
```

The Teacher checkpoint is stored outside Git:

```text
output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/
```

Model weights and datasets are intentionally not committed to this repository.

## Key Findings

Initial local-label verification failed:

```text
Raw fold-0 accuracy with local os.listdir label order: 0.0691
Expected fold-0 accuracy: around 0.837
Initial bird indices: [2, 6]
Result: FAIL
```

This failure indicates that the checkpoint output label order does not match the local `os.listdir()` label order.

Recovered Teacher bird mapping:

```text
23birdchirping -> output index 12
24wingflapping -> output index 20
```

Therefore the binary collapse must use:

```text
P(bird) = P[12] + P[20]
P(non_bird) = 1 - P(bird)
```

Recovered performance reported during permutation recovery:

```text
All clips remapped accuracy: 0.9467
Fold-0 remapped accuracy: 0.9333
```

## Current Status

```text
Teacher status: usable with CAUTION
Reason: Swint_LSTM output is batch-size / ordering sensitive because the LSTM consumes the batch dimension as a sequence.
```

For any soft-label generation using this Teacher, the following must be fixed:

```text
batch_size = 32
shuffle = False
fixed clip ordering
same preprocessing
same checkpoint
same recovered output mapping
bird_indices = [12, 20]
```

## Next Step

Create a deterministic soft-label generation script using the recovered Teacher mapping.

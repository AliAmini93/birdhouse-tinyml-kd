# 02 - Teacher Verification and Label-Permutation Recovery

## Initial Verification

Script:

```text
teacher_kd/verify_teacher_labelmap.py
```

The first verification reproduced the local FSC22 label map using unsorted `os.listdir()`.

Local bird indices were:

```text
23birdchirping -> local index 2
24wingflapping -> local index 6
```

But the checkpoint did not match this local label order.

Result:

```text
Raw fold-0 accuracy: 0.0691
Expected: around 0.837
Status: FAIL
```

This indicated label permutation rather than complete model failure.

## Recovery

Script:

```text
teacher_kd/recover_teacher_label_permutation.py
```

Recovered mapping:

```text
23birdchirping -> output index 12
24wingflapping -> output index 20
```

Recommended binary collapse:

```text
P(bird) = P[12] + P[20]
P(non_bird) = 1 - P(bird)
```

Recovered accuracy reported during permutation recovery:

```text
All clips remapped accuracy: 0.9467
Fold-0 remapped accuracy: 0.9333
```

## Caution

The `Swint_LSTM` implementation is batch-sensitive.

Reason:

```text
swin_t output shape: (B, 768)
nn.LSTM receives a 2-D tensor
PyTorch treats it as an unbatched sequence
batch dimension becomes sequence length
```

Therefore Teacher predictions depend on batch size and order.

For soft-label generation, use:

```text
batch_size = 32
shuffle = False
fixed file order
fixed recovered mapping
```

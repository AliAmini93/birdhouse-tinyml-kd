# teacher_kd

This folder contains Teacher verification, label-map recovery, and future distillation utilities.

## Existing Verification

```text
verify_teacher_labelmap.py
```

This script tested the local `os.listdir()` label order and failed:

```text
accuracy = 0.0691
status = FAIL
```

## Label-Permutation Recovery

```text
recover_teacher_label_permutation.py
```

Recovered Teacher bird output indices:

```text
23birdchirping -> 12
24wingflapping -> 20
```

Use:

```text
P(bird) = P[12] + P[20]
```

## Warning

Do not use:

```text
P(bird) = P[2] + P[6]
```

Those are local dataset indices, not the checkpoint output indices.

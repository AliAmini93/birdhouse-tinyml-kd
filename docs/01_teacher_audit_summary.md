# 01 - Teacher Audit Summary

## Selected Teacher

```text
Dataset: FSC22
Task: 27-class forest sound classification
Feature: mel-spectrogram
Architecture: SWinT-BiLSTM
Code class: Swint_LSTM
Framework: PyTorch
```

## Checkpoint Location

```text
output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/
```

The main fold-0 checkpoint used for verification:

```text
output_for_dissertation/fsc22/model/melspectrogram/Swint_LSTM/2025_07_21_16_06_03_Swint_LSTM_0.pth
```

## Teacher Input Preprocessing

The Teacher expects the original dissertation preprocessing:

```text
librosa.load(path, sr=None)
native 44.1 kHz
mono
librosa.feature.melspectrogram(y=y, sr=sr)
n_fft = 2048
hop_length = 512
n_mels = 128
power = 2.0
no power_to_db
no log scaling
no normalization
tile/truncate to 128 x 432
model input shape before forward: [B, 128, 432]
inside model: repeat 1 channel to 3 channels
```

## Git Policy

Do not commit:

```text
Dataset/
output_for_dissertation/
output_for_revision/
output_p_10/
*.pth
*.wav
venv/
```

Only scripts, configs, and lightweight reports should be tracked.

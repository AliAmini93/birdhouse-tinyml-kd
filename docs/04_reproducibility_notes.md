# 04 - Reproducibility Notes

## Working Interpreter

The working interpreter used from the PyCharm environment:

```text
/mnt/HDD/AliWorks/HCI Tagging Database/HCI/bin/python3
```

Observed package versions:

```text
Python: 3.11.15
torch: 2.9.1+cu128
torchvision: 0.24.1+cu128
librosa: 0.11.0
sklearn: 1.6.1
pandas: 2.2.2
numpy: 1.26.4
```

## Broken External venv

The venvs inside the copied external project are not reliable because they were created on another machine and point to missing `python3.13` symlinks.

Do not rely on:

```text
venv/
AQR/MIMII/mimiienv/
```

Use a local working PyCharm interpreter or create a fresh environment.

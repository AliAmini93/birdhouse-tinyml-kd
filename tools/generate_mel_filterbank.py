#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import librosa
import numpy as np
import scipy.signal

REPO_ROOT_GUESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT_GUESS / "student"))

import train_student_5s_hardlabel_baseline as v1  # noqa: E402


def format_float_array(values: np.ndarray, values_per_line: int = 8) -> str:
    flat = values.reshape(-1)
    lines = []
    for i in range(0, len(flat), values_per_line):
        chunk = flat[i:i + values_per_line]
        lines.append("  " + ", ".join(f"{float(x):.9e}f" for x in chunk) + ",")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    out_dir = repo / "firmware" / "preprocess"
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = v1.Config()
    win_length = int(round(cfg.sample_rate * cfg.frame_ms / 1000.0))
    hop_length = int(round(cfg.sample_rate * cfg.hop_ms / 1000.0))
    expected_frames = v1.expected_frames(cfg)
    fft_bins = cfg.n_fft // 2 + 1

    mel = librosa.filters.mel(
        sr=cfg.sample_rate,
        n_fft=cfg.n_fft,
        n_mels=cfg.n_mels,
        fmin=cfg.fmin,
        fmax=cfg.fmax,
        htk=False,
        norm="slaney",
    ).astype(np.float32)

    if mel.shape != (cfg.n_mels, fft_bins):
        raise RuntimeError(f"Unexpected mel shape: {mel.shape}")

    window = scipy.signal.get_window("hann", win_length, fftbins=True).astype(np.float32)
    left = (cfg.n_fft - win_length) // 2
    right = cfg.n_fft - win_length - left
    padded_window = np.pad(window, (left, right), mode="constant").astype(np.float32)

    header = """#ifndef BIRDHOUSE_MEL_FILTERBANK_H_
#define BIRDHOUSE_MEL_FILTERBANK_H_

#include "firmware/preprocess/preprocess_constants.h"

namespace birdhouse {

extern const float kMelFilterbank[kNumMels * kFftBins];
extern const float kPaddedHannWindow[kFftSize];

}  // namespace birdhouse

#endif  // BIRDHOUSE_MEL_FILTERBANK_H_
"""

    source = f"""#include "firmware/preprocess/mel_filterbank.h"

namespace birdhouse {{

const float kMelFilterbank[kNumMels * kFftBins] = {{
{format_float_array(mel)}
}};

const float kPaddedHannWindow[kFftSize] = {{
{format_float_array(padded_window)}
}};

}}  // namespace birdhouse
"""

    (out_dir / "mel_filterbank.h").write_text(header, encoding="utf-8")
    (out_dir / "mel_filterbank.cc").write_text(source, encoding="utf-8")

    summary = {
        "sample_rate": cfg.sample_rate,
        "duration_s": cfg.duration_s,
        "n_fft": cfg.n_fft,
        "win_length": win_length,
        "hop_length": hop_length,
        "n_mels": cfg.n_mels,
        "fmin": cfg.fmin,
        "fmax": cfg.fmax,
        "htk": False,
        "norm": "slaney",
        "center": False,
        "expected_frames": expected_frames,
        "fft_bins": fft_bins,
        "mel_shape": list(mel.shape),
        "window_shape": list(padded_window.shape),
        "window_padding_left": left,
        "window_padding_right": right,
        "mel_filterbank_min": float(np.min(mel)),
        "mel_filterbank_max": float(np.max(mel)),
        "mel_filterbank_sum": float(np.sum(mel)),
    }

    (out_dir / "mel_filterbank_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print("Generated:")
    print(f"  {out_dir / 'mel_filterbank.h'}")
    print(f"  {out_dir / 'mel_filterbank.cc'}")
    print(f"  {out_dir / 'mel_filterbank_summary.json'}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()


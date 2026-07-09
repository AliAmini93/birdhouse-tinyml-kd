# NOTE - Superseded Design Review

This document is kept for traceability as Claude's independent Student design review.

Its earlier recommendation of a 2-second primary Student is superseded by:

```text
docs/06_student_design_decision.md
```

Final project decision:

```text
Start with 5-second Student models.
Use 2-second models only as fallback if 5-second models fail memory, latency, or energy constraints.
```

---

# 05 - Student Design Review (Bird / Non-Bird TinyML)

Design review only. No training code, no script changes, no commits. This document
proposes and critiques Student model options for a battery-powered birdhouse acoustic
node on a **Seeed Studio XIAO ESP32S3**, distilling from the recovered 27-class FSC22
SWinT-BiLSTM Teacher.

> This review is deliberately critical. Where the current plan looks weak, it says so.

---

## 0. What the data actually says (grounding)

Read directly from `teacher_kd/soft_labels/` before proposing anything:

| Fact | Value | Consequence for the Student |
|---|---|---|
| Total clips | 2025 (5 s, from FSC22) | Small. This, not the model, is the binding constraint. |
| Bird clips | 150 (75 `23birdchirping` + 75 `24wingflapping`) | Tiny positive set from **only two folders** → narrow acoustic coverage. |
| Imbalance | 1875 : 150 ≈ **12.5 : 1** | Must be handled explicitly (loss weighting / sampling). |
| P(bird) distribution | 1857 clips < 0.1, 124 clips > 0.9, **only 5 in [0.4,0.6]** | Soft labels are **near-degenerate (almost hard)** → binary distillation adds little over hard labels. |
| Harder bird class | `24wingflapping` mean P=0.891, min **0.049** | Wing-flapping is quiet/impulsive/diverse; expect most missed birds here. |
| Top non-bird confusers | `27squirrel` (mean 0.043, 1 FP), `02rain` (0.026, 1 FP), `07treefalling` (0.022) | These are the **field false-positive risks**. Squirrel ≈ bird-like calls; rain ≈ broadband chirpy texture. |
| Frog / insect | mean P(bird) ≈ 0.004 | Easy negatives on FSC22 — but the field will have far more insect/frog energy than FSC22. |

**Two conclusions up front:**

1. **The binary soft labels are almost hard.** Their marginal value for a *binary* Student
   is small. The Teacher's genuine value is (a) a trustworthy auto-labeler / sanity oracle,
   and (b) its **27-class distribution** (`probs_27`/`logits_27` in the NPZ), which still
   carries dark knowledge (e.g. a rain clip's spread over rain/thunderstorm/waterdrops).
   If distillation is going to help at all, it will be through *temperature-softened
   27-class targets collapsed to bird*, **not** the raw summed P(bird).

2. **FSC22 is a weak proxy for the field.** The Teacher never saw birdhouse audio, so it
   cannot transfer field robustness the hard labels don't already contain. Its highest-value
   future use is as a **pseudo-labeler for unlabeled field recordings you collect later**
   (semi-supervised expansion), which is where soft labels would actually pay off.

---

## 1. Executive recommendation

- **Primary (deploy candidate): Option C — 2 s, 16 kHz, compact log-mel (32 bins) + DS-CNN, INT8.**
  Best accuracy/energy trade-off. 2 s captures most bird events without the severe
  weak-label problem of 1 s; log-mel + depthwise-separable CNN is the proven KWS/TinyML
  sweet spot; comfortably fits the XIAO's resources.

- **Secondary / pipeline-validation: Option D — 5 s, 16 kHz, log-mel + small CNN or TCN.**
  Matches the Teacher's 5 s label granularity, so it has **zero window-mismatch label
  noise** and gives the cleanest distillation comparison. Use it first to validate the
  data/label/distillation pipeline, and keep it as a fallback if 2 s underperforms.

- **Fallback if energy is too tight: Option B — 1 s log-mel + DS-CNN**, but only with
  explicit positive-window mining (see §5). Do **not** ship a 1 s model trained on naively
  inherited 5 s labels.

- **Add regardless of model: Option F as a *pre-gate*, not a classifier.** A cheap
  RMS / spectral-flux energy gate decides *when* to run the NN. This is the single biggest
  battery win and is orthogonal to the model choice.

- **Avoid:**
  - **Option E (raw-waveform Conv1D) as the primary.** Raw-waveform nets are less
    data-efficient and less robust than spectral features — a bad match for 150 positives.
    Keep only as a curiosity if on-device feature extraction proves infeasible (it won't).
  - **A 27-class Student** on-device — no deployment need, larger, and the imbalance/label
    problems get worse per class.
  - **Naive 1 s windows inheriting 5 s bird labels** — manufactures positive-class label
    noise on the class you can least afford to corrupt.
  - **Assuming distillation helps.** Treat it as a hypothesis to be *tested against a
    hard-label baseline*, not a given.

---

## 2. Candidate Student options

Ratings are relative, for this dataset and the XIAO ESP32S3. "Distill fit" = how cleanly
the current Teacher labels transfer.

| | Input | Feature+Model | Accuracy (exp.) | Latency | RAM/Flash | Energy | Robustness | Impl. complexity | Distill fit |
|---|---|---|---|---|---|---|---|---|---|
| **A** | 1 s / 16 kHz | MFCC(13) + small CNN | Medium | Very low | Very low | Very low | Medium- | Low | Poor (window mismatch) |
| **B** | 1 s / 16 kHz | log-mel(32) + DS-CNN | Medium+ | Low | Low | Very low | Medium | Low-Med | Poor (window mismatch) |
| **C** ★ | 2 s / 16 kHz | log-mel(32) + DS-CNN | **High** | Low-Med | Low-Med | Low | **Med-High** | Medium | Medium |
| **D** | 5 s / 16 kHz | log-mel(40) + CNN/TCN | High | Medium | Medium | Med | High (clip-level) | Medium | **Best** (matches Teacher) |
| **E** | 1–2 s / 16 kHz | raw Conv1D | Low-Med | Med | Low-Med | Med | Low-Med | Medium | Poor |
| **F** | frame | RMS/ZCR/flux + tiny tree/LR | Low (alone) | Trivial | Trivial | Trivial | Low (alone) | Very low | N/A |

Notes per option:

- **A — 1 s MFCC + small CNN.** Cheapest neural option and closest to the existing Arduino
  PoCs. MFCC's DCT decorrelation is a legacy of GMM/HMM systems; small CNNs generally learn
  *better* from log-mel because the DCT discards locally-correlated structure the conv
  filters want. Combined with the 1 s weak-label issue, this is a reasonable *ablation* but
  a weak primary. Expected: usable recall on loud chirps, poor on wing-flapping.

- **B — 1 s log-mel + DS-CNN.** Better feature than A. DS-CNN is the MLPerf-Tiny KWS
  archetype and maps well to ESP-NN INT8 kernels. Still limited by the 1 s window: many
  1 s slices of a 5 s "bird" clip contain no bird. Only viable with positive-window mining.

- **C — 2 s log-mel + DS-CNN (recommended).** 2 s comfortably spans typical passerine song
  phrases and multiple wing-flap impulses, so inherited labels are far less noisy than at
  1 s while the model stays tiny. Sweet spot of the six. Slightly more RAM/latency than 1 s,
  still trivial for the XIAO.

- **D — 5 s log-mel + CNN/TCN (recommended secondary).** Trains on exactly the Teacher's
  label granularity → **no window-mismatch label noise** and the cleanest distillation.
  A TCN or a modest 2-D CNN both work. Costs more RAM/energy per inference and gives coarser
  event timing, but is the right **Stage-1** model to prove the pipeline and the honest
  upper bound on FSC22 accuracy. Can be deployed with a longer duty cycle if 2 s disappoints.

- **E — raw-waveform Conv1D.** Matches the earlier 1 s/16 kHz raw experiments, but for a
  150-positive dataset the inductive bias of spectral features is worth a lot. Raw nets
  also tend to overfit mic/channel characteristics — bad under domain shift. Not primary.

- **F — RMS/ZCR/spectral-flux + tiny classifier.** Cannot separate bird from squirrel/rain
  on energy statistics alone (they overlap in RMS/ZCR). **But** as an *always-on gate* that
  wakes the NN only on acoustic events, it is the biggest single energy lever. Use it that
  way, not as the decision model.

---

## 3. Recommended feature pipeline

- **Sample rate: 16 kHz mono.** Nyquist 8 kHz covers passerine fundamentals and lower
  harmonics; 44.1 kHz triples FFT cost and memory for little bird-relevant information.
  Down-sample/decimate on-device from the mic's native rate. (Teacher's 44.1 kHz is
  irrelevant to the Student — inputs need not match.)
- **Feature: compact log-mel (primary), MFCC (smaller backup).**
  - log-mel **32 bins** (extend to 40 for the 5 s Option D). Apply `log(mel + eps)` — this
    is a **deliberate divergence from the Teacher's linear power-mel**; log compression is
    standard and much better-conditioned for a small INT8 CNN. The Student is trained on its
    own features against the Teacher's *labels*, so feature parity with the Teacher is neither
    required nor desirable.
  - MFCC alternative: 13–20 coefficients (drop or keep C0). Smaller, cheaper, slightly worse
    for CNNs; good for the tightest-memory fallback.
- **Framing:** 25 ms window (400 samples), 10 ms hop (160) is the KWS default. For energy,
  20 ms hop halves the frame count with minor accuracy cost.
  - 1 s @ 20 ms hop → ~49 frames; 2 s → ~99 frames; 5 s → ~249 frames.
  - Feature map (primary C): **32 mels × ~99 frames**.
- **On-device extraction: yes, feasible.** Use ESP-DSP's optimized real FFT (radix-2, 256/512
  point) + a precomputed mel filterbank (store the sparse triangular weights in flash).
  Compute frames incrementally into a ring buffer so only one window is resident.
- **INT8 features:** quantize the log-mel to the TFLM input's int8 scale/zero-point. Fix the
  quantization range from the representative set (below), not per-frame min/max, so runtime
  behavior is stationary. Per-frame CMVN/normalization is tempting but adds state and can hurt
  under nonstationary field noise — prefer a fixed global mean/scale learned offline.

---

## 4. Distillation strategy

Given the near-degenerate binary soft labels (§0), be disciplined:

- **Baseline first (mandatory): hard labels only.** Folder-derived `binary_hard_label`
  with imbalance handling. This is the number every distillation variant must *beat* in
  cross-validation, or distillation is not worth its complexity.
- **How to use soft labels (if at all):** do **not** distill from the summed P(bird)
  directly. A summed 2-class probability cannot be meaningfully re-softened — temperature is
  undefined on it. Instead use the saved **`logits_27`**: compute
  `softmax(logits_27 / T)` then **sum indices 12 + 20** to get a *temperature-softened*
  P_soft(bird). At `T ≈ 2–4` this lifts the confident 0/1 mass into an informative range and
  is the only version of "soft" that carries usable signal here.
- **Combined loss:**
  `L = α · BCE(student, P_soft(bird)) + (1 − α) · L_hard(student, hard)`,
  with `L_hard` = weighted BCE or focal loss (see imbalance). Start `α ≈ 0.3`, `T ≈ 3`, and
  ablate `α ∈ {0, 0.3, 0.5}`. `α = 0` is the baseline; if higher `α` never wins on CV,
  drop distillation.
- **Class imbalance:**
  - **Weighted BCE** with `pos_weight ≈ 12` (≈ neg/pos) is the simplest correct baseline.
  - **Focal loss** (γ ≈ 2) is worth trying — it down-weights the many easy negatives and
    focuses on the hard wing-flapping positives and squirrel/rain confusers.
  - **Oversample birds + augment** rather than under-sampling (you can't afford to discard
    negatives that teach the confusers). Augment birds: time-shift, small pitch-shift (±1–2
    semitones), SpecAugment (time/freq masking), and **mix bird events onto non-bird
    backgrounds** (wind/rain/insect) to synthesize realistic low-SNR positives — this both
    balances classes and directly hardens against the known confusers.
- **Uncertain samples (the 5 in [0.4,0.6]):** keep them; they are the decision boundary. Do
  not drop or force to hard 0/1. Under the softened-27 scheme they naturally carry their
  ambiguity.
- **Splits without leakage:** split by **whole 5 s clip** (and by source file), so all
  windows of a clip stay in one fold — otherwise near-duplicate windows leak train→test and
  inflate metrics. Stratify by class. With only 150 positives, use **5-fold CV grouped by
  clip** for stable estimates, plus a **held-out test set of whole clips** never touched
  during model selection. Consider grouping the two bird folders' rarer acoustic variants so
  each fold sees both chirping and wing-flapping.

---

## 5. The 5 s Teacher → 1 s / 2 s Student label problem

This is the most technically dangerous part of the plan.

- **Is it acceptable to train a 1 s Student on 5 s clip labels?** Only with care. A 5 s bird
  clip may contain <1 s of actual bird sound. Slicing into five 1 s windows and stamping all
  five "bird" injects false positives into a 150-example positive class — precisely the class
  that can least tolerate noise. For non-bird clips this is harmless (every sub-window is
  non-bird). So the damage is **asymmetric and concentrated on positives**.
- **Why not just re-score sub-windows with the Teacher?** The Teacher is fixed 5 s input
  (mel tiled to 128×432). Feeding it 1 s is out-of-distribution and unreliable, so it cannot
  cleanly localize the bird event within a clip.
- **Recommended handling, in order of preference:**
  1. **Option D first (5 s Student).** Eliminates the mismatch entirely; validate the whole
     pipeline and get the honest FSC22 ceiling before shortening the window.
  2. **Option C (2 s) with positive-window mining.** For each bird clip, use energy /
     spectral-flux / onset detection to select the most salient 2 s window(s) as positives;
     mark low-energy windows **"ignore"** (excluded from loss) rather than positive. Negatives
     can use all windows. This is weak-label MIL done pragmatically.
  3. **Clip-level aggregation at inference.** Even a short-window Student can be evaluated
     clip-level by max/mean-pooling window scores over 5 s, which tolerates a few silent
     windows and matches how the field node will actually integrate evidence over time.
  4. **Avoid** blind 1 s inheritance (Option A/B without mining).
- **Practical compromise:** Stage-1 train and select at **5 s** (clean labels, clean
  distillation). Stage-2 move to **2 s with positive-window mining**, evaluated both
  per-window and clip-aggregated. Only drop to 1 s if energy profiling forces it, and then
  only with mining + clip-level aggregation.

---

## 6. First-attempt architecture (Option C: 2 s log-mel DS-CNN)

```
Input:   int8 log-mel, shape (1, 32, 99, 1)      # 32 mel bins × ~99 frames (2 s, 20 ms hop)
Stem:    Conv2D(3x3, 24 ch, stride (2,2)) + BN + ReLU6        # -> (16, 50, 24)
Block1:  DepthwiseConv(3x3) + BN + ReLU6 → Conv2D(1x1, 32) + BN + ReLU6
Block2:  DepthwiseConv(3x3, stride 2) + BN + ReLU6 → Conv2D(1x1, 48) + BN + ReLU6  # ↓ spatial
Block3:  DepthwiseConv(3x3) + BN + ReLU6 → Conv2D(1x1, 64) + BN + ReLU6
Block4:  DepthwiseConv(3x3, stride 2) + BN + ReLU6 → Conv2D(1x1, 64) + BN + ReLU6
Pool:    GlobalAveragePooling2D                                # → (64,)
Head:    Dense(32) + ReLU6 → Dropout(0.2) → Dense(1)
Output:  sigmoid  →  P(bird)                                   # single logit; BCE / focal
```

- **Parameters:** ≈ 30k–60k (DS-CNN-S class). Tunable via filter widths.
- **Quantized size:** full-integer INT8 → **~40–120 KB flash**.
- **Tensor arena (rough):** dominated by the largest intermediate activation. Stem output
  16×50×24 ≈ 19 K int8; with double-buffering + scratch, budget **~60–150 KB**. Trivial in
  the XIAO's 512 KB SRAM; PSRAM available if needed.
- **Latency:** feature extraction ~5–15 ms (incremental FFT+mel) + inference ~10–30 ms INT8
  with ESP-NN on the S3 → well under a 2 s cadence; real-time with large headroom.
- **Output activation:** sigmoid (one probability). **Quantization:** start with
  post-training full-integer INT8 (representative set = a class-balanced, augmented sample of
  training windows incl. squirrel/rain/insect). If PTQ costs >3 pts recall (likely on the
  quiet wing-flapping positives), switch to **quantization-aware training**.
- 1 s (Option B) and 5 s (Option D) reuse the same block template with the frame dimension
  and one stride changed; keep a single parameterized definition so windows are swappable.

---

## 7. Evaluation plan

- **Primary metrics (imbalance-aware):** **PR-AUC** (more informative than ROC-AUC at
  12.5:1), plus **recall at a fixed low non-bird false-positive rate** (e.g. recall @ FPR ≤
  1–2 %) — deployment cares about not firing on every rain shower far more than about 0.5
  accuracy. Report F1, ROC-AUC too, but decide on PR-AUC + recall@FPR.
- **FN/FP analysis:** expect most **false negatives on `24wingflapping`** (quiet/impulsive)
  and most **false positives on `27squirrel` and `02rain`** (per §0). Track these explicitly.
- **Per-non-bird-class breakdown:** report P(bird) / FP rate per FSC22 non-bird folder so the
  confusers are visible; weight the representative/augmentation sets toward squirrel, rain,
  insect, frog, treefalling, footsteps.
- **Threshold tuning:** do **not** ship 0.5. Choose the operating threshold from the PR curve
  for the target field FP rate; re-tune after INT8 (quantization shifts the logit scale).
- **Energy-aware evaluation:** report inferences/hour × (feature + inference energy) against
  the battery budget under the gated duty cycle; compare 1 s vs 2 s vs 5 s on
  energy-per-correct-detection, not just accuracy.
- **Float-vs-INT8 parity:** require INT8 recall drop < 3 pts vs float; if not, QAT.
- **Real-world test:** the decisive test. Collect ambient birdhouse-like recordings (dawn
  chorus, wind, rain, insects, silence) the model never trained on, label a small validation
  set, and measure FP rate on genuine non-bird ambience and recall on genuine birds. FSC22 CV
  numbers will be optimistic relative to this.

---

## 8. Deployment plan — XIAO ESP32S3

- **Board reality:** ESP32-S3 dual-core LX7 @240 MHz, 512 KB SRAM; XIAO ESP32S3 **Sense**
  adds 8 MB PSRAM, 8 MB flash, and an onboard PDM microphone (use the Sense variant, or add
  an I²S/PDM MEMS mic). Memory is *not* the tight constraint here — energy is.
- **Feature extraction:** ESP-DSP FFT + static mel filterbank in flash; ring-buffer framing.
  Feasible in a few ms/frame.
- **TFLM compatibility:** DS-CNN uses only Conv2D / DepthwiseConv2D / FC / AveragePool /
  ReLU6 / Logistic — all in the TFLM builtin op set with **ESP-NN** INT8 acceleration. Build
  a minimal `MicroMutableOpResolver` with just these ops to save flash.
- **INT8:** full-integer quantization; int8 input (quantized log-mel), int8 weights, int8/int32
  activations.
- **Microphone capture:** I²S DMA from the PDM mic at 16 kHz mono; decimate if the mic clocks
  higher; store one window in a ring buffer.
- **Environmental / sensor gating:** cheap always-on **RMS / spectral-flux gate** (Option F)
  runs on the ADC/I²S stream; wake the NN only when an acoustic event exceeds an adaptive
  noise floor. Optionally gate further by time-of-day (dawn/dusk activity) to cut night-time
  duty.
- **Duty cycling:** deep-sleep between listening windows (S3 deep sleep ~10 µA vs active
  ~40–100 mA). Target a listen/sleep schedule + event gate that meets the battery life goal;
  this dominates energy far more than model size.
- **Event-driven reporting:** transmit only on positive detections. **LoRa** (low duty,
  long range, sub-mW average) fits a remote birdhouse far better than Wi-Fi; batch/aggregate
  detections to minimize radio-on time. If Wi-Fi is mandated, buffer and burst.

---

## 9. Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **Tiny bird set (150 clips, 2 folders)** | High | Aggressive augmentation; mix birds onto real backgrounds; **plan to expand with external bird audio** (e.g. field recordings / open bird-audio sets) or Teacher-pseudo-labeled field data. Treat FSC22-only as a prototype, not a field model. |
| **Domain shift (FSC22 → birdhouse)** | High | Real-world validation set; collect on-site ambience early; the Teacher cannot fix this — only representative data can. |
| **Weak labels (5 s → short window)** | High | Train 5 s first; positive-window mining for 2 s/1 s; clip-level aggregation at inference; "ignore" low-energy windows. |
| **Near-degenerate soft labels** | Medium | Use temperature-softened 27-class collapse, not summed P(bird); gate distillation on beating the hard-label baseline. |
| **Teacher batch/order sensitivity** | Medium | Already contained: soft labels are frozen, deterministic, PASS. Never regenerate with shuffling or a different batch size; the NPZ/CSV are the single source of truth. |
| **Squirrel/rain false positives** | Medium | Over-represent them in training/representative sets; tune threshold to a low field FP rate; report per-class FP. |
| **Label noise on positives** | Medium | MIL-style mining; manual spot-check of the mined positive windows. |
| **ESP32S3 energy budget** | Medium | Energy gate + duty cycle + LoRa; profile on-device early (Stage 5) before committing the window length. |
| **INT8 accuracy loss on quiet birds** | Medium | QAT if PTQ recall drop >3 pts; per-channel weight quant; representative set weighted to quiet wing-flapping. |
| **Overfitting during model selection** | Medium | Group-by-clip CV + untouched held-out test; small model; early stopping on CV recall@FPR. |

---

## 10. Staged roadmap

- **Stage 1 — Offline Student baseline.** Build the windowing + log-mel pipeline. Train
  **Option D (5 s)** and **Option C (2 s)** on **hard labels only** with weighted BCE /
  focal + augmentation. Group-by-clip 5-fold CV + held-out test. Establishes the honest
  FSC22 ceiling and the number distillation must beat.
- **Stage 2 — Distillation comparison.** Add the temperature-softened 27-class-collapsed
  target; ablate `α ∈ {0, 0.3, 0.5}`, `T ∈ {2, 3, 4}`. **Keep distillation only if it
  beats Stage 1 on CV PR-AUC / recall@FPR.** Decide 5 s vs 2 s here.
- **Stage 3 — Quantization.** PTQ full-integer INT8 with a class-balanced representative set;
  compare float vs INT8 recall@FPR. If drop >3 pts → QAT.
- **Stage 4 — TFLM export.** Convert to `.tflite` int8; verify op coverage against a minimal
  ESP-NN resolver; sanity-check parity between TFLite (host) and float on a fixed test set.
- **Stage 5 — On-device profiling.** Flash to the XIAO ESP32S3 Sense; measure feature+inference
  latency, arena size, active/idle current for 1 s/2 s/5 s; validate the energy gate + duty
  cycle against the battery target. This stage can *change the window choice*.
- **Stage 6 — Field testing.** Deploy in/near a real birdhouse; collect ambient audio; measure
  real FP rate on wind/rain/insects/squirrel and real recall on live birds; retune threshold;
  iterate (ideally feeding Teacher-pseudo-labeled field clips back into training).

---

## Final recommendation

- **Primary Student design:** **Option C — 2 s, 16 kHz, log-mel(32) + DS-CNN, INT8**, with
  positive-window mining and an always-on energy pre-gate.
- **Secondary Student design:** **Option D — 5 s, 16 kHz, log-mel(40) + CNN/TCN, INT8** —
  built first as the clean-label pipeline validator and kept as the fallback / distillation
  reference.
- **Explicitly rejected:** 27-class Student, raw-waveform primary (E), and any 1 s model on
  naively inherited labels.

**Minimum experiment matrix (group-by-clip 5-fold CV + held-out test):**

| Axis | Values |
|---|---|
| Window | 5 s (D), 2 s (C) [+ 1 s only if energy forces it] |
| Feature | log-mel(32/40) primary; MFCC(13) ablation |
| Loss | weighted BCE (baseline) vs focal; distill `α ∈ {0, 0.3, 0.5}`, `T ∈ {2,3,4}` |
| Imbalance | oversample+augment birds; background-mix positives |
| Quant | float → PTQ INT8 → (QAT if needed) |

≈ 8–12 training runs total (small model, minutes each on the RTX 5090).

**Go / no-go criteria before deployment:**

1. **CV bird recall ≥ 0.90 at non-bird FPR ≤ 2 %** (threshold tuned on PR curve), stable
   across folds.
2. **PR-AUC** clearly above the hard-label baseline if distillation is claimed to help
   (else ship the simpler baseline).
3. **INT8 recall drop < 3 pts** vs float at the chosen operating point.
4. **On-device:** feature+inference latency < window cadence; arena fits SRAM; energy budget
   met under the gated duty cycle.
5. **Field pilot:** acceptable FP rate on real ambient (wind/rain/insect/squirrel) recordings
   the model never trained on — this, not FSC22 CV, is the real gate. If the field FP rate is
   unacceptable, **stop and expand the dataset** rather than tuning the model further.

> Bottom line: the model is the easy part. Spend the effort on the label-window mismatch,
> the imbalance, and — above all — getting bird/ambience data that resembles the field. The
> Teacher's best role from here is auto-labeling that future data, not squeezing dark
> knowledge out of an already-near-binary soft label.

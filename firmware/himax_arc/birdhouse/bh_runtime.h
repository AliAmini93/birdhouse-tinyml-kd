// Birdhouse runtime: capture 5 s of audio, compute the log-mel features, run
// the model, report the decision with everything needed to reproduce it.
//
// Capture-then-process: the interrupt side only copies samples into a linear
// buffer (bh_capture). Feature extraction and inference run afterwards in the
// main loop, so there is no real-time DSP deadline and no sample queue.
//
// All functions here are main-loop functions. Nothing blocks except the
// processing step at the end of a capture (feature extraction + inference).
#ifndef BIRDHOUSE_HIMAX_BH_RUNTIME_H_
#define BIRDHOUSE_HIMAX_BH_RUNTIME_H_

#include <cstddef>
#include <cstdint>

#include "firmware/himax_arc/birdhouse/bh_capture.h"
#include "firmware/himax_arc/birdhouse/bh_diag.h"
#include "firmware/himax_arc/birdhouse/bh_model.h"

#define BH_VERSION "birdhouse-himax-0.1"

namespace bh {

enum RunState { kRunIdle = 0, kRunCapturing = 1, kRunDone = 2, kRunFailed = 3 };

// Stage at which a run failed; printed so a failure can be located from one line.
enum RunStage {
  kStageNone = 0,
  kStageModelInit = 1,
  kStagePdmStart = 2,
  kStageCapture = 3,
  kStagePdmStop = 4,
  kStagePreprocess = 5,
  kStageInvoke = 6,
};

enum RunSource { kSourceNone = 0, kSourceMicrophone = 1, kSourceSynthetic = 2, kSourceReference = 3 };

struct RunResult {
  uint32_t seq;
  RunState state;
  RunSource source;
  RunStage failed_stage;
  int failure_detail;      // ModelStatus, CaptureError or port return code
  bool has_decision;
  int output_q;            // raw INT8 model output
  bool is_bird;
  uint32_t p_bird_x10000;  // probability * 10000, integer
  CaptureQuality quality;  // microphone runs only
  CaptureStats capture;
  PcmStats pcm;
  uint32_t pcm_crc32;
  uint32_t feature_crc32;
  uint32_t capture_us;
  uint32_t preprocess_us;
  uint32_t invoke_us;
};

const char* RunStateName(RunState s);
const char* RunStageName(RunStage s);

// Builds the interpreter on first use. Safe to call repeatedly.
ModelStatus RuntimeEnsureModel();

// Queue `count` microphone runs (count >= 1); gaps between runs are allowed.
// Returns 0, or -1 if a run is already active or queued, -2 for count == 0.
int RuntimeRequestRuns(uint32_t count);
// Abort the active capture and drop queued runs.
void RuntimeCancel();
// Call from the main loop as often as possible. Cheap when idle.
void RuntimePoll();

RunState RuntimeState();
uint32_t RuntimePendingRuns();
const RunResult& RuntimeLastResult();

// Self-tests that need no microphone.
// Model only, no audio and no feature extraction: the embedded reference
// features, scaled by step/8 about the input zero point (step 1..8, 8 = the
// unmodified clip), are run through the model and the raw output is compared
// with the value the TensorFlow Lite reference kernels produce. The eight steps
// give outputs across the whole range (-128 ... 116), so a kernel that differs
// numerically shows up as a small non-zero difference.
// Returns the absolute difference, or -1 if the model did not run.
int RuntimeSelfTestModel(int step = 8);
// All eight steps plus a summary line. Returns the largest difference or -1.
int RuntimeSelfTestModelAll();
// Whole pipeline on a deterministic integer signal (bh::SynthKind).
// Returns 0 if a decision was produced.
int RuntimeRunSynthetic(int kind);

// Report helpers (print through bh_port_printf).
void RuntimePrintInfo();
void RuntimePrintResult(const RunResult& r);
// Base64 dump of the PCM (int16 little endian) or feature (int8) buffer of the
// last run. `offset`/`count` are in elements. Returns false if out of range.
bool RuntimeDumpPcm(uint32_t offset, uint32_t count);
bool RuntimeDumpFeatures(uint32_t offset, uint32_t count);

// Buffers of the last run; valid while no capture is active.
const int16_t* RuntimePcm();
const int8_t* RuntimeFeatures();

#if defined(BIRDHOUSE_HOST_BUILD)
// Host tests only: force a model initialisation failure, or reset all state.
void RuntimeTestSetArenaLimit(size_t bytes);  // 0 = full arena
void RuntimeTestReset();
#endif

}  // namespace bh

#endif  // BIRDHOUSE_HIMAX_BH_RUNTIME_H_

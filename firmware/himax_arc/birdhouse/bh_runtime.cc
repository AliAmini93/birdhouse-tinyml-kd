#include "firmware/himax_arc/birdhouse/bh_runtime.h"

#include <cstring>

#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/birdhouse/bh_selftest_expected.h"
#include "firmware/inference/testdata/reference_model_output.h"
#include "firmware/model/model_constants.h"
#include "firmware/model/student_final_int8_model_data.h"
#include "firmware/preprocess/audio_preprocess.h"
#include "firmware/preprocess/testdata/reference_input_int8.h"

namespace bh {
namespace {

// Ownership: the capture interrupt writes g_pcm between pdm_start and the
// moment the main loop has stopped audio and called Capture::Finish().
int16_t g_pcm[kTargetSamples] BH_BIG_RAM;
alignas(16) uint8_t g_arena[kArenaBytes] BH_BIG_RAM;
int8_t g_features[birdhouse::kFeatureElements] BH_BIG_RAM;

Capture g_capture;
RunResult g_last = RunResult();
RunState g_state = kRunIdle;
uint32_t g_pending = 0;
uint32_t g_seq = 0;
uint64_t g_capture_start_us = 0;
bool g_in_poll = false;
size_t g_arena_limit = 0;  // host tests only
uint32_t g_pcm_valid_samples = 0;
bool g_features_valid = false;

const CaptureConfig kCaptureConfig = {
    kTargetSamples, kFramesPerBlock, kSettleBlocks,
    kCallbackIntervalUs, kIntervalToleranceUs, kClockTickUs, kDmaCallbackBlocks};

uint32_t ClampU32(uint64_t v) { return v > 0xFFFFFFFFull ? 0xFFFFFFFFu : static_cast<uint32_t>(v); }
unsigned long UL(uint64_t v) { return static_cast<unsigned long>(ClampU32(v)); }
// The BSP can return one tick early; unsigned subtraction would look like a
// multi-billion-year delay and immediately expire a newly started capture.
uint64_t Elapsed(uint64_t now, uint64_t start) { return now >= start ? now - start : 0; }

void BeginResult(RunSource source) {
  g_last = RunResult();
  g_last.seq = ++g_seq;
  g_last.source = source;
  g_last.state = kRunIdle;
  g_pcm_valid_samples = 0;
  g_features_valid = false;
}

void FailRun(RunStage stage, int detail) {
  g_last.state = kRunFailed;
  g_last.failed_stage = stage;
  g_last.failure_detail = detail;
  g_last.has_decision = false;
  g_state = kRunFailed;
}

// Feature extraction + inference on whatever is in g_pcm.
bool ProcessPcm() {
  ComputePcmStats(g_pcm, kTargetSamples, &g_last.pcm);
  g_last.pcm_crc32 = Crc32(g_pcm, sizeof(g_pcm));

  const uint64_t t0 = bh_port_now_us();
  const bool ok = birdhouse::PreprocessInt16PcmToInt8ModelInput(
      g_pcm, kTargetSamples, g_features, sizeof(g_features));
  const uint64_t t1 = bh_port_now_us();
  g_last.preprocess_us = ClampU32(Elapsed(t1, t0));
  if (!ok) {
    FailRun(kStagePreprocess, 0);
    return false;
  }
  g_last.feature_crc32 = Crc32(g_features, sizeof(g_features));
  g_features_valid = true;

  // The interpreter reuses the input tensor's memory during Invoke, so the
  // features are kept in their own buffer and copied in before every run.
  int8_t* input = ModelInput();
  if (input == nullptr) {
    FailRun(kStageModelInit, kModelNotReady);
    return false;
  }
  std::memcpy(input, g_features, sizeof(g_features));
  const uint64_t t2 = bh_port_now_us();
  const ModelStatus st = ModelInvoke();
  const uint64_t t3 = bh_port_now_us();
  g_last.invoke_us = ClampU32(Elapsed(t3, t2));
  if (st != kModelOk) {
    FailRun(kStageInvoke, st);
    return false;
  }
  g_last.output_q = ModelOutputQ();
  g_last.is_bird = ModelIsBird();
  g_last.p_bird_x10000 = static_cast<uint32_t>(
      (g_last.output_q - birdhouse::kModelOutputZeroPoint) * 10000 / 256);
  // Keep raw inference for diagnosis, but never label questionable audio as
  // a valid bird/non-bird observation.
  g_last.has_decision = g_last.source != kSourceMicrophone || g_last.quality == kQualityClean;
  return true;
}

void StopAudio() {
  const int rc = bh_port_pdm_stop();
  g_capture.Finish();
  g_last.capture = g_capture.stats();
  g_pcm_valid_samples = g_last.capture.samples;
  if (rc != 0 && g_last.failed_stage == kStageNone) {
    // Reported, but the samples already in the buffer are not affected.
    g_last.failed_stage = kStagePdmStop;
    g_last.failure_detail = rc;
  }
}

void StartOneCapture() {
  BeginResult(kSourceMicrophone);
  const ModelStatus ms = RuntimeEnsureModel();
  if (ms != kModelOk) {
    FailRun(kStageModelInit, ms);
    return;
  }
  if (!g_capture.Begin(g_pcm, kTargetSamples, kCaptureConfig)) {
    FailRun(kStageCapture, g_capture.error());
    return;
  }
  const int rc = bh_port_pdm_start(&g_capture);
  if (rc != 0) {
    g_capture.Finish();
    FailRun(kStagePdmStart, rc);
    return;
  }
  // Nothing is printed between start and stop: console output must not
  // disturb the interrupt that re-arms each audio block.
  g_capture_start_us = bh_port_now_us();
  g_last.state = kRunCapturing;
  g_state = kRunCapturing;
}

void FinishCapture(CaptureError reason = kCapNone) {
  g_last.capture_us = ClampU32(Elapsed(bh_port_now_us(), g_capture_start_us));
  StopAudio();
  if (reason != kCapNone) g_capture.Fail(reason);  // ISR detached, no first-error race
  const CaptureError err = g_capture.error();
  if (err != kCapNone) {
    FailRun(kStageCapture, err);
    return;
  }
  if (g_last.failed_stage == kStagePdmStop) {
    FailRun(kStagePdmStop, g_last.failure_detail);
    return;
  }
  g_last.quality = JudgeCapture(g_last.capture, kCaptureConfig);
  if (ProcessPcm()) {
    g_last.state = kRunDone;
    g_state = kRunDone;
  }
}

void DumpSink(const char* chunk, size_t len, void*) {
  char line[65];
  if (len > 64) len = 64;
  std::memcpy(line, chunk, len);
  line[len] = '\0';
  bh_port_printf("%s\n", line);
}

bool DumpBytes(const char* what, const void* base, size_t element_size, uint32_t total,
               uint32_t offset, uint32_t count) {
  if (g_state == kRunCapturing) return false;
  if (count == 0 || offset >= total || count > total - offset) return false;
  const uint8_t* p = static_cast<const uint8_t*>(base) + static_cast<size_t>(offset) * element_size;
  const size_t bytes = static_cast<size_t>(count) * element_size;
  bh_port_printf("BIRDHOUSE DUMP BEGIN what=%s seq=%lu offset=%lu count=%lu bytes=%lu crc=%08lx\n",
                 what, UL(g_last.seq), UL(offset), UL(count), UL(bytes),
                 static_cast<unsigned long>(Crc32(p, bytes)));
  Base64Encode(p, bytes, DumpSink, nullptr);
  bh_port_printf("BIRDHOUSE DUMP END\n");
  return true;
}

}  // namespace

const char* RunStateName(RunState s) {
  switch (s) {
    case kRunIdle: return "IDLE";
    case kRunCapturing: return "CAPTURING";
    case kRunDone: return "DONE";
    case kRunFailed: return "FAILED";
  }
  return "UNKNOWN";
}

const char* RunStageName(RunStage s) {
  switch (s) {
    case kStageNone: return "NONE";
    case kStageModelInit: return "MODEL_INIT";
    case kStagePdmStart: return "PDM_START";
    case kStageCapture: return "CAPTURE";
    case kStagePdmStop: return "PDM_STOP";
    case kStagePreprocess: return "PREPROCESS";
    case kStageInvoke: return "INVOKE";
  }
  return "UNKNOWN";
}

ModelStatus RuntimeEnsureModel() {
  if (ModelReady()) return kModelOk;
  const size_t arena = g_arena_limit != 0 ? g_arena_limit : sizeof(g_arena);
  const ModelStatus st = ModelInit(birdhouse::g_student_final_int8_model_data,
                                   birdhouse::g_student_final_int8_model_data_len, g_arena, arena);
  bh_port_printf("BIRDHOUSE MODEL status=%s arena_size=%lu arena_used=%lu\n", ModelStatusName(st),
                 UL(arena), UL(ModelGetInfo().arena_used));
  return st;
}

int RuntimeRequestRuns(uint32_t count) {
  if (count != 1) return -2;  // repeated physical capture is unqualified
  if (g_state == kRunCapturing || g_pending != 0 || bh_port_pdm_faulted() || bh_port_vendor_busy()) return -1;
  g_pending = count;
  return 0;
}

void RuntimeCancel() {
  g_pending = 0;
  if (g_state == kRunCapturing) {
    g_last.capture_us = ClampU32(Elapsed(bh_port_now_us(), g_capture_start_us));
    StopAudio();
    g_capture.Fail(kCapCancelled);
    FailRun(kStageCapture, g_capture.error());
    RuntimePrintResult(g_last);
  } else if (bh_port_pdm_faulted()) {
    const int rc = bh_port_pdm_stop();
    bh_port_printf("BIRDHOUSE STOP retry_rc=%d faulted=%d\n", rc, bh_port_pdm_faulted() ? 1 : 0);
  }
}

void RuntimePoll() {
  if (g_in_poll) return;
  g_in_poll = true;

  if (g_state == kRunCapturing) {
    bool finished = false;
    CaptureError reason = kCapNone;
    if (g_capture.error() != kCapNone || g_capture.complete()) {
      finished = true;
    } else if (Elapsed(bh_port_now_us(), g_capture_start_us) > kCaptureDeadlineUs) {
      reason = kCapTimeout;
      finished = true;
    }
    if (finished) {
      FinishCapture(reason);
      RuntimePrintResult(g_last);
      if (g_state == kRunFailed || !g_last.has_decision || bh_port_pdm_faulted()) g_pending = 0;
    }
  } else if (g_pending != 0) {
    --g_pending;
    StartOneCapture();
    if (g_state == kRunFailed) {
      g_pending = 0;
      RuntimePrintResult(g_last);
    }
  }

  g_in_poll = false;
}

RunState RuntimeState() { return g_state; }
uint32_t RuntimePendingRuns() { return g_pending; }
const RunResult& RuntimeLastResult() { return g_last; }
const int16_t* RuntimePcm() { return g_pcm; }
const int8_t* RuntimeFeatures() { return g_features; }

int RuntimeSelfTestModel(int step) {
  if (g_state == kRunCapturing || g_pending != 0 || bh_port_pdm_faulted() || bh_port_vendor_busy()) return -1;
  if (step < 1 || step > kSelfTestSteps) return -1;
  BeginResult(kSourceReference);
  const ModelStatus ms = RuntimeEnsureModel();
  if (ms != kModelOk) {
    FailRun(kStageModelInit, ms);
    RuntimePrintResult(g_last);
    return -1;
  }
  const int zp = birdhouse::kModelInputZeroPoint;
  for (int i = 0; i < birdhouse::kFeatureElements; ++i) {
    const int delta = (static_cast<int>(birdhouse::kReferenceInputInt8[i]) - zp) * step;
    g_features[i] = static_cast<int8_t>(zp + delta / 8);  // truncates toward zero
  }
  g_last.feature_crc32 = Crc32(g_features, sizeof(g_features));
  g_features_valid = true;
  std::memcpy(ModelInput(), g_features, sizeof(g_features));
  const uint64_t t0 = bh_port_now_us();
  const ModelStatus st = ModelInvoke();
  g_last.invoke_us = ClampU32(Elapsed(bh_port_now_us(), t0));
  if (st != kModelOk) {
    FailRun(kStageInvoke, st);
    RuntimePrintResult(g_last);
    return -1;
  }
  g_last.output_q = ModelOutputQ();
  g_last.is_bird = ModelIsBird();
  g_last.p_bird_x10000 = static_cast<uint32_t>(
      (g_last.output_q - birdhouse::kModelOutputZeroPoint) * 10000 / 256);
  g_last.has_decision = true;
  g_last.state = kRunDone;
  g_state = kRunDone;
  const int expected = kSelfTestExpectedQ[step];
  const int diff = g_last.output_q > expected ? g_last.output_q - expected : expected - g_last.output_q;
  bh_port_printf("BIRDHOUSE SELFTEST model step=%d out_q=%d expected_q=%d abs_diff=%d feature_crc=%08lx invoke_us=%lu verdict=%s\n",
                 step, g_last.output_q, expected, diff, static_cast<unsigned long>(g_last.feature_crc32),
                 UL(g_last.invoke_us), diff == 0 ? "EXACT" : (diff <= 2 ? "CLOSE" : "MISMATCH"));
  return diff;
}

int RuntimeSelfTestModelAll() {
  int exact = 0, close = 0, mismatch = 0, worst = 0;
  for (int step = 1; step <= kSelfTestSteps; ++step) {
    const int diff = RuntimeSelfTestModel(step);
    if (diff < 0) {
      bh_port_printf("BIRDHOUSE SELFTEST summary verdict=NOT_RUN step=%d\n", step);
      return -1;
    }
    if (diff == 0) ++exact; else if (diff <= 2) ++close; else ++mismatch;
    if (diff > worst) worst = diff;
  }
  bh_port_printf("BIRDHOUSE SELFTEST summary steps=%d exact=%d close=%d mismatch=%d max_abs_diff=%d verdict=%s\n",
                 kSelfTestSteps, exact, close, mismatch, worst,
                 mismatch != 0 ? "MISMATCH" : (close != 0 ? "CLOSE" : "EXACT"));
  return worst;
}

int RuntimeRunSynthetic(int kind) {
  if (g_state == kRunCapturing || g_pending != 0 || bh_port_pdm_faulted() || bh_port_vendor_busy()) return -1;
  BeginResult(kSourceSynthetic);
  const ModelStatus ms = RuntimeEnsureModel();
  if (ms != kModelOk) {
    FailRun(kStageModelInit, ms);
    RuntimePrintResult(g_last);
    return -1;
  }
  if (!SynthFill(kind, g_pcm, kTargetSamples)) {
    FailRun(kStagePreprocess, -1);
    RuntimePrintResult(g_last);
    return -1;
  }
  g_pcm_valid_samples = kTargetSamples;
  bh_port_printf("BIRDHOUSE SYNTH kind=%d name=%s\n", kind, SynthKindName(kind));
  if (ProcessPcm()) {
    g_last.state = kRunDone;
    g_state = kRunDone;
  }
  RuntimePrintResult(g_last);
  return g_last.has_decision ? 0 : -1;
}

void RuntimePrintInfo() {
  const ModelInfo& mi = ModelGetInfo();
  bh_port_printf("BIRDHOUSE INFO version=%s state=%s pending=%lu seq=%lu\n", BH_VERSION,
                 RunStateName(g_state), UL(g_pending), UL(g_seq));
  bh_port_printf("BIRDHOUSE INFO model_bytes=%lu model_crc=%08lx ready=%d arena_size=%lu arena_used=%lu invokes=%lu\n",
                 UL(birdhouse::g_student_final_int8_model_data_len),
                 static_cast<unsigned long>(Crc32(birdhouse::g_student_final_int8_model_data,
                                                   birdhouse::g_student_final_int8_model_data_len)),
                 ModelReady() ? 1 : 0, UL(sizeof(g_arena)), UL(mi.arena_used), UL(mi.invoke_count));
  bh_port_printf("BIRDHOUSE INFO samples=%lu rate=%lu block_bytes=%lu blocks=%lu cb_blocks=%lu settle_blocks=%lu thr_q=%d\n",
                 UL(kTargetSamples), UL(kSampleRateHz), UL(kDmaBlockBytes), UL(kDmaBlockCount),
                 UL(kDmaCallbackBlocks), UL(kSettleBlocks), ModelBirdThresholdQ());
  bh_port_print_platform_info();
  bh_port_printf("BIRDHOUSE INFO pdm_faulted=%d detached_callbacks=%lu pcm_valid_samples=%lu features_valid=%d\n",
                 bh_port_pdm_faulted() ? 1 : 0, UL(bh_port_pdm_late_callbacks()),
                 UL(g_pcm_valid_samples), g_features_valid ? 1 : 0);
}

void RuntimePrintResult(const RunResult& r) {
  const char* source = r.source == kSourceMicrophone ? "MIC"
                       : r.source == kSourceSynthetic ? "SYNTH"
                       : r.source == kSourceReference ? "REFERENCE" : "NONE";
  if (r.state == kRunFailed) {
    const char* detail = "";
    if (r.failed_stage == kStageCapture) {
      detail = CaptureErrorName(static_cast<CaptureError>(r.failure_detail));
    } else if (r.failed_stage == kStageModelInit || r.failed_stage == kStageInvoke) {
      detail = ModelStatusName(static_cast<ModelStatus>(r.failure_detail));
    }
    bh_port_printf("BIRDHOUSE RESULT seq=%lu source=%s state=FAILED stage=%s detail=%d %s\n",
                   UL(r.seq), source, RunStageName(r.failed_stage), r.failure_detail, detail);
  } else {
    bh_port_printf("BIRDHOUSE RESULT seq=%lu source=%s state=%s decision=%s out_q=%d p_x10000=%lu thr_q=%d quality=%s\n",
                   UL(r.seq), source, RunStateName(r.state),
                   r.has_decision ? (r.is_bird ? "BIRD" : "NON-BIRD") : "NONE", r.output_q,
                   UL(r.p_bird_x10000), ModelBirdThresholdQ(),
                   r.source == kSourceMicrophone ? CaptureQualityName(r.quality) : "N/A");
  }
  if (r.source == kSourceMicrophone) {
    const CaptureStats& c = r.capture;
    bh_port_printf("BIRDHOUSE CAPTURE seq=%lu samples=%lu callbacks=%lu blocks=%lu settle=%lu used=%lu late=%lu inactive=%lu per_cb=%lu..%lu fifo=%lu\n",
                   UL(r.seq), UL(c.samples), UL(c.callbacks), UL(c.blocks_seen),
                   UL(c.blocks_settle_dropped), UL(c.blocks_used), UL(c.blocks_after_complete),
                   UL(c.callbacks_inactive),
                   UL(c.min_blocks_per_callback == 0xFFFFFFFFu ? 0 : c.min_blocks_per_callback),
                   UL(c.max_blocks_per_callback), UL(c.fifo_events));
    bh_port_printf("BIRDHOUSE TIMING seq=%lu intervals=%lu min_us=%lu max_us=%lu nominal_us=%lu anomalies=%lu clock_steps=%lu span_us=%lu nominal_span_us=%lu\n",
                   UL(r.seq), UL(c.intervals),
                   UL(c.interval_min_us == 0xFFFFFFFFu ? 0 : c.interval_min_us),
                   UL(c.interval_max_us), UL(kCallbackIntervalUs), UL(c.interval_anomalies),
                   UL(c.clock_steps), UL(c.complete_us - c.first_callback_us),
                   UL(NominalSpanUs(c, kCaptureConfig)));
    const unsigned long n = c.samples != 0 ? c.samples : 1;
    bh_port_printf("BIRDHOUSE CHANNELS seq=%lu mean_abs_left=%lu mean_abs_right=%lu\n", UL(r.seq),
                   UL(c.sum_abs_left / n), UL(c.sum_abs_right / n));
  }
  if ((r.source == kSourceMicrophone || r.source == kSourceSynthetic) && r.state == kRunDone) {
    bh_port_printf("BIRDHOUSE PCM seq=%lu crc=%08lx min=%ld max=%ld mean=%ld rms=%lu clipped=%lu zeros=%lu zero_run=%lu\n",
                   UL(r.seq), static_cast<unsigned long>(r.pcm_crc32), static_cast<long>(r.pcm.min),
                   static_cast<long>(r.pcm.max), static_cast<long>(r.pcm.mean), UL(r.pcm.rms),
                   UL(r.pcm.clipped), UL(r.pcm.zeros), UL(r.pcm.longest_zero_run));
  }
  bh_port_printf("BIRDHOUSE COMPUTE seq=%lu feature_crc=%08lx capture_us=%lu preprocess_us=%lu invoke_us=%lu arena_used=%lu\n",
                 UL(r.seq), static_cast<unsigned long>(r.feature_crc32), UL(r.capture_us),
                 UL(r.preprocess_us), UL(r.invoke_us), UL(ModelGetInfo().arena_used));
}

bool RuntimeDumpPcm(uint32_t offset, uint32_t count) {
  return DumpBytes("pcm_s16le", g_pcm, sizeof(int16_t), g_pcm_valid_samples, offset, count);
}

bool RuntimeDumpFeatures(uint32_t offset, uint32_t count) {
  return g_features_valid && DumpBytes("features_s8", g_features, 1, birdhouse::kFeatureElements, offset, count);
}

#if defined(BIRDHOUSE_HOST_BUILD)
void RuntimeTestSetArenaLimit(size_t bytes) {
  g_arena_limit = bytes;
  ModelDeinit();
}

void RuntimeTestReset() {
  ModelDeinit();
  g_capture.Finish();
  g_last = RunResult();
  g_state = kRunIdle;
  g_pending = 0;
  g_seq = 0;
  g_capture_start_us = 0;
  g_in_poll = false;
  g_arena_limit = 0;
  g_pcm_valid_samples = 0;
  g_features_valid = false;
  std::memset(g_pcm, 0, sizeof(g_pcm));
  std::memset(g_features, 0, sizeof(g_features));
}
#endif

}  // namespace bh

// End-to-end host test of the Birdhouse runtime:
//   emulated audio library -> PDM adapter -> capture -> batch log-mel ->
//   TFLite Micro (vendor sources, reference kernels) -> decision and report.
// Everything except the audio library emulation and the clock/print port is
// the code that is linked into the firmware.
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "firmware/himax_arc/birdhouse/bh_config.h"
#include "firmware/himax_arc/birdhouse/bh_port.h"
#include "firmware/himax_arc/birdhouse/bh_runtime.h"
#include "firmware/himax_arc/tests/bh_test.h"
#include "firmware/himax_arc/tests/fake_aud_lib.h"
#include "firmware/himax_arc/tests/host_port.h"
#include "firmware/inference/testdata/reference_model_output.h"
#include "firmware/model/model_constants.h"
#include "firmware/preprocess/audio_preprocess.h"

namespace {

std::vector<int16_t> g_signal[bh::kSynthKindCount];

struct Expected {
  uint32_t pcm_crc;
  uint32_t feature_crc;
  int output_q;
  bool is_bird;
};
Expected g_expected[bh::kSynthKindCount];

// Microphone emulation: 2048 frames of start-up transient, then the selected
// synthetic signal on the left channel; the right channel carries junk.
int g_mic_kind = 0;
int16_t MicSource(uint64_t frame, int channel, void*) {
  if (channel == 1) return static_cast<int16_t>(12345 - static_cast<int>(frame % 97));
  if (frame < 2048) return static_cast<int16_t>(30000 - static_cast<int>(frame) * 14);  // settling ramp
  const uint64_t i = frame - 2048;
  return i < bh::kTargetSamples ? g_signal[g_mic_kind][i] : 0;
}

void Fresh() {
  fake_aud::Reset();
  fake_aud::SetSource(MicSource, nullptr);
  bh::RuntimeTestReset();
  host_port::Clear();
}

// Runs the main loop and the emulated audio until nothing is active or queued.
uint32_t Drive(uint32_t max_blocks = 5000) {
  uint32_t blocks = 0;
  for (;;) {
    bh::RuntimePoll();
    if (bh::RuntimeState() != bh::kRunCapturing && bh::RuntimePendingRuns() == 0) break;
    if (blocks >= max_blocks) break;
    fake_aud::CompleteBlock();
    ++blocks;
  }
  return blocks;
}

bool Contains(const std::string& haystack, const char* needle) {
  return haystack.find(needle) != std::string::npos;
}

std::vector<uint8_t> DecodeBase64(const std::string& text) {
  std::vector<uint8_t> out;
  uint32_t acc = 0;
  int bits = 0;
  for (char ch : text) {
    int v;
    if (ch >= 'A' && ch <= 'Z') v = ch - 'A';
    else if (ch >= 'a' && ch <= 'z') v = ch - 'a' + 26;
    else if (ch >= '0' && ch <= '9') v = ch - '0' + 52;
    else if (ch == '+') v = 62;
    else if (ch == '/') v = 63;
    else continue;
    acc = (acc << 6) | static_cast<uint32_t>(v);
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      out.push_back(static_cast<uint8_t>((acc >> bits) & 0xFF));
    }
  }
  return out;
}

// Body of the last dump printed (text between the BEGIN and END lines).
std::string LastDumpBody(const std::string& output) {
  const size_t begin = output.rfind("BIRDHOUSE DUMP BEGIN");
  const size_t end = output.rfind("BIRDHOUSE DUMP END");
  if (begin == std::string::npos || end == std::string::npos || end < begin) return "";
  const size_t body = output.find('\n', begin);
  return output.substr(body + 1, end - body - 1);
}

}  // namespace

int main() {
  for (int kind = 0; kind < bh::kSynthKindCount; ++kind) {
    g_signal[kind].resize(bh::kTargetSamples);
    bh::SynthFill(kind, g_signal[kind].data(), bh::kTargetSamples);
  }

  BH_CASE("model self-test on the embedded reference features");
  Fresh();
  BH_CHECK(bh::RuntimeSelfTestModel() == 0);
  BH_CHECK(bh::RuntimeLastResult().output_q == birdhouse::kReferenceModelOutputInt8);
  BH_CHECK(bh::RuntimeLastResult().is_bird);
  BH_CHECK(Contains(host_port::Output(), "BIRDHOUSE SELFTEST model step=8 out_q=116 expected_q=116 abs_diff=0"));
  BH_CHECK(Contains(host_port::Output(), "verdict=EXACT"));
  BH_CHECK(Contains(host_port::Output(), "BIRDHOUSE MODEL status=OK"));
  BH_CHECK(bh::RuntimeSelfTestModel(0) == -1);
  BH_CHECK(bh::RuntimeSelfTestModel(9) == -1);

  BH_CASE("graded model self-test: eight steps across the output range, all exact on host");
  Fresh();
  BH_CHECK(bh::RuntimeSelfTestModelAll() == 0);
  BH_CHECK(Contains(host_port::Output(), "BIRDHOUSE SELFTEST summary steps=8 exact=8 close=0 mismatch=0 max_abs_diff=0 verdict=EXACT"));
  BH_CHECK(Contains(host_port::Output(), "step=4 out_q=12 expected_q=12"));
  BH_CHECK(Contains(host_port::Output(), "step=3 out_q=-89 expected_q=-89"));
  {
    const std::string& out = host_port::Output();
    size_t pos = 0;
    while ((pos = out.find("BIRDHOUSE SELFTEST model step=", pos)) != std::string::npos) {
      const size_t end = out.find('\n', pos);
      std::printf("EXPECTED_LINE %s\n", out.substr(pos, end - pos).c_str());
      pos = end;
    }
  }

  BH_CASE("synthetic pipeline runs equal a direct call of preprocessing and the model");
  for (int kind = 0; kind < bh::kSynthKindCount; ++kind) {
    Fresh();
    BH_CHECK(bh::RuntimeRunSynthetic(kind) == 0);
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(r.state == bh::kRunDone && r.has_decision && r.source == bh::kSourceSynthetic);
    // Independent path: same PCM through the preprocessing function and the model wrapper.
    static int8_t features[birdhouse::kFeatureElements];
    BH_CHECK(birdhouse::PreprocessInt16PcmToInt8ModelInput(g_signal[kind].data(), bh::kTargetSamples,
                                                           features, sizeof(features)));
    BH_CHECK(std::memcmp(features, bh::RuntimeFeatures(), sizeof(features)) == 0);
    BH_CHECK(r.feature_crc32 == bh::Crc32(features, sizeof(features)));
    BH_CHECK(r.pcm_crc32 == bh::Crc32(g_signal[kind].data(), bh::kTargetSamples * sizeof(int16_t)));
    std::memcpy(bh::ModelInput(), features, sizeof(features));
    BH_CHECK(bh::ModelInvoke() == bh::kModelOk);
    BH_CHECK(bh::ModelOutputQ() == r.output_q);
    BH_CHECK(r.p_bird_x10000 == static_cast<uint32_t>((r.output_q + 128) * 10000 / 256));
    BH_CHECK(r.is_bird == (r.output_q >= bh::ModelBirdThresholdQ()));
    g_expected[kind] = {r.pcm_crc32, r.feature_crc32, r.output_q, r.is_bird};
    std::printf("EXPECTED {\"test\":\"AT+BIRDSYNTH=%d\",\"name\":\"%s\",\"pcm_crc\":\"%08x\","
                "\"feature_crc\":\"%08x\",\"out_q\":%d,\"decision\":\"%s\"}\n",
                kind, bh::SynthKindName(kind), r.pcm_crc32, r.feature_crc32, r.output_q,
                r.is_bird ? "BIRD" : "NON-BIRD");
  }
  BH_CHECK(bh::RuntimeRunSynthetic(99) == -1);
  BH_CHECK(bh::RuntimeLastResult().state == bh::kRunFailed);
  std::printf("EXPECTED {\"test\":\"AT+BIRDSELFTEST\",\"out_q\":%d,\"decision\":\"BIRD\"}\n",
              birdhouse::kReferenceModelOutputInt8);

  BH_CASE("microphone run: 80,000 samples after the settle blocks, same result as the synthetic run");
  for (int kind = 0; kind < bh::kSynthKindCount; ++kind) {
    Fresh();
    g_mic_kind = kind;
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    const uint32_t blocks = Drive();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(blocks == 82);
    BH_CHECK(r.state == bh::kRunDone && r.source == bh::kSourceMicrophone && r.has_decision);
    BH_CHECK(r.quality == bh::kQualityClean);
    BH_CHECK(r.capture.samples == 80000 && r.capture.callbacks == 41);
    BH_CHECK(r.capture.blocks_settle_dropped == 2 && r.capture.fifo_events == 0);
    BH_CHECK(r.pcm_crc32 == g_expected[kind].pcm_crc);
    BH_CHECK(r.feature_crc32 == g_expected[kind].feature_crc);
    BH_CHECK(r.output_q == g_expected[kind].output_q);
    BH_CHECK(r.is_bird == g_expected[kind].is_bird);
    BH_CHECK(std::memcmp(bh::RuntimePcm(), g_signal[kind].data(), bh::kTargetSamples * sizeof(int16_t)) == 0);
    BH_CHECK(!fake_aud::running());
    BH_CHECK(fake_aud::counters().starts == 1 && fake_aud::counters().stops == 1);
    BH_CHECK(fake_aud::counters().ring_overflows == 0);
    const std::string& out = host_port::Output();
    BH_CHECK(Contains(out, "BIRDHOUSE RESULT seq=1 source=MIC state=DONE decision="));
    BH_CHECK(Contains(out, "quality=CLEAN"));
    BH_CHECK(Contains(out, "BIRDHOUSE CAPTURE seq=1 samples=80000 callbacks=41 blocks=82 settle=2 used=79"));
    BH_CHECK(Contains(out, "BIRDHOUSE TIMING seq=1 intervals=40 min_us=128000 max_us=128000 nominal_us=128000 anomalies=0 clock_steps=0 span_us=5120000 nominal_span_us=5120000"));
    BH_CHECK(Contains(out, "BIRDHOUSE CHANNELS"));
    BH_CHECK(Contains(out, "BIRDHOUSE PCM seq=1 crc="));
    BH_CHECK(Contains(out, "BIRDHOUSE COMPUTE seq=1 feature_crc="));
  }

  BH_CASE("nothing is printed while a capture is in progress");
  {
    Fresh();
    g_mic_kind = 1;
    bh::RuntimeEnsureModel();  // the model line is printed before audio starts
    host_port::Clear();
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    bh::RuntimePoll();
    BH_CHECK(bh::RuntimeState() == bh::kRunCapturing);
    for (int i = 0; i < 60; ++i) {
      fake_aud::CompleteBlock();
      bh::RuntimePoll();
    }
    BH_CHECK(bh::RuntimeState() == bh::kRunCapturing);
    BH_CHECK(host_port::Output().empty());
    Drive();
    BH_CHECK(!host_port::Output().empty());
  }

  BH_CASE("repeated classification: queued runs restart audio and settle again every time");
  {
    Fresh();
    g_mic_kind = 2;
    BH_CHECK(bh::RuntimeRequestRuns(0) == -2);
    BH_CHECK(bh::RuntimeRequestRuns(5) == 0);
    BH_CHECK(bh::RuntimeRequestRuns(1) == -1);  // already queued
    Drive();
    BH_CHECK(fake_aud::counters().blocks_completed == 5 * 82);
    BH_CHECK(bh::RuntimeLastResult().seq == 5);
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunDone);
    BH_CHECK(bh::RuntimeLastResult().output_q == g_expected[2].output_q);
    BH_CHECK(bh::RuntimeLastResult().pcm_crc32 == g_expected[2].pcm_crc);
    BH_CHECK(fake_aud::counters().starts == 5 && fake_aud::counters().stops == 5);
    BH_CHECK(bh::ModelGetInfo().invoke_count == 5);
    size_t pos = 0;
    int results = 0;
    while ((pos = host_port::Output().find("state=DONE", pos)) != std::string::npos) {
      ++results;
      pos += 10;
    }
    BH_CHECK(results == 5);
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);  // idle again
    Drive();
    BH_CHECK(bh::RuntimeLastResult().seq == 6);
  }

  BH_CASE("capture timeout: audio never delivers, deadline expires, next run works");
  {
    Fresh();
    g_mic_kind = 0;
    BH_CHECK(bh::RuntimeRequestRuns(3) == 0);
    bh::RuntimePoll();
    BH_CHECK(bh::RuntimeState() == bh::kRunCapturing);
    fake_aud::AdvanceTime(bh::kCaptureDeadlineUs - 1000);
    bh::RuntimePoll();
    BH_CHECK(bh::RuntimeState() == bh::kRunCapturing);
    fake_aud::AdvanceTime(2000);
    bh::RuntimePoll();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(r.state == bh::kRunFailed && r.failed_stage == bh::kStageCapture);
    BH_CHECK(r.failure_detail == bh::kCapTimeout && !r.has_decision);
    BH_CHECK(!fake_aud::running());
    BH_CHECK(bh::RuntimePendingRuns() == 0);  // a failing run is not repeated blindly
    BH_CHECK(Contains(host_port::Output(), "state=FAILED stage=CAPTURE detail=5 TIMEOUT"));
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunDone);
  }

  BH_CASE("incomplete recording: audio stops delivering half way");
  {
    Fresh();
    g_mic_kind = 1;
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    bh::RuntimePoll();
    fake_aud::CompleteBlocks(40);
    bh::RuntimePoll();
    BH_CHECK(bh::RuntimeState() == bh::kRunCapturing);
    fake_aud::AdvanceTime(bh::kCaptureDeadlineUs);
    bh::RuntimePoll();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(r.state == bh::kRunFailed && r.failure_detail == bh::kCapTimeout);
    BH_CHECK(r.capture.samples == 38 * 1024);
    BH_CHECK(!r.has_decision);
  }

  BH_CASE("PDM start failure is reported with its stage and does not stick");
  {
    Fresh();
    fake_aud::faults().fail_start = true;
    BH_CHECK(bh::RuntimeRequestRuns(2) == 0);
    Drive();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(r.state == bh::kRunFailed && r.failed_stage == bh::kStagePdmStart && r.failure_detail == -3);
    BH_CHECK(bh::RuntimePendingRuns() == 0);
    BH_CHECK(Contains(host_port::Output(), "state=FAILED stage=PDM_START detail=-3"));
    fake_aud::faults().fail_start = false;
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunDone);
  }

  BH_CASE("PDM stop failure fails the run; the next start is still possible");
  {
    Fresh();
    fake_aud::faults().fail_stop = true;
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunFailed);
    BH_CHECK(bh::RuntimeLastResult().failed_stage == bh::kStagePdmStop);
    fake_aud::faults().fail_stop = false;
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunDone);
  }

  BH_CASE("PDM FIFO overflow during capture fails the run at stage CAPTURE");
  {
    Fresh();
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    bh::RuntimePoll();
    fake_aud::CompleteBlocks(30);
    bh_port_on_pdm_reinit();
    Drive();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(r.state == bh::kRunFailed && r.failed_stage == bh::kStageCapture);
    BH_CHECK(r.failure_detail == bh::kCapFifoOverflow);
    BH_CHECK(Contains(host_port::Output(), "FIFO_OVERFLOW"));
    BH_CHECK(!fake_aud::running());
  }

  BH_CASE("library errors and bad block addresses fail the run");
  {
    Fresh();
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    bh::RuntimePoll();
    fake_aud::CompleteBlocks(6);
    fake_aud::faults().fail_request_read = 1;
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunFailed);
    BH_CHECK(bh::RuntimeLastResult().failure_detail == bh::kCapLibraryError);

    Fresh();
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    bh::RuntimePoll();
    fake_aud::CompleteBlocks(6);
    fake_aud::faults().bad_address = 1;
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunFailed);
    BH_CHECK(bh::RuntimeLastResult().failure_detail == bh::kCapBadBlock);
  }

  BH_CASE("overrun inside the audio library: decision is produced but flagged SUSPECT");
  {
    Fresh();
    g_mic_kind = 2;
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    bh::RuntimePoll();
    fake_aud::CompleteBlocks(24);
    fake_aud::faults().suppress_callbacks = 6;
    Drive();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(fake_aud::counters().ring_overflows >= 1);
    BH_CHECK(r.state == bh::kRunDone && r.has_decision);
    BH_CHECK(r.quality == bh::kQualitySuspect);
    BH_CHECK(r.pcm_crc32 != g_expected[2].pcm_crc);
    BH_CHECK(Contains(host_port::Output(), "quality=SUSPECT"));
  }

  BH_CASE("time base at half speed: flagged CLOCK, samples intact");
  {
    Fresh();
    g_mic_kind = 3;
    fake_aud::SetBlockPeriodUs(32000);
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(r.state == bh::kRunDone && r.quality == bh::kQualityClock);
    BH_CHECK(r.pcm_crc32 == g_expected[3].pcm_crc);
    BH_CHECK(r.output_q == g_expected[3].output_q);
  }

  BH_CASE("model initialisation failure is reported before audio is started");
  {
    Fresh();
    bh::RuntimeTestSetArenaLimit(16 * 1024);
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    const bh::RunResult r = bh::RuntimeLastResult();
    BH_CHECK(r.state == bh::kRunFailed && r.failed_stage == bh::kStageModelInit);
    BH_CHECK(r.failure_detail == bh::kModelAllocateTensors);
    BH_CHECK(fake_aud::counters().starts == 0);
    BH_CHECK(Contains(host_port::Output(), "stage=MODEL_INIT detail=4 ALLOCATE_TENSORS"));
    BH_CHECK(bh::RuntimeSelfTestModel() == -1);
    BH_CHECK(bh::RuntimeSelfTestModelAll() == -1);
    BH_CHECK(bh::RuntimeRunSynthetic(0) == -1);
    bh::RuntimeTestSetArenaLimit(0);
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunDone);
  }

  BH_CASE("cancel aborts the capture and clears the queue");
  {
    Fresh();
    BH_CHECK(bh::RuntimeRequestRuns(4) == 0);
    bh::RuntimePoll();
    fake_aud::CompleteBlocks(10);
    bh::RuntimeCancel();
    BH_CHECK(bh::RuntimeState() == bh::kRunFailed);
    BH_CHECK(bh::RuntimeLastResult().failure_detail == bh::kCapCancelled);
    BH_CHECK(bh::RuntimePendingRuns() == 0);
    BH_CHECK(!fake_aud::running());
    bh::RuntimeCancel();  // idle: no effect
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunDone);
  }

  BH_CASE("self-tests are refused while capturing");
  {
    Fresh();
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    bh::RuntimePoll();
    BH_CHECK(bh::RuntimeSelfTestModel() == -1);
    BH_CHECK(bh::RuntimeRunSynthetic(1) == -1);
    BH_CHECK(!bh::RuntimeDumpPcm(0, 16));
    BH_CHECK(bh::RuntimeState() == bh::kRunCapturing);
    Drive();
    BH_CHECK(bh::RuntimeLastResult().state == bh::kRunDone);
  }

  BH_CASE("PCM and feature dumps decode back to the buffers");
  {
    Fresh();
    g_mic_kind = 1;
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    host_port::Clear();
    BH_CHECK(bh::RuntimeDumpPcm(0, bh::kTargetSamples));
    std::vector<uint8_t> pcm_bytes = DecodeBase64(LastDumpBody(host_port::Output()));
    BH_CHECK(pcm_bytes.size() == bh::kTargetSamples * 2);
    BH_CHECK(std::memcmp(pcm_bytes.data(), g_signal[1].data(), pcm_bytes.size()) == 0);
    BH_CHECK(Contains(host_port::Output(), "BIRDHOUSE DUMP BEGIN what=pcm_s16le seq=1 offset=0 count=80000 bytes=160000 crc="));
    host_port::Clear();
    BH_CHECK(bh::RuntimeDumpPcm(79990, 10));
    BH_CHECK(DecodeBase64(LastDumpBody(host_port::Output())).size() == 20);
    host_port::Clear();
    BH_CHECK(bh::RuntimeDumpFeatures(0, birdhouse::kFeatureElements));
    std::vector<uint8_t> feat = DecodeBase64(LastDumpBody(host_port::Output()));
    BH_CHECK(feat.size() == static_cast<size_t>(birdhouse::kFeatureElements));
    BH_CHECK(std::memcmp(feat.data(), bh::RuntimeFeatures(), feat.size()) == 0);
    BH_CHECK(!bh::RuntimeDumpPcm(0, 0));
    BH_CHECK(!bh::RuntimeDumpPcm(80000, 1));
    BH_CHECK(!bh::RuntimeDumpPcm(79999, 2));
    BH_CHECK(!bh::RuntimeDumpFeatures(9960, 1));
    BH_CHECK(!bh::RuntimeDumpFeatures(0, 9961));
  }

  BH_CASE("idle polling does nothing and prints nothing");
  {
    Fresh();
    for (int i = 0; i < 1000; ++i) bh::RuntimePoll();
    BH_CHECK(host_port::Output().empty());
    BH_CHECK(bh::RuntimeState() == bh::kRunIdle);
    BH_CHECK(fake_aud::counters().starts == 0);
  }

  BH_CASE("report lines are short, prefixed and free of format artefacts");
  {
    Fresh();
    BH_CHECK(bh::RuntimeRequestRuns(1) == 0);
    Drive();
    bh::RuntimePrintInfo();
    const std::string& out = host_port::Output();
    BH_CHECK(Contains(out, "BIRDHOUSE INFO version=" BH_VERSION));
    BH_CHECK(Contains(out, "model_bytes=59760"));
    size_t start = 0;
    while (start < out.size()) {
      size_t end = out.find('\n', start);
      if (end == std::string::npos) end = out.size();
      const std::string line = out.substr(start, end - start);
      BH_CHECK(line.compare(0, 10, "BIRDHOUSE ") == 0);
      BH_CHECK(line.size() <= 200);
      BH_CHECK(line.find('%') == std::string::npos);
      start = end + 1;
    }
  }

  BH_CASE("soak: 40 consecutive runs with alternating content");
  {
    Fresh();
    int ok = 0;
    for (int i = 0; i < 40; ++i) {
      g_mic_kind = i % bh::kSynthKindCount;
      if (bh::RuntimeRequestRuns(1) != 0) break;
      Drive();
      const bh::RunResult r = bh::RuntimeLastResult();
      if (r.state == bh::kRunDone && r.quality == bh::kQualityClean &&
          r.pcm_crc32 == g_expected[g_mic_kind].pcm_crc && r.output_q == g_expected[g_mic_kind].output_q) {
        ++ok;
      }
    }
    BH_CHECK(ok == 40);
    BH_CHECK(fake_aud::counters().starts == 40 && fake_aud::counters().stops == 40);
    BH_CHECK(fake_aud::counters().ring_overflows == 0);
  }

  return bh_test::Finish("runtime");
}

#include <atomic>
#include <cstddef>
#include <cstdint>

static_assert(
    ATOMIC_INT_LOCK_FREE == 2 &&
    ATOMIC_BOOL_LOCK_FREE == 2,
    "Target requires lock-free 32-bit and bool atomics");

namespace birdhouse {

class PdmMonoQueue {
 public:
  static const uint32_t kCapacity = 8192;
  static const uint32_t kBlockFrames = 1024;

  void Reset() {
    read_.store(0, std::memory_order_relaxed);
    write_.store(0, std::memory_order_relaxed);
    overflow_.store(false, std::memory_order_relaxed);
    startup_.store(0, std::memory_order_relaxed);
  }

  // Producer: DMA callback only.
  // This function performs no FFT.
  bool PushStereoBlock(const int16_t* stereo,
                       uint32_t frames) {
    if (!stereo || frames != kBlockFrames) return false;

    if (startup_.load(std::memory_order_relaxed) < 2) {
      startup_.fetch_add(1, std::memory_order_relaxed);
      return true;
    }

    if (overflow_.load(std::memory_order_relaxed))
      return false;

    const uint32_t w =
        write_.load(std::memory_order_relaxed);
    const uint32_t r =
        read_.load(std::memory_order_acquire);

    const uint32_t buffered = w - r;

    if (buffered > kCapacity ||
        frames > kCapacity - buffered) {
      overflow_.store(true, std::memory_order_relaxed);
      return false;
    }

    for (uint32_t i = 0; i < frames; ++i) {
      data_[(w + i) & (kCapacity - 1)] =
          stereo[2 * i];
    }

    write_.store(w + frames, std::memory_order_release);
    return true;
  }

  // Consumer: main program loop only.
  bool PopMono(int16_t* sample) {
    if (!sample) return false;

    const uint32_t r =
        read_.load(std::memory_order_relaxed);
    const uint32_t w =
        write_.load(std::memory_order_acquire);

    if (r == w) return false;

    *sample = data_[r & (kCapacity - 1)];

    read_.store(r + 1, std::memory_order_release);
    return true;
  }

  bool Overflowed() const {
    return overflow_.load(std::memory_order_relaxed);
  }

  uint32_t DroppedStartupBlocks() const {
    return startup_.load(std::memory_order_relaxed);
  }

 private:
  int16_t data_[kCapacity] = {};
  std::atomic<uint32_t> read_{0};
  std::atomic<uint32_t> write_{0};
  std::atomic<bool> overflow_{false};
  std::atomic<uint32_t> startup_{0};
};

}  // namespace birdhouse

namespace {
birdhouse::PdmMonoQueue g_queue;
}

extern "C" void birdhouse_queue_reset() {
  g_queue.Reset();
}

extern "C" int birdhouse_queue_push(
    const int16_t* stereo, uint32_t frames) {
  return g_queue.PushStereoBlock(stereo, frames) ? 1 : 0;
}

extern "C" int birdhouse_queue_pop(int16_t* sample) {
  return g_queue.PopMono(sample) ? 1 : 0;
}

extern "C" int birdhouse_queue_overflowed() {
  return g_queue.Overflowed() ? 1 : 0;
}

#ifdef BIRDHOUSE_HOST_TEST

#include <iostream>

static int16_t FakeSample(uint32_t i) {
  return static_cast<int16_t>(
      static_cast<int>((i * 37u) % 30001u) - 15000);
}

int main() {
  using namespace birdhouse;

  static PdmMonoQueue q;
  q.Reset();

  int16_t block[2 * PdmMonoQueue::kBlockFrames];

  uint32_t received = 0;
  uint32_t mismatches = 0;

  for (uint32_t b = 0; b < 81; ++b) {
    for (uint32_t i = 0; i < 1024; ++i) {
      const uint32_t global = b * 1024 + i;

      block[2 * i] = global < 2048
          ? 777
          : FakeSample(global - 2048);

      block[2 * i + 1] = -1234;
    }

    if (!q.PushStereoBlock(block, 1024)) {
      std::cout << "FAIL: unexpected overflow\n";
      return 1;
    }

    int16_t sample;

    while (q.PopMono(&sample)) {
      if (received < 80000 &&
          sample != FakeSample(received)) {
        ++mismatches;
      }
      ++received;
    }
  }

  std::cout << "Startup blocks dropped: "
            << q.DroppedStartupBlocks() << "\n";
  std::cout << "Mono samples received: "
            << received << "\n";
  std::cout << "First 80000 mismatches: "
            << mismatches << "\n";
  std::cout << "Queue workspace bytes: "
            << sizeof(q) << "\n";

  if (q.DroppedStartupBlocks() != 2 ||
      received != 80896 ||
      mismatches != 0 ||
      q.Overflowed()) {
    std::cout << "FAIL: queue data test\n";
    return 1;
  }

  // Check overflow detection separately.
  q.Reset();

  for (int i = 0; i < 2; ++i)
    q.PushStereoBlock(block, 1024);

  for (int i = 0; i < 8; ++i) {
    if (!q.PushStereoBlock(block, 1024)) {
      std::cout << "FAIL: premature overflow\n";
      return 1;
    }
  }

  const bool rejected =
      !q.PushStereoBlock(block, 1024);

  if (!rejected || !q.Overflowed()) {
    std::cout << "FAIL: overflow not detected\n";
    return 1;
  }

  std::cout << "Overflow detection: PASS\n";
  std::cout << "PASS: MONO AUDIO QUEUE\n";
  return 0;
}

#endif

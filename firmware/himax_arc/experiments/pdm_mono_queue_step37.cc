#include <cstddef>
#include <cstdint>

// Himax embARC SDK interrupt-management functions.
extern "C" uint32_t cpu_lock_save(void);
extern "C" void cpu_unlock_restore(uint32_t status);

#ifdef BIRDHOUSE_QUEUE_HOST_TEST
static volatile uint32_t g_locks = 0;
static volatile uint32_t g_unlocks = 0;

extern "C" uint32_t cpu_lock_save(void) {
  ++g_locks;
  return 0;
}

extern "C" void cpu_unlock_restore(uint32_t) {
  ++g_unlocks;
}
#endif

namespace birdhouse {

class PdmMonoQueue {
 public:
  static const uint32_t kCapacity = 8192;
  static const uint32_t kBlockFrames = 1024;

  // Only call when audio capture is stopped.
  void Reset() {
    read_ = 0;
    write_ = 0;
    dropped_blocks_ = 0;
    overflow_ = 0;
  }

  // Single producer: PDM callback.
  // Stereo layout: L,R,L,R,...
  bool PushStereoBlock(
      const int16_t* stereo,
      uint32_t frames) {

    if (!stereo || frames != kBlockFrames)
      return false;

    if (overflow_)
      return false;

    // Drop two initial blocks for PDM settling.
    if (dropped_blocks_ < 2) {
      ++dropped_blocks_;
      return true;
    }

    const uint32_t w = write_;
    const uint32_t r = read_;
    const uint32_t used = w - r;

    if (used > kCapacity ||
        frames > kCapacity - used) {
      overflow_ = 1;
      return false;
    }

    for (uint32_t i = 0; i < frames; ++i) {
      data_[(w + i) & (kCapacity - 1)] =
          stereo[2 * i];
    }

    // Compiler ordering barrier.
    __asm__ __volatile__("" ::: "memory");

    // Publish complete block.
    write_ = w + frames;
    return true;
  }

  // Single consumer: main loop only.
  bool PopMono(int16_t* sample) {
    if (!sample)
      return false;

    const uint32_t irq_state = cpu_lock_save();

    __asm__ __volatile__("" ::: "memory");

    bool ok = false;

    if (!overflow_ && read_ != write_) {
      *sample = data_[read_ & (kCapacity - 1)];
      ++read_;
      ok = true;
    }

    __asm__ __volatile__("" ::: "memory");

    cpu_unlock_restore(irq_state);
    return ok;
  }

  bool Overflowed() const {
    return overflow_ != 0;
  }

  uint32_t DroppedStartupBlocks() const {
    return dropped_blocks_;
  }

 private:
  int16_t data_[kCapacity] = {};

  volatile uint32_t read_ = 0;
  volatile uint32_t write_ = 0;
  volatile uint32_t dropped_blocks_ = 0;
  volatile uint32_t overflow_ = 0;
};

static PdmMonoQueue queue;

}  // namespace birdhouse

extern "C" void birdhouse_queue_reset_v2() {
  birdhouse::queue.Reset();
}

extern "C" int birdhouse_queue_push_v2(
    const int16_t* p, uint32_t n) {
  return birdhouse::queue.PushStereoBlock(p, n) ? 1 : 0;
}

extern "C" int birdhouse_queue_pop_v2(
    int16_t* p) {
  return birdhouse::queue.PopMono(p) ? 1 : 0;
}

extern "C" int birdhouse_queue_overflowed_v2() {
  return birdhouse::queue.Overflowed() ? 1 : 0;
}

#ifdef BIRDHOUSE_QUEUE_HOST_TEST

#include <iostream>

static int16_t Fake(uint32_t i) {
  return static_cast<int16_t>(
      static_cast<int>((i * 37u) % 30001u)
      - 15000);
}

int main() {
  using namespace birdhouse;

  queue.Reset();

  int16_t block[2 * PdmMonoQueue::kBlockFrames];

  uint32_t received = 0;
  uint32_t mismatches = 0;

  for (uint32_t b = 0; b < 81; ++b) {
    for (uint32_t i = 0; i < 1024; ++i) {
      const uint32_t global = b * 1024 + i;

      block[2 * i] =
          global < 2048
              ? 777
              : Fake(global - 2048);

      block[2 * i + 1] = -1234;
    }

    if (!queue.PushStereoBlock(block, 1024)) {
      std::cout << "FAIL: premature overflow\n";
      return 1;
    }

    int16_t value = 0;

    while (queue.PopMono(&value)) {
      if (received < 80000 &&
          value != Fake(received)) {
        ++mismatches;
      }
      ++received;
    }
  }

  std::cout << "Startup blocks dropped: "
            << queue.DroppedStartupBlocks() << "\n";

  std::cout << "Mono samples received: "
            << received << "\n";

  std::cout << "First 80000 mismatches: "
            << mismatches << "\n";

  std::cout << "Queue workspace bytes: "
            << sizeof(queue) << "\n";

  if (received != 80896 ||
      mismatches != 0 ||
      queue.Overflowed() ||
      queue.DroppedStartupBlocks() != 2) {
    std::cout << "FAIL: queue parity\n";
    return 2;
  }

  // Test sticky overflow detection.
  queue.Reset();

  for (int i = 0; i < 10; ++i) {
    if (!queue.PushStereoBlock(block, 1024))
      return 3;
  }

  const bool rejected =
      !queue.PushStereoBlock(block, 1024);

  if (!rejected || !queue.Overflowed())
    return 4;

  int16_t sample = 0;

  if (queue.PopMono(&sample))
    return 5;

  if (g_locks != g_unlocks || g_locks == 0)
    return 6;

  std::cout << "Overflow detection: PASS\n";
  std::cout << "Balanced interrupt guards: PASS\n";
  std::cout << "PASS: HIMAX IRQ-GUARDED MONO QUEUE HOST TEST\n";

  return 0;
}

#endif

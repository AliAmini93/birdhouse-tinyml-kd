// Opt-in, one-attempt PDM shutdown observer. No start/reset/acknowledge API.
#ifndef BIRDHOUSE_HIMAX_BH_PDM_DIAG_H_
#define BIRDHOUSE_HIMAX_BH_PDM_DIAG_H_
#include <cstdint>

const uint32_t kBhPdmDmaChannel = 4;  // pinned board/24 IO_PDM_RX0_DMA; ARC asserts it
const uint32_t kBhPdmDmaMask = 1u << kBhPdmDmaChannel;
const uint32_t kBhPdmDiagValid = 15;  // busy, completion history, error, DMA IRQ
const uint32_t kBhPdmDiagSamples = 32;
const uint32_t kBhPdmDiagStepUs = 16000;
const uint32_t kBhPdmDiagWindowUs = kBhPdmDiagSamples * kBhPdmDiagStepUs;
const uint32_t kBhPdmDiagPollBudget = 1000000;

struct BhPdmDmaStatus { uint32_t valid, busy, complete, error, irq; };
enum BhPdmDiagVerdict { kBhDmaInconclusive = 0, kBhDmaObservedPass = 1, kBhDmaObservedFail = 2 };
struct BhPdmDiagRow {
  uint32_t phase;  // 0 before vendor stop, 1 first after return, 2 timed post sample
  uint32_t elapsed_us;
  BhPdmDmaStatus dma;  // sequential reads, NOT an atomic hardware snapshot
  uint32_t late_callbacks;
  uint32_t enable_attempts;
  uint32_t changed_words;  // exact comparison with previous scan; never raw audio
};
struct BhPdmDiagReport {
  bool armed, finished, window_complete, clock_invalid, budget_exhausted;
  int stop_rc;
  uint32_t rows, max_gap_us, post_enable_attempt, during_stop_enable_attempt;
  BhPdmDiagVerdict verdict;  // sampled observation only; full quiescence UNOBSERVABLE
  BhPdmDiagRow row[kBhPdmDiagSamples + 2];
};

// Main context only. Arm once before any capture; never lifts P1 quarantine.
int bh_port_pdm_diag_arm();
const BhPdmDiagReport& bh_port_pdm_diag_report();
void bh_port_pdm_diag_print();  // stored records only, no hardware read
// Called by the forwarding DMA-enable wrapper, including ISR context.
// Bounded word stores only; never prints, masks, reads PCM or changes DMA.
void bh_port_pdm_diag_enable_event(uint32_t mask, int enable);

// Platform read-only primitives. Unknown fields must be invalid, never zero-PASS.
BhPdmDmaStatus bh_port_pdm_diag_read_status();
uint32_t bh_port_pdm_diag_read_word(const uint32_t* word);
#endif

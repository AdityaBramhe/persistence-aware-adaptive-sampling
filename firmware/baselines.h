#ifndef BASELINES_H
#define BASELINES_H

#include <math.h>
#include "config.h"

// =============================================================================
//  baselines.h
//  Baseline 1 (fixed-rate reference) and Baseline 2 (simple threshold-based
//  adaptive sampling). Both are independent of the VAR/TRD/SFI classifier --
//  the classifier still runs in parallel in every mode as a diagnostic
//  cross-check (see sketch.ino), but it is these two functions -- not the
//  classifier -- that actually control FIXED_RATE / THRESHOLD_BASELINE
//  scheduling.
// =============================================================================

// Baseline 2: |x_t - x_(t-1)| > THRESHOLD_VALUE -> short interval, else long.
struct ThresholdBaselineState {
  float lastValue;
  bool hasLast;
};

static inline void tb_init(ThresholdBaselineState &t) {
  t.lastValue = 0.0f;
  t.hasLast = false;
}

// Returns the next sampling interval (ms) and updates lastValue. Call exactly
// once per acquisition cycle, regardless of experiment mode (see sketch.ino
// -- this keeps the delta bookkeeping correct even when THRESHOLD_BASELINE
// is not the active mode, in case it's needed for diagnostic parity).
static inline unsigned long tb_update(ThresholdBaselineState &t, float normalizedReading) {
  unsigned long interval;
  if (!t.hasLast) {
    interval = 1000UL;   // first reading: no delta available yet
  } else {
    float delta = fabs(normalizedReading - t.lastValue);
    interval = (delta > THRESHOLD_VALUE) ? 1000UL : 4000UL;
  }
  t.lastValue = normalizedReading;
  t.hasLast = true;
  return interval;
}

#endif // BASELINES_H

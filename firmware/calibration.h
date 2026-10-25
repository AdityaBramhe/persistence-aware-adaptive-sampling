#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <stdint.h>
#include <math.h>
#include "config.h"
#include "feature_extraction.h"

// =============================================================================
//  calibration.h
//  One-time per-sensor calibration baseline. Computed from the first
//  CALIBRATION_SAMPLES normalized readings collected immediately after the
//  WARMUP_SAMPLES gate, before adaptive control begins. VAR_base / sigma_base
//  are then fixed for the rest of the run and used to normalize VAR/TRD/SFI
//  into scale-independent NVI/NTD -- this is what makes the classification
//  thresholds channel-agnostic instead of tuned to one specific noise level.
// =============================================================================

struct CalibrationState {
  float samples[CALIBRATION_SAMPLES];
  uint8_t count;
  bool done;
  float varBase;
  float sigmaBase;
};

static inline void cal_init(CalibrationState &c) {
  c.count = 0;
  c.done = false;
  c.varBase = 0.0f;
  c.sigmaBase = 0.0f;
}

// Feed one post-warmup normalized reading. Returns true on the cycle
// calibration completes (caller should log a CALIBRATION_DONE line then).
static inline bool cal_feed(CalibrationState &c, float normalizedReading) {
  if (c.done) return false;
  if (c.count < CALIBRATION_SAMPLES) {
    c.samples[c.count] = normalizedReading;
    c.count++;
  }
  if (c.count >= CALIBRATION_SAMPLES && !c.done) {
    c.varBase = fe_variance(c.samples, CALIBRATION_SAMPLES);
    c.sigmaBase = sqrt(c.varBase);
    c.done = true;
    return true;
  }
  return false;
}

#endif // CALIBRATION_H

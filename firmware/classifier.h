#ifndef CLASSIFIER_H
#define CLASSIFIER_H

#include <stdint.h>
#include "config.h"

// =============================================================================
//  classifier.h
//  Operational-state classification: S (Stable) / M (Moderate variation) /
//  V (High variation) / U (Unstable). Thresholds apply to NORMALIZED
//  indicators (NVI, NTD) plus the raw SFI reversal count.
//
//  INDICATOR_SET selects the RQ3 ablation: a dropped indicator's condition
//  is treated as always-satisfied, so it cannot by itself block a tighter
//  state -- "reuse the same breakpoints, drop the omitted indicator's check".
// =============================================================================

enum OpState : uint8_t { STATE_S = 0, STATE_M = 1, STATE_V = 2, STATE_U = 3 };

static inline const char* stateLabel(OpState s) {
  switch (s) {
    case STATE_S: return "S";
    case STATE_M: return "M";
    case STATE_V: return "V";
    default:      return "U";
  }
}

struct StateThreshold {
  float nviMax;
  float ntdMax;
  int   sfiMax;
};

// Nominal thresholds (multiplier = 1.0). For the S8/S13 sensitivity sweep,
// pass 0.7f / 1.3f as thresholdMultiplier to classify() instead of editing
// these values directly.
static const StateThreshold THRESH_S = { 1.5f, 1.0f, 2 };
static const StateThreshold THRESH_M = { 4.0f, 3.0f, 5 };
static const StateThreshold THRESH_V = { 10.0f, 8.0f, 8 };

static inline bool thresholdHolds(const StateThreshold &t, float nvi, float ntd, int sfi,
                                   bool checkVar, bool checkTrd, bool checkSfi,
                                   float mult) {
  if (checkVar && !(nvi < t.nviMax * mult)) return false;
  if (checkTrd && !(ntd < t.ntdMax * mult)) return false;
  if (checkSfi && !(sfi <= t.sfiMax)) return false;   // integer count, not scaled
  return true;
}

static inline OpState classify(float nvi, float ntd, int sfi, uint8_t indicatorSet,
                                float thresholdMultiplier) {
  bool checkVar = true;                                   // VAR always included
  bool checkTrd = (indicatorSet != INDICATOR_VAR_ONLY);
  bool checkSfi = (indicatorSet == INDICATOR_FULL);

  if (thresholdHolds(THRESH_S, nvi, ntd, sfi, checkVar, checkTrd, checkSfi, thresholdMultiplier)) return STATE_S;
  if (thresholdHolds(THRESH_M, nvi, ntd, sfi, checkVar, checkTrd, checkSfi, thresholdMultiplier)) return STATE_M;
  if (thresholdHolds(THRESH_V, nvi, ntd, sfi, checkVar, checkTrd, checkSfi, thresholdMultiplier)) return STATE_V;
  return STATE_U;
}

// State-indexed sampling-interval policy.
static inline unsigned long intervalForState(OpState s) {
  switch (s) {
    case STATE_S: return 1000UL;
    case STATE_M: return 2000UL;
    case STATE_V: return 4000UL;
    default:      return 8000UL;   // STATE_U
  }
}

#endif // CLASSIFIER_H

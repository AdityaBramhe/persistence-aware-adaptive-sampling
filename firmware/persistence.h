#ifndef PERSISTENCE_H
#define PERSISTENCE_H

#include <stdint.h>
#include "classifier.h"

// =============================================================================
//  persistence.h -- K-consecutive persistence confirmation.
//
//  K is a CLASSIFICATION-CYCLE count, NOT a time duration. Because sampling
//  interval is state-dependent, the wall-clock time a given K represents
//  varies with the currently-confirmed state (S=1s .. U=8s per cycle).
//  Confirmation latency is therefore measured separately, in milliseconds,
//  by comparing timestamps in the caller (see logEventResponse in sketch.ino)
//  -- never inferred from K itself.
//
//  Formal event definitions (used for Transition Suppression Rate, TSR):
//    raw transition         : raw_t != raw_(t-1)
//    candidate-state update : reassigned exactly when raw_state != candidate
//                              -- i.e. the SAME event as a raw transition in
//                              this implementation. Stated explicitly so the
//                              paper does not imply two independently
//                              countable events where there is only one.
//    confirmed transition   : confirmed_t != confirmed_(t-1), gated by
//                              run_length >= K.
// =============================================================================

struct PersistenceState {
  OpState rawPrev;
  OpState candidate;
  OpState confirmed;
  uint16_t runLength;
  bool initialized;

  // TSR = (rawTransitions - confirmedTransitions) / rawTransitions * 100
  uint32_t rawTransitions;
  uint32_t confirmedTransitions;
};

static inline void pers_init(PersistenceState &p, OpState initialState) {
  p.rawPrev = initialState;
  p.candidate = initialState;
  p.confirmed = initialState;
  p.runLength = 1;
  p.initialized = true;
  p.rawTransitions = 0;
  p.confirmedTransitions = 0;
}

// Feed one new raw classification. Returns true iff a CONFIRMED transition
// happened this cycle (confirmed_state just changed).
static inline bool pers_update(PersistenceState &p, OpState rawState, uint16_t K) {
  if (!p.initialized) {
    pers_init(p, rawState);
    return false;
  }

  if (rawState != p.rawPrev) {
    p.rawTransitions++;
  }
  p.rawPrev = rawState;

  if (rawState == p.candidate) {
    if (p.runLength < 0xFFFF) p.runLength++;
  } else {
    p.candidate = rawState;   // candidate-state update
    p.runLength = 1;
  }

  bool confirmedTransitionThisCycle = false;
  if (p.runLength >= K && p.candidate != p.confirmed) {
    p.confirmed = p.candidate;
    p.confirmedTransitions++;
    confirmedTransitionThisCycle = true;
  }
  return confirmedTransitionThisCycle;
}

// Transition Suppression Rate, formally defined. Returns false (undefined)
// if there have been no raw transitions yet -- report as "n/a", never as a
// misleading 0%.
static inline bool pers_computeTSR(const PersistenceState &p, float &tsrOut) {
  if (p.rawTransitions == 0) return false;
  tsrOut = 100.0f * (float)(p.rawTransitions - p.confirmedTransitions) / (float)p.rawTransitions;
  return true;
}

#endif // PERSISTENCE_H

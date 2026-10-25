#ifndef FEATURE_EXTRACTION_H
#define FEATURE_EXTRACTION_H

#include <stdint.h>
#include "config.h"

// =============================================================================
//  feature_extraction.h
//  Sliding window (per sensor) + raw VAR / TRD / SFI.
//  Values stored are NORMALIZED readings in [0, 1] (raw ADC / 1023.0).
// =============================================================================

struct SlidingWindow {
  float buf[WINDOW_SIZE];
  uint8_t count;   // number of valid samples currently held (caps at WINDOW_SIZE)
  uint8_t head;    // next write position (circular)
};

static inline void fe_init(SlidingWindow &w) {
  w.count = 0;
  w.head = 0;
  for (uint8_t i = 0; i < WINDOW_SIZE; i++) w.buf[i] = 0.0f;
}

static inline void fe_push(SlidingWindow &w, float normalizedReading) {
  w.buf[w.head] = normalizedReading;
  w.head = (uint8_t)((w.head + 1) % WINDOW_SIZE);
  if (w.count < WINDOW_SIZE) w.count++;
}

// Writes samples oldest-to-newest into `out` (length = w.count).
// Caller must size `out` to at least WINDOW_SIZE.
static inline void fe_ordered(const SlidingWindow &w, float *out) {
  uint8_t n = w.count;
  uint8_t start = (w.count < WINDOW_SIZE) ? 0 : w.head;   // oldest index
  for (uint8_t i = 0; i < n; i++) {
    out[i] = w.buf[(uint8_t)((start + i) % WINDOW_SIZE)];
  }
}

// VAR: population variance of the current window.
static inline float fe_variance(const float *x, uint8_t n) {
  if (n == 0) return 0.0f;
  float mean = 0.0f;
  for (uint8_t i = 0; i < n; i++) mean += x[i];
  mean /= (float)n;
  float var = 0.0f;
  for (uint8_t i = 0; i < n; i++) {
    float d = x[i] - mean;
    var += d * d;
  }
  return var / (float)n;
}

// TRD: recent-half mean minus old-half mean (signed).
static inline float fe_trend(const float *x, uint8_t n) {
  if (n < 2) return 0.0f;
  uint8_t h = n / 2;
  uint8_t recentCount = n - h;
  float oldMean = 0.0f, recentMean = 0.0f;
  for (uint8_t i = 0; i < h; i++) oldMean += x[i];
  oldMean /= (float)h;
  for (uint8_t i = h; i < n; i++) recentMean += x[i];
  recentMean /= (float)recentCount;
  return recentMean - oldMean;
}

// SFI: direction-reversal count over consecutive differences, with a
// dead-band to suppress noise-level fluctuations. A zero-difference step
// (|d| <= deadband) carries the previous nonzero direction forward rather
// than resetting it, matching the design's reversal-counting definition.
static inline int fe_reversalCount(const float *x, uint8_t n, float deadband) {
  if (n < 3) return 0;
  int reversals = 0;
  int prevSign = 0;    // -1, 0, +1
  int lastNonzeroSign = 0;
  for (uint8_t i = 1; i < n; i++) {
    float d = x[i] - x[i - 1];
    int sign;
    if (d > deadband) sign = 1;
    else if (d < -deadband) sign = -1;
    else sign = lastNonzeroSign;   // carry forward through the dead-band

    if (i >= 2 && sign != 0 && prevSign != 0 && sign != prevSign) {
      reversals++;
    }
    if (sign != 0) lastNonzeroSign = sign;
    prevSign = sign;
  }
  return reversals;
}

#endif // FEATURE_EXTRACTION_H

#ifndef SIGNAL_GENERATOR_H
#define SIGNAL_GENERATOR_H

#include "config.h"

// =============================================================================
//  signal_generator.h -- deterministic, seed-parameterized synthetic signal.
//
//  The simulated reading at sensor s, time t (ms), for a given seed, is a
//  pure function of (s, t, seed) -- it does NOT depend on how often the
//  controller happens to sample sensor s. This is what makes "paired seeded
//  trials" valid: two different sampling policies observing the SAME
//  underlying process at different moments, not two different processes.
//
//    - Noise: hash-based, depends on (s, t, seed) -> changes across trials
//             when RANDOM_SEED changes, reproducible for a fixed seed.
//    - Drift: scripted ground-truth event, depends on (s, t) ONLY -> stays
//             fixed across seeds, so latency/ARR stay comparable trial to
//             trial for the same scenario.
// =============================================================================

static inline unsigned long sg_hash(unsigned long a, unsigned long b, unsigned long c) {
  unsigned long h = a * 0x9E3779B1UL;
  h ^= b + 0x85EBCA6BUL + (h << 6) + (h >> 2);
  h ^= c + 0xC2B2AE35UL + (h << 6) + (h >> 2);
  h ^= (h >> 15);
  h *= 0x27D4EB2FUL;
  h ^= (h >> 13);
  return h;
}

// Deterministic noise offset in [-amplitude, +amplitude] (ADC counts).
static inline int sg_noise(int sensorIndex, unsigned long elapsedMs, unsigned long seed, int amplitude) {
  if (amplitude <= 0) return 0;
  unsigned long h = sg_hash((unsigned long)sensorIndex, elapsedMs, seed);
  long range = 2L * (long)amplitude + 1L;
  long val = (long)(h % (unsigned long)range) - (long)amplitude;
  return (int)val;
}

// Scripted, seed-independent drift (ADC counts) for sensor `s` at time t (ms).
// Sensor indices: 0=S1, 1=S2, 2=S3, 3=S4.
static inline float sg_drift(int s, unsigned long elapsedMs, int scenarioMode) {
  unsigned long t_s = elapsedMs / 1000UL;

  if (scenarioMode == MODE_GRADUAL_CHANGE || scenarioMode == MODE_MIXED_SENSORS) {
    if (s == GRADUAL_EVENT_SENSOR &&
        t_s >= (unsigned long)GRADUAL_EVENT_START_S && t_s <= (unsigned long)GRADUAL_EVENT_END_S) {
      float span = (float)(GRADUAL_EVENT_END_S - GRADUAL_EVENT_START_S);
      float progress = (float)(t_s - (unsigned long)GRADUAL_EVENT_START_S) / span;
      return 60.0f * progress;                                  // ramp to +60 counts
    }
  }

  if (scenarioMode == MODE_SUDDEN_DISTURBANCE || scenarioMode == MODE_MIXED_SENSORS) {
    if (s == SUDDEN_EVENT_SENSOR &&
        t_s >= (unsigned long)SUDDEN_EVENT_START_S && t_s < (unsigned long)SUDDEN_EVENT_END_S) {
      return 220.0f;                                            // step to +220 counts
    }
  }

  if (scenarioMode == MODE_TRANSIENT_DISTURBANCE && s == TRANSIENT_EVENT_SENSOR) {
    unsigned long startMs = (unsigned long)TRANSIENT_EVENT_START_S * 1000UL;
    if (elapsedMs >= startMs && elapsedMs < startMs + TRANSIENT_EVENT_DURATION_MS) {
      return 220.0f;                                            // same step size, short-lived
    }
  }

  return 0.0f;   // MODE_STABLE, or no event active right now
}

// Noise amplitude for sensor `s` under this scenario. MIXED_SENSORS and
// STABLE keep every channel's own default amplitude (so e.g. S4's large
// default noise -- not a scripted event -- drives its own behaviour).
// Single-event scenarios use a low uniform background amplitude on
// non-target channels so the targeted channel's event dominates.
static inline int sg_amplitudeFor(int s, int scenarioMode) {
  if (scenarioMode == MODE_MIXED_SENSORS || scenarioMode == MODE_STABLE) {
    return NOISE_AMPLITUDE[s];
  }
  bool isTarget =
      (scenarioMode == MODE_GRADUAL_CHANGE      && s == GRADUAL_EVENT_SENSOR) ||
      (scenarioMode == MODE_SUDDEN_DISTURBANCE  && s == SUDDEN_EVENT_SENSOR)  ||
      (scenarioMode == MODE_TRANSIENT_DISTURBANCE && s == TRANSIENT_EVENT_SENSOR);
  return isTarget ? NOISE_AMPLITUDE[s] : (int)STABLE_NOISE_AMPLITUDE;
}

// Full simulated raw ADC reading (0-1023) for sensor `s`. Combines the live
// potentiometer position (baseline -- interactive in Wokwi) with scripted
// drift and deterministic seeded noise, clamped to the ADC range. Leave the
// potentiometer at its minimum position for reproducible experiments; turning
// it live during a run is a valid (if uncontrolled) extra disturbance.
static inline int sg_readSimulated(int s, int pinRawAdc, unsigned long elapsedMs,
                                    unsigned long seed, int scenarioMode) {
  int amp = sg_amplitudeFor(s, scenarioMode);
  int noise = sg_noise(s, elapsedMs, seed, amp);
  float drift = sg_drift(s, elapsedMs, scenarioMode);
  long value = (long)pinRawAdc + (long)noise + (long)drift;
  if (value < 0) value = 0;
  if (value > 1023) value = 1023;
  return (int)value;
}

// Baseline modes (FIXED_RATE / THRESHOLD_BASELINE) borrow a scenario's
// signal so they are compared against the same headline process.
static inline int sg_effectiveScenario(int experimentMode) {
  if (experimentMode == MODE_FIXED_RATE || experimentMode == MODE_THRESHOLD_BASELINE) {
    return BASELINE_SIGNAL_SOURCE;
  }
  return experimentMode;
}

#endif // SIGNAL_GENERATOR_H
#ifndef LOGGER_H
#define LOGGER_H

#include "config.h"
#include "classifier.h"

// =============================================================================
//  logger.h -- all Serial output.
//
//  Every line starts with a tag (DATA, WARMUP, CALIBRATION, GROUND_TRUTH,
//  EVENT_RESPONSE, SENSOR_SUMMARY, ...) so a raw Serial Monitor capture can be
//  split into a clean table with a one-line filter (see README "Parsing the
//  log" / parse_log.py). The column order for DATA rows is printed once in
//  the banner so the log is self-describing without external documentation.
// =============================================================================

static inline const char* modeName(int mode) {
  switch (mode) {
    case MODE_FIXED_RATE:            return "FIXED_RATE";
    case MODE_THRESHOLD_BASELINE:    return "THRESHOLD_BASELINE";
    case MODE_STABLE:                return "STABLE";
    case MODE_GRADUAL_CHANGE:        return "GRADUAL_CHANGE";
    case MODE_SUDDEN_DISTURBANCE:    return "SUDDEN_DISTURBANCE";
    case MODE_MIXED_SENSORS:         return "MIXED_SENSORS";
    case MODE_TRANSIENT_DISTURBANCE: return "TRANSIENT_DISTURBANCE";
    default:                         return "UNKNOWN_MODE";
  }
}

static inline const char* indicatorSetName(int s) {
  switch (s) {
    case INDICATOR_VAR_ONLY: return "VAR";
    case INDICATOR_VAR_TRD:  return "VAR_TRD";
    case INDICATOR_FULL:     return "VAR_TRD_SFI";
    default:                 return "UNKNOWN";
  }
}

static inline void logBanner() {
  Serial.println();
  Serial.println(F("====================================================================="));
  Serial.println(F(" Persistence-Aware Adaptive Sampling -- v4 locked design, sketch build"));
  Serial.println(F("====================================================================="));
  Serial.print(F("RUN_CONFIG,mode="));         Serial.print(modeName(EXPERIMENT_MODE));
  Serial.print(F(",indicator_set="));           Serial.print(indicatorSetName(INDICATOR_SET));
  Serial.print(F(",K="));                       Serial.print(PERSISTENCE_K);
  Serial.print(F(",seed="));                    Serial.print(RANDOM_SEED);
  Serial.print(F(",observation_window_s="));    Serial.println(OBSERVATION_WINDOW_MS / 1000UL);
  Serial.println();
  Serial.println(F("Column key, DATA rows:"));
  Serial.println(F("DATA,t_ms,sensor,raw_adc,x_norm,VAR,TRD,SFI,NVI,NTD,raw_state,candidate_state,run_len,confirmed_state,interval_ms,confirmed_transition"));
  Serial.println(F("(raw/candidate/confirmed state letters: S=Stable, M=Moderate variation, V=High variation, U=Unstable)"));
  Serial.println();
}

static inline void logWarmup(unsigned long t, int sensor, int adc) {
  Serial.print(F("WARMUP,")); Serial.print(t); Serial.print(',');
  Serial.print(sensor); Serial.print(','); Serial.println(adc);
}

static inline void logCalibrationDone(unsigned long t, int sensor, float varBase, float sigmaBase) {
  Serial.print(F("CALIBRATION_DONE,")); Serial.print(t); Serial.print(',');
  Serial.print(sensor); Serial.print(F(",VAR_base=")); Serial.print(varBase, 8);
  Serial.print(F(",sigma_base=")); Serial.println(sigmaBase, 6);
}

static inline void logData(unsigned long t, int sensor, int adc, float xNorm,
                            float var_, float trd_, int sfi_, float nvi, float ntd,
                            OpState rawState, OpState candidateState, uint16_t runLen,
                            OpState confirmedState, unsigned long intervalMs,
                            bool confirmedTransition) {
  Serial.print(F("DATA,"));
  Serial.print(t); Serial.print(',');
  Serial.print(sensor); Serial.print(',');
  Serial.print(adc); Serial.print(',');
  Serial.print(xNorm, 4); Serial.print(',');
  Serial.print(var_, 6); Serial.print(',');
  Serial.print(trd_, 6); Serial.print(',');
  Serial.print(sfi_); Serial.print(',');
  Serial.print(nvi, 4); Serial.print(',');
  Serial.print(ntd, 4); Serial.print(',');
  Serial.print(stateLabel(rawState)); Serial.print(',');
  Serial.print(stateLabel(candidateState)); Serial.print(',');
  Serial.print(runLen); Serial.print(',');
  Serial.print(stateLabel(confirmedState)); Serial.print(',');
  Serial.print(intervalMs); Serial.print(',');
  Serial.println(confirmedTransition ? 1 : 0);
}

static inline void logGroundTruth(unsigned long t, int sensor, const char *eventName) {
  Serial.print(F("GROUND_TRUTH,")); Serial.print(t); Serial.print(',');
  Serial.print(sensor); Serial.print(','); Serial.println(eventName);
}

static inline void logEventResponse(unsigned long tEvent, unsigned long tConfirmed, int sensor) {
  Serial.print(F("EVENT_RESPONSE,sensor=")); Serial.print(sensor);
  Serial.print(F(",t_event_ms=")); Serial.print(tEvent);
  Serial.print(F(",t_confirmed_ms=")); Serial.print(tConfirmed);
  Serial.print(F(",latency_ms=")); Serial.println(tConfirmed - tEvent);
}

#endif // LOGGER_H
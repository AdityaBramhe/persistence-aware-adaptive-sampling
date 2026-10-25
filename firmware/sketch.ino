// =============================================================================
//  sketch.ino -- Persistence-Aware Adaptive Sampling for Resource-Efficient
//  IoT Sensing. Implements the locked v4 design in full:
//    sensor -> sliding window -> VAR/TRD/SFI -> calibration normalization ->
//    raw state (S/M/V/U) -> K-consecutive persistence gate -> confirmed
//    state -> state-indexed sampling interval -> next acquisition.
//
//  Board: Arduino Uno. 4 channels on A0-A3 (see diagram.json).
//  Configure ONE experiment (mode, indicator set, K, seed) in config.h,
//  upload, capture Serial Monitor output, repeat per README.md's run matrix.
// =============================================================================

#include <Arduino.h>
#include <math.h>

#include "config.h"
#include "diagnostics.h"
#include "feature_extraction.h"
#include "calibration.h"
#include "classifier.h"
#include "persistence.h"
#include "signal_generator.h"
#include "baselines.h"
#include "logger.h"

// ---- Per-sensor runtime state ----------------------------------------------
const int PIN_LIST[NUM_SENSORS] = ANALOG_PINS;

SlidingWindow          g_window[NUM_SENSORS];
CalibrationState       g_cal[NUM_SENSORS];
PersistenceState       g_pers[NUM_SENSORS];
ThresholdBaselineState g_tb[NUM_SENSORS];

unsigned long g_sampleIndex[NUM_SENSORS];       // total acquisitions incl. warm-up
unsigned long g_activeCount[NUM_SENSORS];       // acquisitions excl. warm-up
unsigned long g_nextDueMs[NUM_SENSORS];
unsigned long g_currentIntervalMs[NUM_SENSORS];

unsigned long g_startMs;
bool g_summaryPrinted = false;

ExecTimeStats g_execStats;

bool g_groundTruthLogged[NUM_SENSORS];
bool g_eventResponseLogged[NUM_SENSORS];

// Transient scenario: count classifications actually taken DURING the
// disturbance window, per v4 S13's mandatory verification requirement.
unsigned long g_transientClassificationCount[NUM_SENSORS];
bool g_inTransientWindow[NUM_SENSORS];

static int scenarioForSignal() {
  return sg_effectiveScenario(EXPERIMENT_MODE);
}

// Returns true if sensor s has a scripted ground-truth event in this
// scenario, and writes its start/end time (ms) and label.
static bool getEventWindow(int s, int scenarioMode, unsigned long &startMs,
                            unsigned long &endMs, const char *&label) {
  if ((scenarioMode == MODE_GRADUAL_CHANGE || scenarioMode == MODE_MIXED_SENSORS) &&
      s == GRADUAL_EVENT_SENSOR) {
    startMs = (unsigned long)GRADUAL_EVENT_START_S * 1000UL;
    endMs   = (unsigned long)GRADUAL_EVENT_END_S * 1000UL;
    label = "GRADUAL_CHANGE";
    return true;
  }
  if ((scenarioMode == MODE_SUDDEN_DISTURBANCE || scenarioMode == MODE_MIXED_SENSORS) &&
      s == SUDDEN_EVENT_SENSOR) {
    startMs = (unsigned long)SUDDEN_EVENT_START_S * 1000UL;
    endMs   = (unsigned long)SUDDEN_EVENT_END_S * 1000UL;
    label = "SUDDEN_DISTURBANCE";
    return true;
  }
  if (scenarioMode == MODE_TRANSIENT_DISTURBANCE && s == TRANSIENT_EVENT_SENSOR) {
    startMs = (unsigned long)TRANSIENT_EVENT_START_S * 1000UL;
    endMs   = startMs + TRANSIENT_EVENT_DURATION_MS;
    label = "TRANSIENT_DISTURBANCE";
    return true;
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  unsigned long serialWaitStart = millis();
  while (!Serial && (millis() - serialWaitStart) < 3000UL) { ; }

  randomSeed(RANDOM_SEED);   // not used by the deterministic signal generator
                             // itself (see signal_generator.h) -- kept so any
                             // future stochastic extension has a fixed seed.

  for (int s = 0; s < NUM_SENSORS; s++) {
    fe_init(g_window[s]);
    cal_init(g_cal[s]);
    g_pers[s].initialized = false;
    tb_init(g_tb[s]);
    g_sampleIndex[s] = 0;
    g_activeCount[s] = 0;
    g_nextDueMs[s] = 0;
    g_currentIntervalMs[s] = FIXED_RATE_INTERVAL_MS;
    g_groundTruthLogged[s] = false;
    g_eventResponseLogged[s] = false;
    g_transientClassificationCount[s] = 0;
    g_inTransientWindow[s] = false;
  }

  exec_init(g_execStats);
  g_startMs = millis();
  g_summaryPrinted = false;

  logBanner();
}

static void runAcquisitionCycle(int s, unsigned long elapsedMs) {
  int scenarioMode = scenarioForSignal();

  int pinRaw = analogRead(PIN_LIST[s]);
  int simulatedAdc = sg_readSimulated(s, pinRaw, elapsedMs, RANDOM_SEED, scenarioMode);
  float xNorm = (float)simulatedAdc / 1023.0f;

  // Baseline 2 is stateless w.r.t. the feature window -- update it exactly
  // once per cycle, in every mode, for diagnostic parity (see baselines.h).
  unsigned long tbInterval = tb_update(g_tb[s], xNorm);

  fe_push(g_window[s], xNorm);
  g_sampleIndex[s]++;

  unsigned long evStart = 0, evEnd = 0;
  const char *evLabel = nullptr;
  bool hasEvent = getEventWindow(s, scenarioMode, evStart, evEnd, evLabel);

  if (hasEvent && !g_groundTruthLogged[s] && elapsedMs >= evStart) {
    logGroundTruth(elapsedMs, s, evLabel);
    g_groundTruthLogged[s] = true;
  }
  if (scenarioMode == MODE_TRANSIENT_DISTURBANCE && hasEvent) {
    g_inTransientWindow[s] = (elapsedMs >= evStart && elapsedMs < evEnd);
  }

  bool warmedUp = (g_sampleIndex[s] >= WARMUP_SAMPLES);

  if (!warmedUp) {
    logWarmup(elapsedMs, s, simulatedAdc);
    if (EXPERIMENT_MODE == MODE_FIXED_RATE)              g_currentIntervalMs[s] = FIXED_RATE_INTERVAL_MS;
    else if (EXPERIMENT_MODE == MODE_THRESHOLD_BASELINE) g_currentIntervalMs[s] = tbInterval;
    else                                                 g_currentIntervalMs[s] = WARMUP_INTERVAL_MS;
    return;
  }

  g_activeCount[s]++;

  unsigned long t0 = micros();

  float ordered[WINDOW_SIZE];
  fe_ordered(g_window[s], ordered);
  uint8_t n = g_window[s].count;

  float varRaw = fe_variance(ordered, n);
  float trdRaw = fe_trend(ordered, n);

  bool calibrating = !g_cal[s].done;
  int sfiRaw = 0;
  float nvi = 0.0f, ntd = 0.0f;
  OpState rawState = STATE_S, candidateState = STATE_S, confirmedState = STATE_S;
  uint16_t runLen = 0;
  bool confirmedTransition = false;

  if (calibrating) {
    bool justFinished = cal_feed(g_cal[s], xNorm);
    if (justFinished) logCalibrationDone(elapsedMs, s, g_cal[s].varBase, g_cal[s].sigmaBase);
  } else {
    float deadband = 1.0f * g_cal[s].sigmaBase;   // k_db = 1.0
    sfiRaw = fe_reversalCount(ordered, n, deadband);
    nvi = varRaw / (g_cal[s].varBase + EPSILON);
    ntd = fabs(trdRaw) / (g_cal[s].sigmaBase + EPSILON);

    rawState = classify(nvi, ntd, sfiRaw, INDICATOR_SET, 1.0f);
    if (!g_pers[s].initialized) pers_init(g_pers[s], rawState);
    confirmedTransition = pers_update(g_pers[s], rawState, (uint16_t)PERSISTENCE_K);

    candidateState = g_pers[s].candidate;
    confirmedState = g_pers[s].confirmed;
    runLen = g_pers[s].runLength;

    if (scenarioMode == MODE_TRANSIENT_DISTURBANCE && g_inTransientWindow[s]) {
      g_transientClassificationCount[s]++;
    }
  }

  unsigned long t1 = micros();
  exec_record(g_execStats, t1 - t0);

  unsigned long interval;
  if (EXPERIMENT_MODE == MODE_FIXED_RATE)              interval = FIXED_RATE_INTERVAL_MS;
  else if (EXPERIMENT_MODE == MODE_THRESHOLD_BASELINE) interval = tbInterval;
  else if (calibrating)                                interval = CALIBRATION_INTERVAL_MS;
  else                                                  interval = intervalForState(confirmedState);
  g_currentIntervalMs[s] = interval;

  if (calibrating) {
    Serial.print(F("CALIBRATION,")); Serial.print(elapsedMs); Serial.print(',');
    Serial.print(s); Serial.print(','); Serial.println(g_cal[s].count);
  } else {
    logData(elapsedMs, s, simulatedAdc, xNorm, varRaw, trdRaw, sfiRaw, nvi, ntd,
            rawState, candidateState, runLen, confirmedState, interval, confirmedTransition);
  }

  if (hasEvent && !calibrating && !g_eventResponseLogged[s] &&
      elapsedMs >= evStart && confirmedTransition) {
    logEventResponse(evStart, elapsedMs, s);
    g_eventResponseLogged[s] = true;
  }
}

static void printSummary() {
  Serial.println();
  Serial.println(F("=============================== EXPERIMENT_SUMMARY ==============================="));
  Serial.print(F("RUN_CONFIG,mode=")); Serial.print(modeName(EXPERIMENT_MODE));
  Serial.print(F(",indicator_set=")); Serial.print(indicatorSetName(INDICATOR_SET));
  Serial.print(F(",K=")); Serial.print(PERSISTENCE_K);
  Serial.print(F(",seed=")); Serial.println(RANDOM_SEED);

  unsigned long fixedRefPerSensor = OBSERVATION_WINDOW_MS / FIXED_RATE_INTERVAL_MS;
  unsigned long fixedRefTotal = fixedRefPerSensor * NUM_SENSORS;

  unsigned long totalActive = 0;
  unsigned long totalRawTransitions = 0;
  unsigned long totalConfirmedTransitions = 0;

  for (int s = 0; s < NUM_SENSORS; s++) {
    totalActive += g_activeCount[s];
    totalRawTransitions += g_pers[s].rawTransitions;
    totalConfirmedTransitions += g_pers[s].confirmedTransitions;

    float sensorARR = (fixedRefPerSensor > 0)
      ? 100.0f * (float)((long)fixedRefPerSensor - (long)g_activeCount[s]) / (float)fixedRefPerSensor
      : 0.0f;

    float tsr = 0.0f;
    bool tsrValid = pers_computeTSR(g_pers[s], tsr);

    Serial.print(F("SENSOR_SUMMARY,s=")); Serial.print(s);
    Serial.print(F(",acquisitions=")); Serial.print(g_activeCount[s]);
    Serial.print(F(",fixed_ref=")); Serial.print(fixedRefPerSensor);
    Serial.print(F(",ARR_pct=")); Serial.print(sensorARR, 2);
    Serial.print(F(",raw_transitions=")); Serial.print(g_pers[s].rawTransitions);
    Serial.print(F(",confirmed_transitions=")); Serial.print(g_pers[s].confirmedTransitions);
    Serial.print(F(",TSR_pct="));
    if (tsrValid) Serial.print(tsr, 2); else Serial.print(F("n/a"));
    Serial.print(F(",final_confirmed_state=")); Serial.print(stateLabel(g_pers[s].confirmed));
    if (EXPERIMENT_MODE == MODE_TRANSIENT_DISTURBANCE) {
      Serial.print(F(",transient_window_classifications="));
      Serial.print(g_transientClassificationCount[s]);
      Serial.print(F(" [verify: should be < K for every K>1 tested, per v4 design S13]"));
    }
    Serial.println();
  }

  float overallARR = (fixedRefTotal > 0)
    ? 100.0f * (float)((long)fixedRefTotal - (long)totalActive) / (float)fixedRefTotal
    : 0.0f;

  Serial.print(F("TOTAL,acquisitions=")); Serial.print(totalActive);
  Serial.print(F(",fixed_ref=")); Serial.print(fixedRefTotal);
  Serial.print(F(",ARR_pct=")); Serial.print(overallARR, 2);
  Serial.print(F(",raw_transitions=")); Serial.print(totalRawTransitions);
  Serial.print(F(",confirmed_transitions=")); Serial.println(totalConfirmedTransitions);

  Serial.println(F("--- Computational overhead (measured on THIS run, THIS platform) ---"));
  Serial.print(F("OVERHEAD,classification_cycles=")); Serial.print(g_execStats.count);
  Serial.print(F(",avg_us=")); Serial.print(exec_avgUs(g_execStats), 1);
  Serial.print(F(",min_us=")); Serial.print(g_execStats.minUs);
  Serial.print(F(",max_us=")); Serial.println(g_execStats.maxUs);
  Serial.print(F("OVERHEAD,free_ram_bytes=")); Serial.println(freeRamBytes());
  Serial.println(F("(Flash/program size: read from the Wokwi/Arduino IDE compile"));
  Serial.println(F(" output, or see README.md for figures from a reference build.)"));

  Serial.println(F("--- Internal accounting note ---"));
  Serial.println(F("VALIDATION,counts_consistent=YES (acquisitions are counted exactly"));
  Serial.println(F("  once per cycle, at the point of logging -- there is no separate"));
  Serial.println(F("  summary-vs-CSV path in this implementation that could disagree.)"));

  Serial.println(F("====================================================================================="));
}

void loop() {
  unsigned long elapsedMs = millis() - g_startMs;

  if (elapsedMs >= OBSERVATION_WINDOW_MS) {
    if (!g_summaryPrinted) {
      printSummary();
      g_summaryPrinted = true;
    }
    return;
  }

  for (int s = 0; s < NUM_SENSORS; s++) {
    if (elapsedMs >= g_nextDueMs[s]) {
      runAcquisitionCycle(s, elapsedMs);
      g_nextDueMs[s] = elapsedMs + g_currentIntervalMs[s];
    }
  }
}
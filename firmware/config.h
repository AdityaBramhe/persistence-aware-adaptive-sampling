#ifndef CONFIG_H
#define CONFIG_H

// =============================================================================
//  config.h -- Persistence-Aware Adaptive Sampling -- Experiment Configuration
//  Implements the locked v4 design (see the design .md for the full spec).
//
//  HOW TO RUN AN EXPERIMENT
//  One (MODE, INDICATOR_SET, PERSISTENCE_K, SEED) combination runs per Wokwi
//  simulation. To run the full study: set the four values below, run the
//  simulation for OBSERVATION_WINDOW_MS, copy the Serial Monitor output to a
//  .log file, then repeat for every row of the run matrix in README.md.
// =============================================================================

// ---- 1. Experiment mode ----------------------------------------------------
#define MODE_FIXED_RATE            0   // constant interval, all channels
#define MODE_THRESHOLD_BASELINE    1   // |delta| > THRESHOLD_VALUE -> short/long interval
#define MODE_STABLE                2   // no injected event
#define MODE_GRADUAL_CHANGE        3   // slow drift on the gradual-event sensor
#define MODE_SUDDEN_DISTURBANCE    4   // step change on the sudden-event sensor
#define MODE_MIXED_SENSORS         5   // gradual + sudden together, independent channels
#define MODE_TRANSIENT_DISTURBANCE 6   // short pulse, sized in classification
                                        // opportunities -- v4 design S13

#define EXPERIMENT_MODE  MODE_TRANSIENT_DISTURBANCE

// ---- 2. Indicator set (RQ3 ablation) ---------------------------------------
#define INDICATOR_VAR_ONLY   0   // VAR only
#define INDICATOR_VAR_TRD    1   // VAR + TRD
#define INDICATOR_FULL       2   // VAR + TRD + SFI  (main model)

#define INDICATOR_SET  INDICATOR_FULL

// ---- 3. Persistence requirement, in CLASSIFICATION CYCLES (RQ1 / RQ2) -----
//         K is a cycle count, NOT a time duration -- see README "K vs latency".
//         K=1 = no-persistence ablation (confirmed state tracks raw state).
#define PERSISTENCE_K  1

// ---- 4. Paired random seed --------------------------------------------------
//         Use the SAME seed across every method/mode being compared in one trial.
#define RANDOM_SEED  12345UL

// ---- 5. Fixed experiment constants (do not change between paired runs) -----
#define NUM_SENSORS          4
#define ANALOG_PINS          {A0, A1, A2, A3}

#define WINDOW_SIZE            10   // feature-extraction sliding window
#define WARMUP_SAMPLES          6   // samples needed before classification starts
#define CALIBRATION_SAMPLES    20   // samples used to compute VAR_base / sigma_base

// Bootstrap cadence (warm-up + calibration) is intentionally FAST for the
// scenario modes, so both phases finish well before the earliest scripted
// event (20 s) -- otherwise the calibration baseline could be computed partly
// from an already-disturbed signal. This does not affect FIXED_RATE (always
// samples at FIXED_RATE_INTERVAL_MS from cycle 1) or THRESHOLD_BASELINE
// (driven by its own delta rule from cycle 1); see README "Bootstrap timing".
#define WARMUP_INTERVAL_MS       100UL
#define CALIBRATION_INTERVAL_MS  200UL

#define OBSERVATION_WINDOW_MS   60000UL   // 60 s run
#define FIXED_RATE_INTERVAL_MS   1000UL   // reference baseline interval

#define THRESHOLD_VALUE   0.05f           // Baseline 2: |x_t - x_t-1| > THRESHOLD_VALUE

#define EPSILON  1e-9f                     // avoid div-by-zero in normalization

// When EXPERIMENT_MODE is a baseline (FIXED_RATE / THRESHOLD_BASELINE), the
// underlying synthetic signal is taken from this scenario, so both baselines
// are compared against the same "headline" signal as the adaptive method.
#define BASELINE_SIGNAL_SOURCE  MODE_MIXED_SENSORS

// ---- 6. Deterministic ground-truth event windows (seconds) -----------------
//         Sensor indices are 0-based: S1=0, S2=1, S3=2, S4=3.
#define GRADUAL_EVENT_SENSOR      1   // S2
#define GRADUAL_EVENT_START_S    20
#define GRADUAL_EVENT_END_S      40

#define SUDDEN_EVENT_SENSOR       2   // S3
#define SUDDEN_EVENT_START_S     30
#define SUDDEN_EVENT_END_S       40

// Transient disturbance: sized in classification opportunities, not seconds
// (v4 design S13, mandatory correction #3). At S3's pre-disturbance interval
// (1000 ms, state S), a 1200 ms pulse yields ~1 classification opportunity --
// i.e. fewer than K for any K>1. ALWAYS VERIFY from the printed
// "transient_window_classifications" summary line, per run, before treating
// the result as a valid RQ1 test -- do not assume the nominal duration held.
#define TRANSIENT_EVENT_SENSOR         2   // S3
#define TRANSIENT_EVENT_START_S       30
#define TRANSIENT_EVENT_DURATION_MS   1200UL

// ---- 7. Per-sensor default noise amplitudes (ADC counts, 0-1023) -----------
static const int NOISE_AMPLITUDE[NUM_SENSORS] = {2, 18, 55, 130};
static const float STABLE_NOISE_AMPLITUDE = 2.0f;  // used for non-target
                                                     // channels in single-event scenarios

#endif // CONFIG_H
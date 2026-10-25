#ifndef DIAGNOSTICS_H
#define DIAGNOSTICS_H

#include <stdint.h>

// =============================================================================
//  diagnostics.h -- runtime resource-usage measurement (v4 design S14/S16 #9:
//  "computational overhead"). Flash/program size CANNOT be measured from
//  inside the sketch -- read it from the Wokwi/Arduino IDE compile output
//  ("Sketch uses ... bytes"), or see README.md for figures measured via an
//  offline avr-gcc build of this exact source (done while preparing this
//  deliverable, for a representative number ahead of your own build).
// =============================================================================

extern int __heap_start;
extern int *__brkval;

static inline int freeRamBytes() {
  int v;
  return (int)&v - (__brkval == 0 ? (int)&__heap_start : (int)__brkval);
}

struct ExecTimeStats {
  unsigned long count;
  unsigned long sumUs;
  unsigned long minUs;
  unsigned long maxUs;
};

static inline void exec_init(ExecTimeStats &e) {
  e.count = 0; e.sumUs = 0; e.minUs = 0xFFFFFFFFUL; e.maxUs = 0;
}

static inline void exec_record(ExecTimeStats &e, unsigned long elapsedUs) {
  e.count++;
  e.sumUs += elapsedUs;
  if (elapsedUs < e.minUs) e.minUs = elapsedUs;
  if (elapsedUs > e.maxUs) e.maxUs = elapsedUs;
}

static inline float exec_avgUs(const ExecTimeStats &e) {
  return e.count ? ((float)e.sumUs / (float)e.count) : 0.0f;
}

#endif // DIAGNOSTICS_H

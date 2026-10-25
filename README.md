# Persistence-Aware Adaptive Sampling for Resource-Efficient IoT Sensing

Implementation accompanying the paper "Persistence-Aware Adaptive Sampling
for Resource-Efficient IoT Sensing" (Tejal Gupta, Aditya Bramhe, Syamasudha
Veeragandham; Vellore Institute of Technology).

## Folder structure

- `firmware/` - Arduino Uno sketch and headers (feature extraction,
  calibration, classification, persistence gate, baselines, diagnostics,
  logging) plus `diagram.json`, the Wokwi circuit diagram (Arduino Uno with
  four potentiometers on A0-A3).
- `scripts/` - analysis pipeline used to produce the paper's results:
  `run.js` (runs a compiled `.hex` in the avr8js emulator), `sweep.py`
  (drives the full experimental sweep), `analyze.py` (computes metrics from
  the logs), `make_tables.py` / `make_fig.py` / `build_tex.py` (generate the
  paper's tables, figure, and numbers file).

## How to run

**Wokwi (recommended):** open wokwi.com, start a new Arduino Uno project,
copy in `firmware/sketch.ino` and all `firmware/*.h` files, replace the
default circuit with `firmware/diagram.json`, run the simulation, and watch
the Serial Monitor.

**Command-line emulation:** compile `firmware/sketch.ino` for Arduino Uno to
a `.hex` file, then:

```
node scripts/run.js <firmware.hex> <output.log> <seconds> <adc_volts>
```

Use `scripts/sweep.py` to repeat this across scenarios/seeds/K values, then
`scripts/analyze.py`, `scripts/make_tables.py`, and `scripts/make_fig.py` to
reproduce the paper's tables and figure.

**Physical hardware:** wire four potentiometers to analog pins A0-A3 of an
Arduino Uno as shown in `firmware/diagram.json`, upload `firmware/sketch.ino`
via the Arduino IDE, and read the Serial output at 115200 baud.

No physical hardware run is reported in the paper; all reported results come
from the deterministic, seed-parameterized synthetic signal generator
(`firmware/signal_generator.h`), run identically on Wokwi and on the avr8js
emulator since both use the same AVR core.

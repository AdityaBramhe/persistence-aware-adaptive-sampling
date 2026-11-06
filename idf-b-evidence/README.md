# Evidence package for the IDF-B: Evidence-Supported Persistence Qualification

Code and results behind the Invention Disclosure "Evidence-Supported Persistence
Qualification of Temporal-Variability States for Conflict-Free Adaptive Resource
Configuration of Sensing Channels in Distributed Sensor Networks"
(Tejal Gupta, Aditya Bramhe, Syamasudha Veeragandham; VIT).

**Evidence status.** The baseline pipeline is the firmware in `../firmware` (Tier 1,
run in an AVR emulator). The evidence-support test and commit rules are new and are
evaluated only in the Python behavioural model here (Tier 2). They have **not** been
run in firmware or on hardware. All signals are synthetic and seeded.

## Files

| File | Purpose |
|---|---|
| `model.py` | Behavioural model of the pipeline: signal generator, descriptor, classifier, governor (persistence, evidence-support test, optional commit rules), scenarios |
| `evalcfg.py` | Metrics (false confirmations, flip-backs, detection, latency, pulse escalation, saving) |
| `final_study.py` -> `final_results.json` | Main comparison (IDF Table 10) |
| `ablation.py` -> `ablation.json` | Ablation of the optional rules (Table 14) |
| `sens.py` -> `sens.json` | Threshold sensitivity x0.7 / x1.3 |
| `pulse_width.json` | False escalation against pulse width (Table 11) |
| `robust.py`, `robust_cfg.py`, `robust2.py` -> `robust.json`, `robust2.json` | Outlier spikes, ties, noise x0.5 / x2, recovery (Tables 12, 13) |
| `direction_diag.py` -> `direction_diag.json` | Windows withheld by direction (worsening vs recovery), Section 8.4 |
| `verify_fw.py`, `firmware_run1_data.csv` | Fidelity check against one firmware-emulator run (0 mismatches in 104 rows) |
| `figs.py`, `diagrams.py`, `blockfig.py` | Figure scripts (need matplotlib / graphviz) |

## Run

```
pip install numpy
python3 verify_fw.py      # model vs firmware log, expect 0 mismatches
python3 final_study.py    # 60 seeds x 8 configurations (takes a few minutes)
python3 ablation.py
python3 robust2.py
python3 direction_diag.py
```

Seeds are `12345 + 7919*i`, i = 0..59, identical for every method, so comparisons are paired.

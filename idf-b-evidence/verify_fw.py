import csv, numpy as np
from model import *
rows = list(csv.DictReader(open('firmware_run1_data.csv')))
cfg = dict(K=2)
r = run("mixed", 12345, cfg)
# 1) generator check: every logged raw_adc must be reproduced from (sensor,t,seed)
bad = 0
for d in rows:
    if read_adc(int(d['sensor']), int(d['t_ms']), 12345, "mixed") != int(d['raw_adc']): bad += 1
print("generator mismatches:", bad, "of", len(rows))
# 2) full pipeline: compare model log rows with firmware rows
fw = {(int(d['t_ms']), int(d['sensor'])): d for d in rows}
mod = {}
for s in range(4):
    for rec in r['sensors'][s]['log']:
        mod[(rec[0], rec[1])] = rec
print("rows firmware/model:", len(fw), len(mod), " same keys:", set(fw) == set(mod))
mism = dict(raw=0, conf=0, run=0, comm=0, nvi=0)
for k, d in fw.items():
    if k not in mod: continue
    t, s, adc, raw, cand, run_, conf, comm, nvi, ntd, sfi = mod[k][:11]
    if STATES[raw] != d['raw_state']: mism['raw'] += 1
    if STATES[conf] != d['confirmed_state']: mism['conf'] += 1
    if run_ != int(d['run_len']): mism['run'] += 1
    if int(comm) != int(d['confirmed_transition']): mism['comm'] += 1
    if abs(float(nvi) - float(d['NVI'])) > 6e-4: mism['nvi'] += 1
print("mismatches:", mism)
print("acquisitions incl warm-up (model):", r['total'], " per sensor", r['acq'])
print("raw/confirmed transitions:", sum(x['gov'].rawTr for x in r['sensors']), sum(x['gov'].confTr for x in r['sensors']))

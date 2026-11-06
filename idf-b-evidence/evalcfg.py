import numpy as np
from model import *

SEEDS = [12345 + 7919 * i for i in range(60)]

def commits(r, s):
    return [rec for rec in r['sensors'][s]['log'] if rec[7]]

def state_at(r, s, t):
    """confirmed state of channel s just before time t (state after the last record with time < t)"""
    cur = None
    for rec in r['sensors'][s]['log']:
        if rec[0] >= t: break
        cur = rec[6]
    return 0 if cur is None else cur

def detect(r, s, onset, until):
    """first commit to V or U (and more severe than the state at onset) in [onset, until); latency ms or None"""
    base = state_at(r, s, onset)
    for rec in commits(r, s):
        if onset <= rec[0] < until and rec[6] >= max(2, base + 1):
            return rec[0] - onset
    return None

def flipbacks(r, window_ms=30000):
    n = 0
    for s in range(NUM_SENSORS):
        cs = commits(r, s)
        # reconstruct sequence of confirmed states, including the initial one
        seq = []
        prev = None
        for rec in r['sensors'][s]['log']:
            if prev is None: prev = rec[6]; seq.append((rec[0], prev)); continue
            if rec[7]:
                seq.append((rec[0], rec[6]))
        for i in range(2, len(seq)):
            if seq[i][1] == seq[i-2][1] and seq[i][0] - seq[i-1][0] <= window_ms: n += 1
    return n

def evaluate(cfg, seeds=SEEDS, **kw):
    R = dict(stable_fc=[], stable_raw=[], stable_flip=[], stable_arr=[], mixed_arr=[], mixed_commits=[],
             step_lat=[], step_ctrl=[], ramp_lat=[], ramp_ctrl=[], tr_peak_excess=[], tr_pulse_hit=[])
    for sd in seeds:
        rs = run("stable", sd, cfg, **kw)
        R['stable_fc'].append(sum(x['gov'].confTr for x in rs['sensors']))
        R['stable_raw'].append(sum(x['gov'].rawTr for x in rs['sensors']))
        R['stable_flip'].append(flipbacks(rs))
        R['stable_arr'].append(100 * (240 - rs['total']) / 240)
        rm = run("mixed", sd, cfg, **kw)
        R['mixed_arr'].append(100 * (240 - rm['total']) / 240)
        R['mixed_commits'].append(sum(x['gov'].confTr for x in rm['sensors']))
        R['step_lat'].append(detect(rm, S_S, 30000, 55000)); R['step_ctrl'].append(detect(rs, S_S, 30000, 55000))
        R['ramp_lat'].append(detect(rm, G_S, 20000, 60000)); R['ramp_ctrl'].append(detect(rs, G_S, 20000, 60000))
        rt = run("transient", sd, cfg, **kw); rc = run("transient_ctrl", sd, cfg, **kw)
        def peak(r):
            vals = [rec[6] for rec in r['sensors'][T_S]['log'] if 30000 <= rec[0] < 50000]
            return max(vals) if vals else 0
        R['tr_peak_excess'].append(peak(rt) - peak(rc))
        R['tr_pulse_hit'].append(1 if peak(rt) > peak(rc) else 0)
    return R

def summarize(name, R):
    n = len(R['stable_fc'])
    def det(l): return sum(v is not None for v in l)
    def med(l):
        v = [x for x in l if x is not None]
        return np.median(v) / 1000 if v else float('nan')
    return (f"{name:34s} stableFC {np.mean(R['stable_fc']):5.1f} flip {np.mean(R['stable_flip']):4.1f} "
            f"| step det {det(R['step_lat']):2d}/{n} (chance {det(R['step_ctrl']):2d}) lat {med(R['step_lat']):5.1f}s "
            f"| ramp det {det(R['ramp_lat']):2d}/{n} (chance {det(R['ramp_ctrl']):2d}) lat {med(R['ramp_lat']):5.1f}s "
            f"| pulse-induced {100*np.mean(R['tr_pulse_hit']):4.1f}% "
            f"| ARRmix {np.mean(R['mixed_arr']):4.1f} commits(mixed) {np.mean(R['mixed_commits']):4.1f}")

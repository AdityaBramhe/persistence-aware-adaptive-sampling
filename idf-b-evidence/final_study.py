import json, numpy as np, model
from evalcfg import *
from math import sqrt

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d; h = z*sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return 100*(c-h), 100*(c+h)

def team(conf, spm, prev):
    # S: RT if SPM high (Schmitt band 0.8 in / 0.6 out) else OT ; M: OT ; V: RCT ; U: IT
    if conf == 0:
        if prev == "RT": return "RT" if spm >= 0.6 else "OT"
        return "RT" if spm >= 0.8 else "OT"
    return {1: "OT", 2: "RCT", 3: "IT"}[conf]

def scp_counts(r):
    """SCP events: confirmed-state change OR team change; merged into one packet per cycle."""
    scp = 0; team_changes = 0; cycles = 0
    for s in range(NUM_SENSORS):
        prev_t = None
        for rec in r['sensors'][s]['log']:
            cycles += 1
            t = team(rec[6], rec[11], prev_t)
            ch_team = prev_t is not None and t != prev_t
            if rec[7] or ch_team: scp += 1
            team_changes += ch_team
            prev_t = t
    return scp, team_changes, cycles

CFGS = [
 ("K=1  (no persistence)",            dict(K=1)),
 ("K=2  run-length",                  dict(K=2)),
 ("K=3  run-length",                  dict(K=3)),
 ("K=5  run-length",                  dict(K=5)),
 ("K=11 run-length",                  dict(K=11)),
 ("PQCG  K=2,Q=2",                    dict(K=2, integrity="noworse", Q=2)),
 ("PQCG  K=2,Q=3",                    dict(K=2, integrity="noworse", Q=3)),
 ("PQCG-full K=2,Q=2,h=.15,rev",      dict(K=2, integrity="noworse", Q=2, hyst=0.15, rev_mult=2, rev_window=5)),
]
out = {}
n = len(SEEDS)
for name, cfg in CFGS:
    R = evaluate(cfg)
    # SCP / team accounting on the mixed and stable scenarios
    sc = []; tc = []; cy = []; rawtr = []
    for sd in SEEDS:
        rm = run("mixed", sd, cfg)
        a, b, c = scp_counts(rm); sc.append(a); tc.append(b); cy.append(c)
        rawtr.append(sum(x['gov'].rawTr for x in rm['sensors']))
    det = lambda l: sum(v is not None for v in l)
    med = lambda l: float(np.median([x for x in l if x is not None]) / 1000) if det(l) else None
    iqr = lambda l: [float(np.percentile([x for x in l if x is not None], q) / 1000) for q in (25, 75)] if det(l) else None
    hit = int(sum(R['tr_pulse_hit']))
    out[name] = dict(
        cfg=cfg, stable_fc=float(np.mean(R['stable_fc'])), stable_fc_sd=float(np.std(R['stable_fc'], ddof=1)),
        stable_raw=float(np.mean(R['stable_raw'])), stable_flip=float(np.mean(R['stable_flip'])),
        stable_arr=float(np.mean(R['stable_arr'])), mixed_arr=float(np.mean(R['mixed_arr'])),
        mixed_arr_sd=float(np.std(R['mixed_arr'], ddof=1)),
        mixed_commits=float(np.mean(R['mixed_commits'])), mixed_raw=float(np.mean(rawtr)),
        scp=float(np.mean(sc)), team_changes=float(np.mean(tc)), cycles=float(np.mean(cy)),
        step_det=det(R['step_lat']), step_chance=det(R['step_ctrl']), step_med=med(R['step_lat']), step_iqr=iqr(R['step_lat']),
        ramp_det=det(R['ramp_lat']), ramp_chance=det(R['ramp_ctrl']), ramp_med=med(R['ramp_lat']), ramp_iqr=iqr(R['ramp_lat']),
        pulse_hit=hit, pulse_ci=wilson(hit, n), n=n)
    print(name, json.dumps({k: v for k, v in out[name].items() if k != 'cfg'}), flush=True)

# baselines: fixed and threshold rule (acquisition and config-change accounting)
base = {}
for mode in ("fixed", "threshold"):
    acq_m = []; acq_s = []; sw = []
    for sd in SEEDS:
        rm = run("mixed", sd, dict(K=2), mode=mode); rs = run("stable", sd, dict(K=2), mode=mode)
        acq_m.append(100 * (240 - rm['total']) / 240); acq_s.append(100 * (240 - rs['total']) / 240)
        # interval changes (rate switches) in the stable run: count changes of successive inter-sample gaps per sensor
        # reconstruct gaps from the sampling instants: re-run bookkeeping via the due times is not stored, so derive from the threshold rule
        n_sw = 0
        for s in range(NUM_SENSORS):
            xs = rs['sensors'][s]
            # approximate from stored per-sensor sample log is unavailable in baselines (log only after calibration); use tb_last trace
        sw.append(n_sw)
    base[mode] = dict(mixed_arr=float(np.mean(acq_m)), stable_arr=float(np.mean(acq_s)))
print(base)
out["_baselines"] = base
out["_meta"] = dict(seeds=SEEDS, n=n)
json.dump(out, open("final_results.json", "w"), indent=1)

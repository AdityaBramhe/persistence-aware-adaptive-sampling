import json, numpy as np, model
from evalcfg import *
CF = [
 ("K=2 (reference)",                       dict(K=2)),
 ("K=2 + asymmetric K (up 3 / down 2)",    dict(K=2, K_up=3, K_dn=2)),
 ("K=2 + asymmetric K (up 2 / down 1)",    dict(K=2, K_up=2, K_dn=1)),
 ("K=2 + dwell lock (3 cycles)",           dict(K=2, dwell=3)),
 ("K=2 + slew limit",                      dict(K=2, slew=True)),
 ("K=2 + hysteresis 0.15",                 dict(K=2, hyst=0.15)),
 ("K=2 + reversal penalty (2x, 5 cycles)", dict(K=2, rev_mult=2, rev_window=5)),
 ("K=2 + evidence gate Q=2 (hold)",        dict(K=2, integrity="noworse", Q=2)),
 ("  gate + hysteresis 0.15",              dict(K=2, integrity="noworse", Q=2, hyst=0.15)),
 ("  gate + hysteresis + reversal penalty",dict(K=2, integrity="noworse", Q=2, hyst=0.15, rev_mult=2, rev_window=5)),
 ("variant: unsupported window resets run",dict(K=2, integrity="noworse", Q=2, unq="reset")),
 ("alternative: classify on trimmed window (Q=2)", dict(K=2, integrity="noworse", Q=2, trim_raw=True)),
]
out = {}
for name, cfg in CF:
    R = evaluate(cfg)
    model.T_DUR = 2500; hit25 = 0
    for sd in SEEDS:
        rt = run("transient", sd, cfg); rc = run("transient_ctrl", sd, cfg)
        pk = lambda r: max([rec[6] for rec in r['sensors'][T_S]['log'] if 30000 <= rec[0] < 55000] or [0])
        hit25 += pk(rt) > pk(rc)
    model.T_DUR = 1200
    d = lambda l: sum(v is not None for v in l)
    m = lambda l: float(np.median([x for x in l if x is not None]) / 1000) if d(l) else None
    out[name] = dict(fc=float(np.mean(R['stable_fc'])), flip=float(np.mean(R['stable_flip'])), step_det=d(R['step_lat']), step_ch=d(R['step_ctrl']),
        step_lat=m(R['step_lat']), ramp_det=d(R['ramp_lat']), ramp_ch=d(R['ramp_ctrl']), ramp_lat=m(R['ramp_lat']),
        p12=100*float(np.mean(R['tr_pulse_hit'])), p25=100*hit25/len(SEEDS), arr=float(np.mean(R['mixed_arr'])))
    print(name, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in out[name].items()}, flush=True)
json.dump(out, open("ablation.json", "w"), indent=1)

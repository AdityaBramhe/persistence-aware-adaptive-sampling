import json, numpy as np, model
from evalcfg import *
from math import sqrt
CFG = {
 "K=2": dict(K=2), "K=3": dict(K=3), "K=11": dict(K=11),
 "Invention K=2,Q=2": dict(K=2, integrity="noworse", Q=2),
 "Invention K=2,Q=3": dict(K=2, integrity="noworse", Q=3),
 "Invention + hyst + rev": dict(K=2, integrity="noworse", Q=2, hyst=0.15, rev_mult=2, rev_window=5),
}
def med(l): 
    v=[x for x in l if x is not None]; return float(np.median(v)/1000) if v else None
def det(l): return int(sum(v is not None for v in l))
def recov(r, s, off, until):
    base = state_at(r, s, off)
    if base < 2: return 'na'
    for rec in commits(r, s):
        if off <= rec[0] < until and rec[6] < base: return rec[0]-off
    return None
out = {}
# ---- 1. recovery ----
rec_out = {}
for name, cfg in CFG.items():
    lat3=[]; lat2=[]; ret=[]
    for sd in SEEDS:
        rm = run("mixed", sd, cfg)
        a = recov(rm, S_S, 40000, 60000)
        if a != 'na': lat3.append(a)
        b = recov(rm, G_S, 40000, 60000)
        if b != 'na': lat2.append(b)
    rec_out[name] = dict(step_n=len(lat3), step_rec=det(lat3), step_med=med(lat3), ramp_n=len(lat2), ramp_rec=det(lat2), ramp_med=med(lat2))
    print("recovery", name, rec_out[name], flush=True)
out['recovery'] = rec_out
# ---- 2. step with outliers ----
o_out = {}
for name, cfg in CFG.items():
    la=[]; ctrl=[]
    for sd in SEEDS:
        r1 = run("step_out", sd, cfg); r0 = run("stable_out", sd, cfg)
        la.append(detect(r1, S_S, 30000, 55000)); ctrl.append(detect(r0, S_S, 30000, 55000))
    o_out[name] = dict(det=det(la), chance=det(ctrl), med=med(la))
    print("outliers", name, o_out[name], flush=True)
out['outliers'] = o_out
# ---- 3. ties ----
t_out = {}
cfg = CFG["Invention K=2,Q=2"]
for tie in ("older", "newer"):
    model.TIE = tie; model.TIE_STATS[0] = model.TIE_STATS[1] = 0
    R = evaluate(cfg)
    t_out[tie] = dict(stable_fc=float(np.mean(R['stable_fc'])), flip=float(np.mean(R['stable_flip'])), step=det(R['step_lat']), step_med=med(R['step_lat']),
                      ramp=det(R['ramp_lat']), pulse=int(sum(R['tr_pulse_hit'])), windows=model.TIE_STATS[0], ties=model.TIE_STATS[1])
    print("tie", tie, t_out[tie], flush=True)
model.TIE = "older"
out['ties'] = t_out
# ---- 4. noise scale ----
n_out = {}
for sc in (0.5, 1.0, 2.0):
    model.NOISE_SCALE = sc
    for name in ("K=2", "K=3", "Invention K=2,Q=2"):
        R = evaluate(CFG[name])
        n_out[f"{sc}|{name}"] = dict(stable_fc=float(np.mean(R['stable_fc'])), flip=float(np.mean(R['stable_flip'])), step=det(R['step_lat']), step_chance=det(R['step_ctrl']),
                                    step_med=med(R['step_lat']), ramp=det(R['ramp_lat']), ramp_chance=det(R['ramp_ctrl']), pulse=int(sum(R['tr_pulse_hit'])), sav=float(np.mean(R['mixed_arr'])))
        print("noise", sc, name, n_out[f"{sc}|{name}"], flush=True)
model.NOISE_SCALE = 1.0
out['noise'] = n_out
json.dump(out, open('robust.json', 'w'), indent=1)
print("done")

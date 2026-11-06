import json, numpy as np, model
from evalcfg import *
from robust_cfg import CFG, med, det
model.OBS_MS = 240000
out = {}
for name, cfg in CFG.items():
    lat=[]; peak=[]; ndet=0
    for sd in SEEDS:
        r = run("recov", sd, cfg)
        base = state_at(r, S_S, 60000)
        if base < 2: continue
        ndet += 1
        got = None
        for rec in commits(r, S_S):
            if 60000 <= rec[0] and rec[6] < base: got = rec[0]-60000; break
        lat.append(got)
    out[name] = dict(n=ndet, rec=det(lat), med=med(lat))
    print(name, out[name], flush=True)
json.dump(out, open('robust2.json','w'), indent=1)

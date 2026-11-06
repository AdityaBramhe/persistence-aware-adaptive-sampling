import json, numpy as np
from evalcfg import *
CF = [("K=2",dict(K=2)),("K=3",dict(K=3)),("PQCG K=2,Q=2",dict(K=2,integrity="noworse",Q=2))]
res = {}
for mult in (0.7, 1.0, 1.3):
    for name,cfg in CF:
        R = evaluate(cfg, mult=mult)
        det=lambda l:sum(v is not None for v in l)
        res[f"{name}|{mult}"] = dict(stable_fc=float(np.mean(R['stable_fc'])), pulse=int(sum(R['tr_pulse_hit'])),
              step_det=det(R['step_lat']), step_chance=det(R['step_ctrl']), ramp_det=det(R['ramp_lat']), ramp_chance=det(R['ramp_ctrl']),
              mixed_arr=float(np.mean(R['mixed_arr'])))
        print(mult, name, res[f"{name}|{mult}"], flush=True)
json.dump(res, open("sens.json","w"), indent=1)

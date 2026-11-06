import json, model
from model import *
SEEDS = [12345 + 7919 * i for i in range(60)]
cfg = dict(K=2, integrity="noworse", Q=2)
rec = []
orig = Governor.update
def upd(self, raw, window_states_trimmed=None):
    before = self.conf
    c = orig(self, raw, window_states_trimmed)
    rec.append((raw, before, window_states_trimmed))
    return c
Governor.update = upd
out = {}
for scen in ("recov", "mixed", "stable"):
    rec.clear()
    for sd in SEEDS: run(scen, sd, cfg)
    d = {}
    for name, f in (("worsening", lambda r, c: r > c), ("recovery", lambda r, c: r < c), ("recovery_nonS", lambda r, c: r < c and r > 0), ("same", lambda r, c: r == c)):
        sel = [(r, c, t) for r, c, t in rec if f(r, c) and t is not None]
        unq = sum(1 for r, c, t in sel if t < r)
        d[name] = dict(windows=len(sel), unqualified=unq)
    out[scen] = d
    print(scen, d)
json.dump(out, open("direction_diag.json", "w"), indent=1)

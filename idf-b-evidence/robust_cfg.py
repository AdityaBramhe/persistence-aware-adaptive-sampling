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

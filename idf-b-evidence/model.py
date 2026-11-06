"""
Behavioural (cycle-accurate) Python model of the v4 firmware pipeline plus the
proposed Persistence-Qualified Configuration Governor (PQCG).
float32 arithmetic is used wherever the firmware uses float, 32-bit wrap for
unsigned long, so the model can be checked sample-by-sample against the
firmware log (run1_data.csv).
"""
import numpy as np
F = np.float32
M32 = 0xFFFFFFFF

# ---------------- constants copied from config.h / classifier.h ----------------
NUM_SENSORS = 4
WINDOW = 10; WARMUP = 6; CAL = 20
WARM_INT = 100; CAL_INT = 200
OBS_MS = 60000; FIXED_INT = 1000
EPS = F(1e-9)
NOISE = [2, 18, 55, 130]; STABLE_NOISE = 2
G_S, G_START, G_END = 1, 20, 40
S_S, S_START, S_END = 2, 30, 40
T_S, T_START, T_DUR = 2, 30, 1200
NOISE_SCALE = 1.0            # scales every channel's noise amplitude (robustness study)
TIE_STATS = [0, 0]           # [windows evaluated by the evidence test, windows with a tie at the cut]
TIE = 'older'                # tie-break among equally deviant samples in the evidence test
OUT_PERIOD, OUT_MAG = 8, 200  # outlier study: ~1 in 8 samples of the stepped channel gets +/-OUT_MAG counts
T0 = 45                      # first loop pass observed in the firmware log (t=45 ms)
INTERVAL = {0: 1000, 1: 2000, 2: 4000, 3: 8000}
THR = [(F(1.5), F(1.0), 2), (F(4.0), F(3.0), 5), (F(10.0), F(8.0), 8)]
STATES = "SMVU"

def sg_hash(a, b, c):
    h = (a * 0x9E3779B1) & M32
    h ^= (b + 0x85EBCA6B + ((h << 6) & M32) + (h >> 2)) & M32
    h ^= (c + 0xC2B2AE35 + ((h << 6) & M32) + (h >> 2)) & M32
    h ^= (h >> 15)
    h = (h * 0x27D4EB2F) & M32
    h ^= (h >> 13)
    return h

def sg_noise(s, t, seed, amp):
    if amp <= 0: return 0
    h = sg_hash(s, t, seed)
    return int(h % (2 * amp + 1)) - amp

def sg_drift(s, t, scen):
    ts = t // 1000
    if scen in ("gradual", "mixed") and s == G_S and G_START <= ts <= G_END:
        prog = F(ts - G_START) / F(G_END - G_START)
        return F(60.0) * prog
    if scen in ("sudden", "mixed", "step_out") and s == S_S and S_START <= ts < S_END:
        return F(220.0)
    if scen == "recov" and s == S_S and 30 <= ts < 60:        # recovery study: 30 s step, 240 s run
        return F(220.0)
    if scen == "transient" and s == T_S and T_START * 1000 <= t < T_START * 1000 + T_DUR:
        return F(220.0)
    return F(0.0)

def amp_for(s, scen):
    if scen in ("mixed", "stable"): a = NOISE[s]
    else:
        tgt = (scen == "gradual" and s == G_S) or (scen in ("sudden", "step_out", "stable_out", "recov") and s == S_S) or (scen in ("transient", "transient_ctrl") and s == T_S)
        a = NOISE[s] if tgt else STABLE_NOISE
    return int(round(a * NOISE_SCALE))

def sg_outlier(s, t, seed, scen):
    """outlier study: during 30-40 s, ~1 in OUT_PERIOD samples of the stepped channel carries a +/-OUT_MAG spike"""
    if scen in ("step_out", "stable_out") and s == S_S and S_START * 1000 <= t < S_END * 1000:
        h = sg_hash(s, t, seed + 777)
        if h % OUT_PERIOD == 0: return OUT_MAG if (h >> 8) & 1 else -OUT_MAG
    return 0

def read_adc(s, t, seed, scen, pin=0):
    v = pin + sg_noise(s, t, seed, amp_for(s, scen)) + int(sg_drift(s, t, scen)) + sg_outlier(s, t, seed, scen)
    return max(0, min(1023, v))

# ---------------- feature extraction (feature_extraction.h) ----------------
def variance(x):
    n = len(x)
    if n == 0: return F(0)
    mean = F(0)
    for v in x: mean = F(mean + v)
    mean = F(mean / F(n))
    var = F(0)
    for v in x:
        d = F(v - mean); var = F(var + F(d * d))
    return F(var / F(n))

def trend(x):
    n = len(x)
    if n < 2: return F(0)
    h = n // 2; rc = n - h
    o = F(0); r = F(0)
    for v in x[:h]: o = F(o + v)
    o = F(o / F(h))
    for v in x[h:]: r = F(r + v)
    r = F(r / F(rc))
    return F(r - o)

def reversals(x, db):
    n = len(x)
    if n < 3: return 0
    rev = 0; prev = 0; last = 0
    for i in range(1, n):
        d = F(x[i] - x[i - 1])
        if d > db: sg = 1
        elif d < -db: sg = -1
        else: sg = last
        if i >= 2 and sg != 0 and prev != 0 and sg != prev: rev += 1
        if sg != 0: last = sg
        prev = sg
    return rev

def classify(nvi, ntd, sfi, indicator="full", mult=1.0):
    chk_t = indicator != "var"; chk_s = indicator == "full"
    m = F(mult)
    for k, (nv, nt, sf) in enumerate(THR):
        if not (nvi < F(nv * m)): continue
        if chk_t and not (ntd < F(nt * m)): continue
        if chk_s and not (sfi <= sf): continue
        return k
    return 3

# ---------------- persistence variants ----------------
class Governor:
    """cfg keys:
         K          : consecutive-window requirement (K=1 -> no persistence)
         K_up/K_dn  : direction-specific K (None -> K) ; 'up' = to a MORE severe state
         integrity  : None | 'noworse' | 'equal'  (single-sample dominance gate)
         dwell      : minimum cycles between two committed changes (0 = off)
         override   : bool, a >=2-level severity jump bypasses the dwell lock
         slew       : bool, a commit moves at most one severity level
    """
    def __init__(self, cfg):
        self.c = cfg
        self.init = False
        self.rawPrev = self.cand = self.conf = 0
        self.run = 0
        self.rawTr = self.confTr = 0
        self.since = 10**6
        self.dominated = 0
        self.hist = []          # recent raw states (for SPM)
    def update(self, raw, window_states_trimmed=None):
        """raw: raw severity; trimmed: severity of the leave-one-out window (or None)"""
        c = self.c
        if not self.init:
            self.init = True
            self.rawPrev = self.cand = self.conf = raw
            self.run = 1
        # raw transition accounting (unchanged definition)
        if raw != self.rawPrev: self.rawTr += 1
        self.rawPrev = raw
        self.since += 1
        # ---- evidence-integrity gate -------------------------------------
        gate = c.get("integrity")
        qualifies = True
        if gate and window_states_trimmed is not None:
            if gate == "noworse":  qualifies = window_states_trimmed >= raw
            elif gate == "equal":  qualifies = window_states_trimmed == raw
            if not qualifies: self.dominated += 1
        if qualifies:
            if raw == self.cand: self.run = min(self.run + 1, 65535)
            else: self.cand = raw; self.run = 1
        elif c.get("unq") == "reset":
            self.cand = self.conf; self.run = 1            # variant: unsupported window counts as 'no change'
        # (default: a dominated window neither extends nor resets the run: state machine held)
        self.hist.append(raw if qualifies else self.conf)
        self.hist = self.hist[-c.get("spm_w", 10):]
        # ---- direction dependent persistence requirement --------------------
        up = self.cand > self.conf
        K = (c.get("K_up") if up else c.get("K_dn")) or c["K"]
        if c.get("rev_mult") and self.cand == getattr(self, "prevconf", -1) and self.since < c.get("rev_window", 5):
            K = K * c["rev_mult"]
        committed = False
        if self.cand != self.conf and self.run >= K:
            jump = abs(self.cand - self.conf)
            locked = c.get("dwell", 0) > 0 and self.since < c["dwell"] and not (c.get("override") and jump >= 2)
            if not locked:
                new = self.cand
                if c.get("slew") and jump > 1:
                    new = self.conf + (1 if self.cand > self.conf else -1)
                self.prevconf = self.conf
                self.conf = new
                self.confTr += 1; self.since = 0; committed = True
        return committed
    def spm(self):
        if not self.hist: return 1.0
        return sum(1 for s in self.hist if s == self.conf) / len(self.hist)

# ---------------- one run ----------------
def run(scen, seed, cfg, mode="adaptive", indicator="full", mult=1.0, thr_val=0.05):
    """mode: adaptive | fixed | threshold.  Returns dict with per-sensor logs."""
    st = []
    for s in range(NUM_SENSORS):
        st.append(dict(win=[], cal=[], calDone=False, varB=F(0), sigB=F(0), idx=0, active=0,
                       gov=Governor(cfg), interval=FIXED_INT, due=T0, last=None, log=[], times=[], tb_last=None,
                       txn=0, scp=[]))
    t_run = T0
    out_acq = [0] * NUM_SENSORS
    while True:
        due = min(x["due"] for x in st)
        t = max(due, T0)
        if t >= OBS_MS: break
        for s in range(NUM_SENSORS):
            x = st[s]
            if t < x["due"]: continue
            adc = read_adc(s, t, seed, scen)
            xn = F(adc) / F(1023.0)
            # threshold baseline bookkeeping (always updated)
            if x["tb_last"] is None: tb_int = 1000
            else: tb_int = 1000 if abs(F(xn - x["tb_last"])) > F(thr_val) else 4000
            x["tb_last"] = xn
            x["win"].append(xn); x["win"] = x["win"][-WINDOW:]
            x["idx"] += 1
            out_acq[s] += 1
            if x["idx"] < WARMUP:
                x["interval"] = FIXED_INT if mode == "fixed" else (tb_int if mode == "threshold" else WARM_INT)
                x["due"] = t + x["interval"]; continue
            x["active"] += 1
            calibrating = not x["calDone"]
            rec = None
            if calibrating:
                x["cal"].append(xn)
                if len(x["cal"]) >= CAL:
                    x["varB"] = variance(x["cal"]); x["sigB"] = F(np.sqrt(x["varB"])); x["calDone"] = True
            else:
                w = x["win"]
                var = variance(w); trd = trend(w)
                db = F(1.0) * x["sigB"]
                sfi = reversals(w, db)
                nvi = F(var / F(x["varB"] + EPS)); ntd = F(abs(trd) / F(x["sigB"] + EPS))
                raw = classify(nvi, ntd, sfi, indicator, mult)
                h = cfg.get("hyst", 0.0)
                if h and x["gov"].init:
                    cf = x["gov"].conf
                    if raw > cf:
                        if classify(nvi, ntd, sfi, indicator, mult * (1 + h)) <= cf: raw = cf
                    elif raw < cf:
                        if classify(nvi, ntd, sfi, indicator, mult * (1 - h)) >= cf: raw = cf
                trimmed = None
                if cfg.get("integrity"):
                    q = cfg.get("Q", 2)
                    mean = F(sum(w, F(0)) / F(len(w)))
                    order = sorted(range(len(w)), key=lambda i: (-float(abs(F(w[i] - mean))), i if TIE == "older" else -i))
                    TIE_STATS[0] += 1
                    if q >= 2 and len(order) >= q and abs(F(w[order[q - 2]] - mean)) == abs(F(w[order[q - 1]] - mean)): TIE_STATS[1] += 1
                    drop = set(order[:q - 1])
                    w2 = [v for i, v in enumerate(w) if i not in drop]
                    v2 = variance(w2); t2 = trend(w2); s2 = reversals(w2, db)
                    n2 = F(v2 / F(x["varB"] + EPS)); d2 = F(abs(t2) / F(x["sigB"] + EPS))
                    trimmed = classify(n2, d2, s2, indicator, mult)
                if cfg.get("trim_raw") and trimmed is not None:
                    raw = trimmed; trimmed = None          # alternative: classify on the trimmed window always
                prev_conf = x["gov"].conf if x["gov"].init else raw
                committed = x["gov"].update(raw, trimmed)
                conf = x["gov"].conf
                rec = (t, s, adc, raw, x["gov"].cand, x["gov"].run, conf, committed, nvi, ntd, sfi, x["gov"].spm(), trimmed)
                x["log"].append(rec)
                if committed:
                    x["scp"].append((t, s, conf, x["gov"].spm()))
            if mode == "fixed": iv = FIXED_INT
            elif mode == "threshold": iv = tb_int
            elif calibrating: iv = CAL_INT
            else: iv = INTERVAL[x["gov"].conf]
            x["interval"] = iv
            x["due"] = t + iv
    return dict(sensors=st, acq=out_acq, total=sum(out_acq))

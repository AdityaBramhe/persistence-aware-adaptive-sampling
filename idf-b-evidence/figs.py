import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import model
from evalcfg import *
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#444", "axes.labelcolor": "#222", "xtick.color": "#333", "ytick.color": "#333"})
BLUE, ORANGE, GRAY, INK = "#2B6CB0", "#C05621", "#6B7280", "#1f2937"

# ---------- Fig 4: worked trace of a single-sample transient --------------
cfgK3 = dict(K=3); cfgP = dict(K=2, integrity="noworse", Q=2)
pick = None
for sd in SEEDS:
    a = run("transient", sd, cfgK3); b = run("transient", sd, cfgP)
    c = run("transient_ctrl", sd, cfgK3)
    pk = lambda r: max([rec[6] for rec in r['sensors'][T_S]['log'] if 30000 <= rec[0] < 55000] or [0])
    inside = [rec for rec in b['sensors'][T_S]['log'] if 30000 <= rec[0] < 31200]
    if pk(a) >= 2 and pk(c) <= 1 and pk(b) <= pk(c) and inside:
        pick = sd; break
print("trace seed", pick)
a = run("transient", pick, cfgK3); b = run("transient", pick, cfgP)
la = a['sensors'][T_S]['log']; lb = b['sensors'][T_S]['log']
fig, ax = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True, gridspec_kw={"height_ratios": [1, 1.5]})
ts = [r[0] / 1000 for r in lb if r[0] >= 20000]; adcs = [r[2] for r in lb if r[0] >= 20000]
ax[0].plot(ts, adcs, "o-", color=INK, ms=3.5, lw=0.8)
ax[0].axvspan(30, 31.2, color=ORANGE, alpha=0.25, lw=0)
ax[0].set_ylabel("S3 reading\n(ADC counts)")
ax[0].text(31.6, max(adcs) * 0.93, "1.2 s pulse", color=ORANGE, fontsize=8, va="top")
def stairs(a_, key, **kw):
    rows = [r for r in a_ if r[0] >= 20000]
    ax[1].step([r[0] / 1000 for r in rows], [key(r) for r in rows], where="post", **kw)
stairs(lb, lambda r: r[3] + 0.0, color=GRAY, lw=1.0, ls=":", label="raw state (every window)")
stairs(la, lambda r: r[6] + 0.07, color=ORANGE, lw=1.8, label="confirmed: run-length K = 3")
stairs(lb, lambda r: r[6] - 0.07, color=BLUE, lw=1.8, label="confirmed: PQCG (K = 2, Q = 2)")
ax[1].axvspan(30, 31.2, color=ORANGE, alpha=0.25, lw=0)
ax[1].set_yticks([0, 1, 2, 3]); ax[1].set_yticklabels(["S", "M", "V", "U"]); ax[1].set_ylim(-0.4, 3.4)
ax[1].set_xlabel("time (s)"); ax[1].set_ylabel("operating state, channel S3")
ax[1].legend(frameon=False, fontsize=8, loc="lower right")
ax[0].set_xlim(20, 60)
fig.suptitle(f"Single-sample transient on S3 (seed {pick})", fontsize=10, color=INK, x=0.02, ha="left")
fig.tight_layout(); fig.savefig("fig/fig_trace.png", dpi=220); plt.close(fig)

# ---------- Fig 5: results (a) pulse width vs false escalation, (b) trade-off ----------
R = json.load(open("final_results.json"))
widths = [1200, 2500, 4500, 8000]
CF = {"K=2": dict(K=2), "K=3": dict(K=3), "K=5": dict(K=5),
      "PQCG Q=2": dict(K=2, integrity="noworse", Q=2), "PQCG Q=3": dict(K=2, integrity="noworse", Q=3)}
pw = {}
for name, cfg in CF.items():
    pw[name] = []
    for d in widths:
        model.T_DUR = d; hit = 0
        for sd in SEEDS:
            rt = run("transient", sd, cfg); rc = run("transient_ctrl", sd, cfg)
            pk = lambda r: max([rec[6] for rec in r['sensors'][T_S]['log'] if 30000 <= rec[0] < 55000] or [0])
            hit += pk(rt) > pk(rc)
        pw[name].append(100 * hit / len(SEEDS))
model.T_DUR = 1200
json.dump(pw, open("pulse_width.json", "w"), indent=1)
print(pw)
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.3))
ax = axs[0]
sty = {"K=2": (GRAY, "o", ":"), "K=3": (GRAY, "s", "--"), "K=5": (GRAY, "^", "-."), "PQCG Q=2": (BLUE, "o", "-"), "PQCG Q=3": (ORANGE, "D", "-")}
for name, v in pw.items():
    c, m, ls = sty[name]
    ax.plot(range(4), v, marker=m, color=c, ls=ls, lw=1.6, ms=5, label=name)
ax.set_xticks(range(4)); ax.set_xticklabels(["1.2", "2.5", "4.5", "8.0"])
ax.set_xlabel("pulse width (s)"); ax.set_ylabel("pulses causing a false escalation (%)")
ax.set_ylim(-3, 105); ax.legend(frameon=False, fontsize=7.5, loc="lower right"); ax.set_title("(a) transient rejection", fontsize=9, loc="left")
ax = axs[1]
pts = [("K=1", "K=1"), ("K=2 run-length", "K=2"), ("K=3 run-length", "K=3"), ("K=5 run-length", "K=5"), ("K=11 run-length", "K=11"),
       ("PQCG  K=2,Q=2", "PQCG Q=2"), ("PQCG  K=2,Q=3", "PQCG Q=3")]
keymap = {k: k for k in R if not k.startswith("_")}
for lab, short in [("K=1  (no persistence)", "K=1"), ("K=2  run-length", "K=2"), ("K=3  run-length", "K=3"), ("K=5  run-length", "K=5"), ("K=11 run-length", "K=11"),
                   ("PQCG  K=2,Q=2", "PQCG Q=2")]:
    v = R[lab]; isP = short.startswith("PQCG")
    col = BLUE if short == "PQCG Q=2" else ORANGE if short == "PQCG Q=3" else GRAY
    ax.scatter(v["step_med"], 100 * v["pulse_hit"] / 60, s=46, color=col, marker="o" if not short == "PQCG Q=3" else "D", zorder=3)
    dx, dy, ha = 0.5, 3, "left"
    if short == "K=1": dx, dy = 0.5, -9
    if short == "K=2": dx, dy, ha = -0.3, 6, "right"
    if short == "K=3": dx, dy = 0.0, 7; ha = "center"
    if short == "K=5": dx, dy = 0.5, 4
    if short == "K=11": dx, dy, ha = -0.5, 5, "right"
    if short == "PQCG Q=2": dx, dy = 0.7, 9; short = "PQCG (Q = 2 or 3)"
    if short == "PQCG Q=3": dx, dy = 0.5, -9
    ax.annotate(short, (v["step_med"], 100 * v["pulse_hit"] / 60), xytext=(v["step_med"] + dx, 100 * v["pulse_hit"] / 60 + dy), fontsize=7.5, color=INK, ha=ha)
ax.set_xlabel("median latency, step event (s)"); ax.set_ylabel("pulses causing a false escalation (%)")
ax.set_ylim(-6, 105); ax.set_xlim(-1, 24); ax.set_title("(b) cost of rejection: latency (1.2 s pulse)", fontsize=9, loc="left")
fig.tight_layout(); fig.savefig("fig/fig_results.png", dpi=220); plt.close(fig)

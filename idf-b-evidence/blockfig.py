import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
plt.rcParams["font.family"] = "DejaVu Sans"
fig, ax = plt.subplots(figsize=(7.4, 9.0)); ax.set_xlim(0, 12.4); ax.set_ylim(-0.4, 11.3); ax.axis("off")
W, H = 3.35, 1.25
cols = {0: 0.45, 1: 4.35, 2: 8.25}
def box(c, y, text, fill="white", bold=False, tag=""):
    x = cols[c]
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fill, ec="#222", lw=2.0 if bold else 1.1))
    ax.text(x + W / 2, y + H / 2, text, ha="center", va="center", fontsize=6.3, color="#111", linespacing=1.25)
    if tag: ax.text(x + 0.1, y + H - 0.08, tag, ha="left", va="top", fontsize=6.5, color="#555", fontweight="bold")
def arrow(p, q, dashed=False, lw=1.1, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=9, lw=lw, color="#222", ls="--" if dashed else "-", connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))
def line(pts, dashed=False, lw=1.1, head=True):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] if head else xs, ys[:-1] if head else ys, color="#222", lw=lw, ls="--" if dashed else "-", solid_capstyle="butt")
    if head: arrow(pts[-2], pts[-1], dashed=dashed, lw=lw)
SH = "#e6e6e6"
yA, yB1, yB2, yC, yD, yE = 8.7, 7.0, 5.3, 3.6, 1.95, 0.3
box(0, yA, "Acquisition scheduler\nnext sample after T_i", tag="A")
box(1, yA, "Sensor channel i\n(analog / digital front end)", tag="A")
box(2, yA, "Sliding window W_t\n(N most recent samples)", tag="A")
box(1, yB1, "Calibration baseline\nVAR_base, sigma_base\n(first 20 samples after warm-up)", tag="B")
box(2, yB1, "TVV engine\nVAR, TRD, SFI\n-> NVI, NTD, SFI", tag="B")
box(2, yB2, "State estimator\nraw state r_t in {S, M, V, U}", tag="B")
box(1, yB2, "Hysteresis band (optional)\nvs confirmed state c(t-1)", tag="B")
box(1, yC, "Evidence-support test\nremove Q-1 most deviant samples;\nre-estimate r'_t; qualified\nonly if r'_t >= r_t", fill=SH, bold=True, tag="C")
box(0, yC, "Run-length counter R_t\nand persistence metric SPM_t\n(held if window not qualified)", fill=SH, tag="C")
box(0, yD, "Commit controller\nR_t >= K_dir; reversal penalty;\ndwell lock; slew limit -> c_t", fill=SH, bold=True, tag="C")
box(1, yD, "Sensor-team manager\nRT / OT / RCT / IT\nfrom c_t and SPM_t", tag="D")
box(2, yD, "SCP generator\nevent-driven, atomic,\nsequence-numbered packet", tag="D")
box(2, yE, "Adaptive resource controller\npolicy table gives sampling T_s,\ncommunication T_c, priority P", tag="D")
cx = lambda c: cols[c] + W / 2
# A row
arrow((cols[0] + W, yA + H / 2), (cols[1], yA + H / 2)); ax.text((cols[0] + W + cols[1]) / 2, yA + H / 2 + 0.28, "trigger", ha="center", fontsize=6.0)
arrow((cols[1] + W, yA + H / 2), (cols[2], yA + H / 2))
# window -> TVV
arrow((cx(2), yA), (cx(2), yB1 + H))
# sensor -> calibration (dashed), calibration -> TVV (dashed)
arrow((cx(1), yA), (cx(1), yB1 + H), dashed=True); ax.text(cx(1) + 0.08, (yA + yB1 + H) / 2, "one-time", fontsize=6.3, va="center")
arrow((cols[1] + W, yB1 + H / 2), (cols[2], yB1 + H / 2), dashed=True)
# TVV -> estimator -> hysteresis -> evidence
arrow((cx(2), yB1), (cx(2), yB2 + H))
arrow((cols[2], yB2 + H / 2), (cols[1] + W, yB2 + H / 2))
arrow((cx(1), yB2), (cx(1), yC + H))
# window samples -> evidence (dashed, route outside right)
line([(cols[2] + W, yA + H / 2), (12.15, yA + H / 2), (12.15, yC + H / 2), (cols[1] + W, yC + H / 2)], dashed=True)
ax.text(12.22, 6.1, "window samples", rotation=90, fontsize=6.3, va="center", ha="left")
# evidence -> run-length -> commit
arrow((cols[1], yC + H / 2), (cols[0] + W, yC + H / 2))
arrow((cx(0), yC), (cx(0), yD + H))
# commit -> team -> SCP -> ARC
arrow((cols[0] + W, yD + H / 2), (cols[1], yD + H / 2)); ax.text((cols[0] + W + cols[1]) / 2, yD + H / 2 + 0.28, "commit", ha="center", fontsize=6.3)
arrow((cols[1] + W, yD + H / 2), (cols[2], yD + H / 2))
arrow((cx(2), yD), (cx(2), yE + H))
# confirmed state fed back to hysteresis (dashed, route via left margin)
line([(cols[0], yD + H / 2 + 0.25), (0.22, yD + H / 2 + 0.25), (0.22, 6.4), (cols[1] - 0.45, 6.4), (cols[1] - 0.45, yB2 + H / 2 - 0.2), (cols[1], yB2 + H / 2 - 0.2)], dashed=True)
ax.text(0.3, 6.55, "c(t) to hysteresis", fontsize=6.3, ha="left")
# control feedback ARC -> scheduler (bold, along bottom and far left)
line([(cols[2], yE + H / 2), (0.05, yE + H / 2), (0.05, yA + H / 2), (cols[0], yA + H / 2)], lw=1.9)
ax.text(2.2, yE + H / 2 + 0.12, "new sampling interval T_i  (closed loop)", fontsize=7, ha="left", fontweight="bold")
# legend
ax.add_patch(FancyBboxPatch((0.45, 10.75), 0.35, 0.2, boxstyle="square,pad=0", fc=SH, ec="#222", lw=1))
ax.text(0.9, 10.85, "persistence qualification (C); bold outline = evidence-support test and commit controller", fontsize=6.6, va="center")
ax.text(0.45, 10.4, "A sensing   B temporal health assessment   C persistence qualification   D governance and control", fontsize=6.6, va="center", color="#444")
fig.savefig("fig/fig_block.png", dpi=220, bbox_inches="tight", pad_inches=0.1)

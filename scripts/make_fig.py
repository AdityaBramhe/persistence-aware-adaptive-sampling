#!/usr/bin/env python3
"""Fig. 2: effect of the persistence requirement K (mixed-activity scenario, 10 paired seeds)."""
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

df = pd.read_csv('/home/claude/sim/results/all_runs.csv')
mix = df[df.scenario == 'MIXED']
BLUE, ORANGE, INK, MUTED, GRID = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e3e2dd'
plt.rcParams.update({'font.family': 'serif', 'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False})

def ci(v):
    v = np.asarray(v, float); v = v[~np.isnan(v)]
    h = stats.t.ppf(0.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
    return v.mean(), h

panels = [('ARR', 'Acquisition reduction, ARR (%)', 1.0, 'thr_arr'),
          ('TSR', 'Transition suppression, TSR (%)', 1.0, None),
          ('lat_sudden', 'Response latency to S3 step (s)', 1e-3, 'thr_lat')]
fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5))
rng = np.random.default_rng(3)
thr = mix[mix.method == 'threshold']
for ax, (col, ylab, scale, ref) in zip(axes, panels):
    for k in (1, 2, 3):
        v = mix[mix.method == f'adaptive_K{k}'].sort_values('seed')[col].values * scale
        ax.scatter(k + rng.uniform(-0.12, 0.12, len(v)), v, s=9, color=BLUE, alpha=0.35, linewidths=0, zorder=2)
        m, h = ci(v)
        ax.errorbar(k, m, yerr=h, color=BLUE, marker='o', ms=5, mfc=BLUE, mec='white', mew=1, lw=1.6, capsize=3, zorder=3)
    means = [ci(mix[mix.method == f'adaptive_K{k}'][col].values * scale)[0] for k in (1, 2, 3)]
    ax.plot([1, 2, 3], means, color=BLUE, lw=1.2, zorder=1)
    if ref:
        rv = thr[col if col != 'ARR' else 'ARR'].values * scale
        ax.axhline(np.nanmean(rv), color=ORANGE, lw=1.2, ls='--', zorder=1)
        ax.text(3.35, np.nanmean(rv), 'threshold\nbaseline', color=MUTED, fontsize=7, va='center', ha='left')
    ax.set_xticks([1, 2, 3]); ax.set_xlim(0.6, 3.5 if ref else 3.4); ax.set_xlabel('Persistence requirement $K$')
    ax.set_ylabel(ylab, fontsize=8); ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
    if col == 'TSR': ax.set_ylim(bottom=-2)
fig.text(0.005, 0.99, '', fontsize=1)
fig.tight_layout(w_pad=1.2)
fig.savefig('/home/claude/sim/paper/fig_K.pdf'); fig.savefig('/home/claude/sim/results/fig_K.png', dpi=200)
print('saved')

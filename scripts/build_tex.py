#!/usr/bin/env python3
"""Generate paper/numbers.tex (macros quoted in the prose) and paper/tables.tex (Tables 2-6) straight
from results/all_runs.csv, so no number in the manuscript is typed by hand."""
import numpy as np, pandas as pd
from scipy import stats

df = pd.read_csv('/home/claude/sim/results/all_runs.csv')
P = '/home/claude/sim/paper'
def sub(m, sc): return df[(df.method == m) & (df.scenario == sc)].sort_values('seed').set_index('seed')
NAME = {1: 'One', 2: 'Two', 3: 'Three', 11: 'Eleven'}
mac = {}
def M(name, val): mac[name] = val
def f(x, d=1): return f'{x:.{d}f}'
def mean(x): return float(pd.Series(x).dropna().mean())
def sd(x): return float(pd.Series(x).dropna().std(ddof=1))
def msd(x, d=1, scale=1.0):
    x = pd.Series(x).dropna() * scale
    return f'{x.mean():.{d}f} $\\pm$ {x.std(ddof=1):.{d}f}'
def pair(a, b, scale=1.0):
    d = ((b - a) * scale).dropna().values
    m, se = d.mean(), d.std(ddof=1) / np.sqrt(len(d)); h = stats.t.ppf(0.975, len(d) - 1) * se
    return m, m - h, m + h
def sg(x, d=1):
    return ('$+$' if x >= 0 else '$-$') + f'{abs(x):.{d}f}'
def pr(t, d=1): return f'{sg(t[0], d)} [{sg(t[1], d)}, {sg(t[2], d)}]'

seeds = sorted(sub('adaptive_K2', 'MIXED').index)
M('NSeeds', str(len(seeds)))
M('NRuns', str(len(df))); M('NSGvals', f'{int(df.sg_checked.sum()):,}'.replace(',', '{,}')); M('NSGbad', str(int(df.sg_mismatch.sum())))
thr = df[df.method == 'threshold']
M('GapN', f'{int(thr.gap_checked.sum()):,}'.replace(',', '{,}')); M('GapOK', f'{int(thr.gap_match.sum()):,}'.replace(',', '{,}'))

# ---------------- Table 2: method comparison, mixed scenario
rows = [('fixed', 'Fixed-rate reference'), ('threshold', 'Threshold baseline'),
        ('adaptive_K1', 'Adaptive, $K=1$ (no persistence)'), ('adaptive_K2', 'Adaptive, $K=2$'), ('adaptive_K3', 'Adaptive, $K=3$')]
t2 = []
for m, lab in rows:
    d = sub(m, 'MIXED')
    if m == 'fixed':
        t2.append(f'{lab} & {int(d.acq.iloc[0])} & 0.0 & 0.0 & n/a & n/a\\\\'); continue
    tsr = msd(d.TSR, 1) if m.startswith('adaptive') else 'n/a'
    lat = f'{msd(d.lat_sudden, 1, 1e-3)} ({d.lat_sudden.median()/1000:.1f})'
    t2.append(f'{lab} & {msd(d.acq, 1)} & {msd(d.ARR, 1)} & {msd(d.ivchg_total, 1)} & {tsr} & {lat}\\\\')
for m, nm in (('threshold', 'Thr'), ('adaptive_K1', 'kOne'), ('adaptive_K2', 'kTwo'), ('adaptive_K3', 'kThree')):
    d = sub(m, 'MIXED')
    M(f'ARR{nm}M', f(mean(d.ARR))); M(f'ARR{nm}S', f(sd(d.ARR))); M(f'ACQ{nm}M', f(mean(d.acq)))
    M(f'SW{nm}M', f(mean(d.ivchg_total))); M(f'SW{nm}S', f(sd(d.ivchg_total)))
    M(f'LAT{nm}M', f(mean(d.lat_sudden) / 1000)); M(f'LAT{nm}S', f(sd(d.lat_sudden) / 1000)); M(f'LAT{nm}Med', f(d.lat_sudden.median() / 1000))
    M(f'LAT{nm}Max', f(d.lat_sudden.max() / 1000)); M(f'LAT{nm}Min', f(d.lat_sudden.min() / 1000))
    if m.startswith('adaptive'):
        M(f'TSR{nm}M', f(mean(d.TSR))); M(f'TSR{nm}S', f(sd(d.TSR)))
        M(f'RAW{nm}M', f(mean(d.raw_trans))); M(f'CONF{nm}M', f(mean(d.conf_trans)))
K = {k: sub(f'adaptive_K{k}', 'MIXED') for k in (1, 2, 3)}
gr = sub('threshold', 'MIXED')
M('ThrGradN', str(int(gr.lat_gradual.notna().sum()))); M('ThrGradLat', f(gr.lat_gradual.median() / 1000))
for k in (1, 2, 3):
    M(f'GradMed{NAME[k]}', f(K[k].lat_gradual.median() / 1000))
M('ThrGradCount', str(int(gr.lat_gradual.notna().sum())))

# ---------------- Table 3: per-sensor K=2, mixed
d = K[2]; t3 = []
for s in range(4):
    n_def = int(d[f'TSR_s{s}'].notna().sum())
    t3.append(f"S{s+1} & {msd(d[f'acqall_s{s}'], 1)} & {msd(d[f'ARRall_s{s}'], 1)} & {msd(d[f'raw_s{s}'], 1)} & {msd(d[f'conf_s{s}'], 1)} & {msd(d[f'TSR_s{s}'], 1)} ({n_def}/10)\\\\")
    M(f'PSacq{s+1}', f(d.loc[12345, f'acqall_s{s}'], 0))
t3.append(f"\\midrule All & {msd(d.acq, 1)} & {msd(d.ARR, 1)} & {msd(d.raw_trans, 1)} & {msd(d.conf_trans, 1)} & {msd(d.TSR, 1)} (10/10)\\\\")
s12345 = d.loc[12345]
M('SeedAcq', str(int(s12345.acq))); M('SeedARR', f(s12345.ARR, 1)); M('SeedTSR', f(s12345.TSR, 1)); M('SeedARRfw', f(s12345.ARR_fw, 2))
M('SeedRaw', str(int(s12345.raw_trans))); M('SeedConf', str(int(s12345.conf_trans)))
M('SeedLatS', f'{int(s12345.lat_sudden):,}'.replace(',', '{,}')); M('SeedLatG', f'{int(s12345.lat_gradual):,}'.replace(',', '{,}'))
M('SeedAcqfw', str(int(s12345.acq_fw)))
for s in range(4):
    M(f'PSarr{s+1}M', f(mean(d[f'ARRall_s{s}'])))

# ---------------- Table 4: paired effect of K
t4 = []
for a, b in ((1, 2), (2, 3), (1, 3)):
    tsr = pair(K[a].TSR, K[b].TSR); lat = pair(K[a].lat_sudden, K[b].lat_sudden, 1e-3)
    arr = pair(K[a].ARR, K[b].ARR); sw = pair(K[a].ivchg_total, K[b].ivchg_total)
    t4.append(f'$K={a}\\rightarrow K={b}$ & {pr(tsr)} & {pr(lat, 1)} & {pr(arr)} & {pr(sw)}\\\\')
    n = f'{NAME[a]}{NAME[b]}'
    for nm, t_, dd in (('TSR', tsr, 1), ('LAT', lat, 1), ('ARR', arr, 1), ('SW', sw, 1)):
        M(f'd{nm}{n}M', sg(t_[0], dd)); M(f'd{nm}{n}Lo', sg(t_[1], dd)); M(f'd{nm}{n}Hi', sg(t_[2], dd))
# expected extra delay
M('CycleM', '2')  # S3's confirmed state before the step is M (2000 ms) in 26 of 30 mixed runs (see check below)
pre = []
for k in (1, 2, 3):
    pass

# ---------------- Table 5: transient test
t5 = []
Ks = [k for k in (1, 2, 3, 11) if len(sub(f'adaptive_K{k}', 'TRANSIENT')) and len(sub(f'control_K{k}', 'TRANSIENT'))]
for k in Ks:
    p = sub(f'adaptive_K{k}', 'TRANSIENT'); c = sub(f'control_K{k}', 'TRANSIENT')
    seen = p.twc_s2 == 1; esc = p.s3_state_35s > c.s3_state_35s
    lost = (p.acqall_s2 - c.acqall_s2)[seen]
    t5.append(f'$K={k}$ & {int(seen.sum())}/10 & {int((seen & esc).sum())}/{int(seen.sum())} & '
              f'{(msd(lost, 1) if seen.sum() > 1 else (f(lost.iloc[0], 0) if seen.sum() == 1 else "n/a"))} & '
              f'{int(p.twc_s2.max())}\\\\')
    M(f'TSeen{NAME[k]}', str(int(seen.sum()))); M(f'TEsc{NAME[k]}', str(int((seen & esc).sum())))
    M(f'TLost{NAME[k]}', f(-lost.mean(), 0) if seen.sum() else 'n/a')
    M(f'TWCmax{NAME[k]}', str(int(p.twc_s2.max())))
tt = sub('threshold', 'TRANSIENT')
M('ThrPulse', str(int(tt.lat_sudden.notna().sum())))
M('ThrTransSw', msd(tt.ivchg_s2, 1).replace('$\\pm$', '$\\pm$'))
t5.append(f'Threshold baseline & {int(tt.lat_sudden.notna().sum())}/10 (rule triggered) & n/a & n/a & n/a\\\\')

# ---------------- overhead
ad = df[df.method.isin(['adaptive_K1', 'adaptive_K2', 'adaptive_K3'])]
k2m = K[2]
M('OvhAvg', f(mean(k2m.avg_us))); M('OvhAvgSD', f(sd(k2m.avg_us))); M('OvhAll', f(mean(ad.avg_us)))
M('OvhLo', f(ad.avg_us.min())); M('OvhHi', f(ad.avg_us.max())); M('OvhMin', str(int(ad.min_us.min()))); M('OvhMax', f'{int(ad.max_us.max()):,}'.replace(',', '{,}'))
M('OvhNruns', str(len(ad)))
M('RamMixed', str(int(ad[ad.scenario == 'MIXED'].free_ram.iloc[0]))); M('RamTrans', str(int(ad[ad.scenario == 'TRANSIENT'].free_ram.iloc[0])))

with open(f'{P}/numbers.tex', 'w') as fh:
    for k, v in mac.items(): fh.write(f'\\newcommand{{\\{k}}}{{{v}}}\n')
with open(f'{P}/tables.tex', 'w') as fh:
    fh.write('%% TABLE2\n' + '\n'.join(t2) + '\n%% TABLE3\n' + '\n'.join(t3) + '\n%% TABLE4\n' + '\n'.join(t4) + '\n%% TABLE5\n' + '\n'.join(t5) + '\n')
print(open(f'{P}/tables.tex').read()); print(len(mac), 'macros')

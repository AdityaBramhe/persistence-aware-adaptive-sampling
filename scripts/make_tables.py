#!/usr/bin/env python3
"""Aggregate all_runs.csv into the tables used in the paper (mean +/- SD over 10 paired seeds)."""
import numpy as np, pandas as pd, json
from scipy import stats

R = '/home/claude/sim/results'
df = pd.read_csv(f'{R}/all_runs.csv')
SEEDS = sorted(df[df.method == 'adaptive_K2'].seed.unique())

def ms(x, d=2):
    x = pd.Series(x).dropna()
    if len(x) == 0: return 'n/a'
    if len(x) == 1: return f'{x.iloc[0]:.{d}f}'
    return f'{x.mean():.{d}f} ± {x.std(ddof=1):.{d}f}'

def paired(a, b):
    """mean(b-a) and 95% t-CI, paired by seed; returns (mean, lo, hi, p_wilcoxon)."""
    d = (b - a).dropna().values
    if len(d) < 3: return (np.nan,) * 4
    m, se = d.mean(), d.std(ddof=1) / np.sqrt(len(d))
    h = stats.t.ppf(0.975, len(d) - 1) * se
    try: p = stats.wilcoxon(d).pvalue
    except ValueError: p = np.nan
    return m, m - h, m + h, p

def sub(method, scen):
    return df[(df.method == method) & (df.scenario == scen)].sort_values('seed').set_index('seed')

out = {}
methods = [('fixed', 'Fixed-rate'), ('threshold', 'Threshold baseline'),
           ('adaptive_K1', 'Adaptive, K = 1 (no persistence)'), ('adaptive_K2', 'Adaptive, K = 2'), ('adaptive_K3', 'Adaptive, K = 3')]

# ---------- Table A: method comparison, mixed-activity scenario -------------------------
rowsA = []
for m, label in methods:
    d = sub(m, 'MIXED')
    rowsA.append(dict(Method=label, n=len(d), Acquisitions=ms(d.acq, 1), ARR=ms(d.ARR, 2),
                      RateSwitches=ms(d.ivchg_total, 1),
                      RawTrans=ms(d.raw_trans, 1) if m.startswith('adaptive') else 'n/a',
                      ConfTrans=ms(d.conf_trans, 1) if m.startswith('adaptive') else 'n/a',
                      TSR=ms(d.TSR, 1) if m.startswith('adaptive') else 'n/a',
                      SuddenLatency=ms(d.lat_sudden, 0) if m != 'fixed' else 'n/a',
                      SuddenMedian=(f'{d.lat_sudden.median():.0f}' if m != 'fixed' else 'n/a'),
                      SuddenDetected=(f'{int(d.lat_sudden.notna().sum())}/{len(d)}' if m != 'fixed' else 'n/a')))
tA = pd.DataFrame(rowsA); tA.to_csv(f'{R}/tableA_method_comparison_mixed.csv', index=False); out['A'] = rowsA

# ---------- Table B: per-sensor, mixed scenario, K=2 (mean over seeds) ------------------
d = sub('adaptive_K2', 'MIXED')
rowsB = []
for s in range(4):
    rowsB.append(dict(Sensor=f'S{s+1}', Acq=ms(d[f'acq_s{s}'], 1), ARR=ms(d[f'ARR_s{s}'], 1),
                      Raw=ms(d[f'raw_s{s}'], 1), Conf=ms(d[f'conf_s{s}'], 1), TSR=ms(d[f'TSR_s{s}'], 1),
                      seed12345=dict(acq=int(d.loc[12345, f'acq_s{s}']), arr=float(d.loc[12345, f'ARR_s{s}']),
                                     raw=int(d.loc[12345, f'raw_s{s}']), conf=int(d.loc[12345, f'conf_s{s}']),
                                     tsr=None if pd.isna(d.loc[12345, f'TSR_s{s}']) else float(d.loc[12345, f'TSR_s{s}']))))
pd.DataFrame(rowsB).drop(columns='seed12345').to_csv(f'{R}/tableB_per_sensor_K2.csv', index=False); out['B'] = rowsB

# ---------- Table C: effect of K (paired) ------------------------------------------------
rowsC = []
K = {k: sub(f'adaptive_K{k}', 'MIXED') for k in (1, 2, 3)}
for k in (1, 2, 3):
    d = K[k]
    rowsC.append(dict(K=k, ARR=ms(d.ARR, 2), TSR=ms(d.TSR, 1), Lat=ms(d.lat_sudden, 0), LatMedian=f'{d.lat_sudden.median():.0f}',
                      LatMax=f'{d.lat_sudden.max():.0f}', ConfTrans=ms(d.conf_trans, 1)))
pairsC = {}
for a, b in ((1, 2), (2, 3), (1, 3)):
    for met in ('ARR', 'TSR', 'lat_sudden', 'conf_trans'):
        m, lo, hi, p = paired(K[a][met], K[b][met])
        pairsC[f'K{a}->K{b}:{met}'] = dict(mean=m, lo=lo, hi=hi, p_wilcoxon=p)
out['C'] = rowsC; out['C_paired'] = pairsC
pd.DataFrame(rowsC).to_csv(f'{R}/tableC_effect_of_K.csv', index=False)

# ---------- Table D: transient-disturbance test (S3 pulse) -------------------------------
rowsD = []
for m, label in methods:
    d = sub(m, 'TRANSIENT')
    r = dict(Method=label, n=len(d), Acquisitions=ms(d.acq, 1), ARR=ms(d.ARR, 2), RateSwitchesS3=ms(d.ivchg_s2, 1),
             RateSwitchesAll=ms(d.ivchg_total, 1))
    if m.startswith('adaptive'):
        r['TWC'] = f'{d.twc_s2.min():.0f}–{d.twc_s2.max():.0f} (mean {d.twc_s2.mean():.1f})'
        r['RawChgInWindow'] = ms(d.s3_rawchg_in_30_33s, 1)
        r['ConfInWindow'] = ms(d.s3_conf_in_30_33s, 1)
        r['RunsWithPulseConfirmed'] = f'{int((d.s3_conf_in_30_33s > 0).sum())}/{len(d)}'
        r['S3ConfTotal'] = ms(d.conf_s2, 1)
        r['ResponseLogged'] = f'{int(d.lat_sudden.notna().sum())}/{len(d)}'
    else:
        r['TWC'] = r['RawChgInWindow'] = r['ConfInWindow'] = r['RunsWithPulseConfirmed'] = r['S3ConfTotal'] = r['ResponseLogged'] = 'n/a'
    if m == 'threshold':
        r['ThresholdPulseDetected'] = f'{int(d.lat_sudden.notna().sum())}/{len(d)}'
    rowsD.append(r)
out['D'] = rowsD
pd.DataFrame(rowsD).to_csv(f'{R}/tableD_transient.csv', index=False)

# ---------- Overhead ----------------------------------------------------------------------
ad = df[df.method.str.startswith('adaptive')]
out['overhead'] = dict(avg_mean=float(ad.avg_us.mean()), avg_min=float(ad.avg_us.min()), avg_max=float(ad.avg_us.max()),
                       min_us=int(ad.min_us.min()), max_us=int(ad.max_us.max()), free_ram=sorted(ad.free_ram.unique().tolist()),
                       n_runs=len(ad), k2_mixed_seed12345_avg=float(sub('adaptive_K2', 'MIXED').loc[12345, 'avg_us']))
out['checks'] = dict(runs=len(df), sg_values=int(df.sg_checked.sum()), sg_mismatch=int(df.sg_mismatch.sum()),
                     iv_checked=int(df.iv_checked.sum()) if 'iv_checked' in df else 0,
                     iv_mismatch=int(df.iv_mismatch.sum()) if 'iv_mismatch' in df else 0)
json.dump(out, open(f'{R}/tables.json', 'w'), indent=1, default=str)

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
for k in ('A', 'B', 'C', 'D'):
    print(f'\n=== Table {k} ==='); print(pd.DataFrame(out[k]).drop(columns=['seed12345'], errors='ignore').to_string(index=False))
print('\n=== paired K comparisons (mean diff, 95% CI, Wilcoxon p) ===')
for k, v in pairsC.items(): print(f'{k:22s} {v["mean"]:9.2f}  [{v["lo"]:8.2f}, {v["hi"]:8.2f}]  p={v["p_wilcoxon"]:.3f}')
print('\noverhead', out['overhead']); print('checks', out['checks'])

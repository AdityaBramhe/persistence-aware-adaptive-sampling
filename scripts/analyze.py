#!/usr/bin/env python3
"""Parse the emulator logs, cross-check them, and build every number used in the paper."""
import os, re, glob, json, math
import numpy as np, pandas as pd
from scipy import stats

HERE = '/home/claude/sim'
RUNS = f'{HERE}/runs'
OUT = f'{HERE}/results'
os.makedirs(OUT, exist_ok=True)
M32 = 0xFFFFFFFF
NOISE_AMP = [2, 18, 55, 130]
F32 = np.float32

# ---------------- exact replica of signal_generator.h (used only as a cross-check
# and to reconstruct the threshold baseline's decision from logged timestamps) -------
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
    return sg_hash(s, t, seed) % (2 * amp + 1) - amp

def sg_amp(s, scen):
    if scen == 'MIXED': return NOISE_AMP[s]
    return NOISE_AMP[s] if (scen == 'TRANSIENT' and s == 2) else 2

def sg_drift(s, t, scen):
    ts = t // 1000
    if scen == 'MIXED':
        if s == 1 and 20 <= ts <= 40:
            progress = F32(ts - 20) / F32(20)
            return int(F32(60.0) * progress)
        if s == 2 and 30 <= ts < 40: return 220
    if scen == 'TRANSIENT' and s == 2 and 30000 <= t < 31200: return 220
    return 0

def sg_adc(s, t, seed, scen, pin=0):
    v = pin + sg_noise(s, t, seed, sg_amp(s, scen)) + sg_drift(s, t, scen)
    return max(0, min(1023, v))

# ---------------- log parsing ---------------------------------------------------------
def kv(line):
    return dict(p.split('=', 1) for p in line.split(',') if '=' in p)

def parse(path):
    r = dict(sensor={}, total={}, ev={}, samples={0: [], 1: [], 2: [], 3: []}, data={0: [], 1: [], 2: [], 3: []})
    for line in open(path, errors='replace').read().splitlines():
        f = line.split(',')
        if line.startswith('RUN_CONFIG'):
            r['cfg'] = kv(line)
        elif line.startswith('WARMUP,'):
            t, s, a = int(f[1]), int(f[2]), int(f[3]); r['samples'][s].append((t, a))
        elif line.startswith('CALIBRATION,'):
            r['samples'][int(f[2])].append((int(f[1]), None))
        elif line.startswith('DATA,'):
            if not f[1].isdigit(): continue   # skip the banner's column-key line
            t, s, a = int(f[1]), int(f[2]), int(f[3])
            r['samples'][s].append((t, a))
            r['data'][s].append(dict(t=t, adc=a, raw=f[10], conf=f[13], interval=int(f[14]), ctrans=int(f[15])))
        elif line.startswith('SENSOR_SUMMARY'):
            d = kv(line); d['transient_window_classifications'] = d.get('transient_window_classifications', '').split(' ')[0]
            r['sensor'][int(d['s'])] = d
        elif line.startswith('TOTAL,'):
            r['total'] = kv(line)
        elif line.startswith('OVERHEAD,classification_cycles'):
            r['ovh'] = kv(line)
        elif line.startswith('OVERHEAD,free_ram_bytes'):
            r['free_ram'] = int(line.split('=')[1])
        elif line.startswith('EVENT_RESPONSE'):
            d = kv(line); r['ev'][int(d['sensor'])] = int(d['latency_ms'])
    r['complete'] = bool(r['total'])
    return r

def name_meta(n):
    m = re.match(r'(adaptive|threshold|fixed)_(MIXED|TRANSIENT)_?(?:SENSORS|DISTURBANCE)?_?(?:K(\d))?_?s(\d+)', n)
    kind, scen, K, seed = m.group(1), m.group(2), m.group(3), int(m.group(4))
    method = f'adaptive_K{K}' if kind == 'adaptive' else kind
    return method, scen, seed

def analyse_run(name):
    path = f'{RUNS}/{name}/run.log'
    if not os.path.exists(path): return None
    r = parse(path)
    if not r['complete']: return None
    method, scen, seed = name_meta(name)
    row = dict(name=name, method=method, scenario=scen, seed=seed)
    tot = r['total']
    row['acq'] = int(tot['acquisitions'])
    row['ARR'] = float(tot['ARR_pct'])
    row['raw_trans'] = int(tot['raw_transitions']); row['conf_trans'] = int(tot['confirmed_transitions'])
    for s in range(4):
        d = r['sensor'][s]
        row[f'acq_s{s}'] = int(d['acquisitions']); row[f'ARR_s{s}'] = float(d['ARR_pct'])
        row[f'raw_s{s}'] = int(d['raw_transitions']); row[f'conf_s{s}'] = int(d['confirmed_transitions'])
        row[f'TSR_s{s}'] = float(d['TSR_pct']) if d['TSR_pct'] != 'n/a' else np.nan
        row[f'final_s{s}'] = d['final_confirmed_state']
    row['TSR'] = 100.0 * (row['raw_trans'] - row['conf_trans']) / row['raw_trans'] if row['raw_trans'] else np.nan
    row['twc_s2'] = int(r['sensor'][2]['transient_window_classifications']) if r['sensor'][2]['transient_window_classifications'] else np.nan
    row['lat_sudden'] = r['ev'].get(2, np.nan)
    row['lat_gradual'] = r['ev'].get(1, np.nan)
    row['avg_us'] = float(r['ovh']['avg_us']); row['min_us'] = int(r['ovh']['min_us']); row['max_us'] = int(r['ovh']['max_us'])
    row['free_ram'] = r['free_ram']

    # signal-generator cross-check on every logged ADC value
    bad = 0; n = 0
    gscen = scen
    for s in range(4):
        for (t, a) in r['samples'][s]:
            if a is None: continue
            n += 1
            if sg_adc(s, t, seed, gscen) != a: bad += 1
    row['sg_checked'] = n; row['sg_mismatch'] = bad

    # ---- interval-change events (sampling-rate switches) per sensor ---------------
    if method.startswith('adaptive'):
        for s in range(4):
            iv = [d['interval'] for d in r['data'][s]]
            row[f'ivchg_s{s}'] = sum(1 for a, b in zip(iv, iv[1:]) if a != b)
        # pulse / event windows on S3 (sensor index 2)
        w = [d for d in r['data'][2] if 30000 <= d['t'] < 33000]
        row['s3_conf_in_30_33s'] = sum(d['ctrans'] for d in w)
        wr = [d for d in r['data'][2] if 29000 <= d['t'] < 33000]
        row['s3_rawchg_in_30_33s'] = sum(1 for a, b in zip(wr, wr[1:]) if a['raw'] != b['raw'] and b['t'] >= 30000)
    elif method == 'threshold':
        # reconstruct the baseline's rule from logged sample times: delta > 0.05 -> 1000 ms else 4000 ms
        bad_iv = 0; nchk = 0
        det = {}
        for s in range(4):
            ts = [t for (t, _) in sorted(r['samples'][s])]
            x = [F32(sg_adc(s, t, seed, scen)) / F32(1023.0) for t in ts]
            iv = []
            for i in range(len(ts)):
                if i == 0: iv.append(1000)
                else: iv.append(1000 if abs(x[i] - x[i - 1]) > F32(0.05) else 4000)
            # verify against logged intervals for DATA rows
            dmap = {d['t']: d['interval'] for d in r['data'][s]}
            for t, v in zip(ts, iv):
                if t in dmap:
                    nchk += 1; bad_iv += (dmap[t] != v)
            row[f'ivchg_s{s}'] = sum(1 for a, b in zip(iv, iv[1:]) if a != b)
            onset = {1: 20000, 2: 30000}.get(s) if scen == 'MIXED' else ({2: 30000}.get(s))
            if onset is not None:
                lat = np.nan
                for i in range(1, len(ts)):
                    if ts[i] >= onset and abs(x[i] - x[i - 1]) > F32(0.05):
                        lat = ts[i] - onset; break
                det[s] = lat
        row['iv_checked'] = nchk; row['iv_mismatch'] = bad_iv
        row['lat_sudden'] = det.get(2, np.nan); row['lat_gradual'] = det.get(1, np.nan)
    else:  # fixed
        for s in range(4): row[f'ivchg_s{s}'] = 0
    row['ivchg_total'] = sum(row[f'ivchg_s{s}'] for s in range(4))
    return row

def main():
    names = sorted(os.listdir(RUNS))
    rows = [analyse_run(n) for n in names]
    rows = [r for r in rows if r]
    df = pd.DataFrame(rows)
    df.to_csv(f'{OUT}/all_runs.csv', index=False)
    print(len(df), 'complete runs')
    print('signal-generator cross-check: values checked =', int(df.sg_checked.sum()), ' mismatches =', int(df.sg_mismatch.sum()))
    thr = df[df.method == 'threshold']
    if len(thr):
        print('threshold-rule cross-check: intervals checked =', int(thr.iv_checked.sum()), ' mismatches =', int(thr.iv_mismatch.sum()))
    return df

if __name__ == '__main__':
    main()

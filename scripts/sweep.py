#!/usr/bin/env python3
"""Build + emulate every run in the reduced experiment set.

Each run = the unmodified firmware with only the config.h macros (mode, K, seed,
baseline signal source) changed, compiled with avr-gcc and executed for 60 s of
AVR time in avr8js.  Logs land in runs/<name>/run.log.
"""
import os, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor

HERE = '/home/claude/sim'
A = '/usr/share/arduino/hardware/arduino/avr'
SEEDS = [12345, 20240, 31415, 27182, 16180, 14142, 17320, 22360, 26457, 30103]

def jobs():
    out = []
    for scen in ('MIXED_SENSORS', 'TRANSIENT_DISTURBANCE'):
        for K in (1, 2, 3):
            for sd in SEEDS:
                out.append((f'adaptive_{scen}_K{K}_s{sd}', f'MODE_{scen}', K, sd, 'MODE_MIXED_SENSORS'))
        for sd in SEEDS:
            out.append((f'threshold_{scen}_s{sd}', 'MODE_THRESHOLD_BASELINE', 2, sd, f'MODE_{scen}'))
        out.append((f'fixed_{scen}_s{SEEDS[0]}', 'MODE_FIXED_RATE', 2, SEEDS[0], f'MODE_{scen}'))
    return out

def run(job):
    name, mode, K, seed, basesrc = job
    d = f'{HERE}/runs/{name}'
    if os.path.exists(f'{d}/run.log') and os.path.getsize(f'{d}/run.log') > 0 and 'EXPERIMENT_SUMMARY' in open(f'{d}/run.log', errors='replace').read():
        return name, 'cached'
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(HERE):
        if f.endswith('.h'):
            shutil.copy(f'{HERE}/{f}', d)
    cfg = open(f'{d}/config.h').read().splitlines()
    for i, l in enumerate(cfg):
        if l.startswith('#define EXPERIMENT_MODE'):        cfg[i] = f'#define EXPERIMENT_MODE  {mode}'
        elif l.startswith('#define PERSISTENCE_K'):         cfg[i] = f'#define PERSISTENCE_K  {K}'
        elif l.startswith('#define RANDOM_SEED'):           cfg[i] = f'#define RANDOM_SEED  {seed}UL'
        elif l.startswith('#define BASELINE_SIGNAL_SOURCE'): cfg[i] = f'#define BASELINE_SIGNAL_SOURCE  {basesrc}'
    open(f'{d}/config.h', 'w').write('\n'.join(cfg) + '\n')
    shutil.copy(f'{HERE}/sketch.ino', f'{d}/sketch.cpp')
    cf = ['-mmcu=atmega328p', '-DF_CPU=16000000L', '-DARDUINO=10819', '-DARDUINO_AVR_UNO',
          '-DARDUINO_ARCH_AVR', '-Os', '-w', '-ffunction-sections', '-fdata-sections']
    inc = [f'-I{d}', f'-I{A}/cores/arduino', f'-I{A}/variants/standard']
    subprocess.check_call(['avr-g++'] + cf + ['-std=gnu++11', '-fno-exceptions', '-fno-threadsafe-statics', '-flto']
                          + inc + ['-c', f'{d}/sketch.cpp', '-o', f'{d}/sketch.o'])
    subprocess.check_call(['avr-gcc', '-mmcu=atmega328p', '-Os', '-flto', '-fuse-linker-plugin', '-Wl,--gc-sections',
                           f'{d}/sketch.o', f'{HERE}/core/core.a', '-lm', '-o', f'{d}/fw.elf'])
    subprocess.check_call(['avr-objcopy', '-O', 'ihex', '-R', '.eeprom', f'{d}/fw.elf', f'{d}/fw.hex'])
    subprocess.check_call(['node', f'{HERE}/run.js', f'{d}/fw.hex', f'{d}/run.log', '61'], stderr=subprocess.DEVNULL)
    for f in ('sketch.o', 'sketch.cpp'):
        os.remove(f'{d}/{f}')
    return name, 'ok'

if __name__ == '__main__':
    js = jobs()
    print(len(js), 'runs', flush=True)
    with ThreadPoolExecutor(max_workers=2) as ex:
        for i, (n, st) in enumerate(ex.map(run, js), 1):
            print(f'[{i}/{len(js)}] {n} {st}', flush=True)

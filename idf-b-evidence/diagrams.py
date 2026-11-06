import subprocess, textwrap
FONT = 'fontname="Helvetica" fontsize=11'
def dot(name, src):
    open(f"fig/{name}.dot", "w").write(src)
    subprocess.run(["dot", "-Tpng", "-Gdpi=200", f"fig/{name}.dot", "-o", f"fig/{name}.png"], check=True)

# ---------------- FIG 1: end-to-end block diagram ----------------
dot("fig_block", f'''
digraph G {{
  rankdir=TB; nodesep=0.35; ranksep=0.42; splines=ortho; bgcolor=white;
  node [shape=box style="rounded" {FONT} margin="0.12,0.07" color="#222222" penwidth=1.2];
  edge [color="#222222" penwidth=1.1 arrowsize=0.8 {FONT}];

  subgraph cluster_a {{ label="A  SENSING"; labeljust=l; {FONT} style=dashed color="#777777";
    ADC [label="Sensor channel i\\n(analog / digital front end)"];
    SCH [label="Acquisition scheduler\\nnext sample after T_i"];
    WIN [label="Sliding window W_t\\n(N most recent samples)"];
    CAL [label="Calibration baseline\\nVAR_base, sigma_base\\n(per channel, one-time)"];
  }}
  subgraph cluster_b {{ label="B  TEMPORAL HEALTH ASSESSMENT"; labeljust=l; {FONT} style=dashed color="#777777";
    TVV [label="TVV engine\\nVAR, TRD, SFI  ->  NVI, NTD, SFI"];
    EST [label="State estimator\\nraw state r_t in {{S, M, V, U}}"];
    HYS [label="Hysteresis band (optional)\\nrelative to confirmed state c_(t-1)"];
  }}
  subgraph cluster_c {{ label="C  PERSISTENCE QUALIFICATION (decision mechanism)"; labeljust=l; {FONT} style=dashed color="#777777";
    EVT [label="Evidence-support test\\nre-estimate r'_t with Q-1 most deviant\\nsamples removed; qualifies if r'_t >= r_t" shape=box style="rounded,bold" penwidth=2.2];
    PER [label="Run-length counter R_t and SPM_t\\n(held when window not qualified)"];
    COM [label="Commit controller\\nR_t >= K_dir ?  reversal penalty, dwell, slew limit\\n-> confirmed state c_t"];
  }}
  subgraph cluster_d {{ label="D  GOVERNANCE AND CONTROL"; labeljust=l; {FONT} style=dashed color="#777777";
    TEAM [label="Sensor-team manager\\nRT / OT / RCT / IT from c_t, SPM_t"];
    SCP [label="SCP generator\\nevent-driven; one atomic packet\\nper sensor, sequence-numbered"];
    ARC [label="Adaptive resource controller\\npolicy table: sampling interval T_s,\\ncommunication interval T_c, priority P"];
  }}
  ADC -> WIN; SCH -> ADC [label=" trigger"]; WIN -> TVV; CAL -> TVV [style=dashed]; ADC -> CAL [style=dashed label=" first 20 samples"];
  TVV -> EST; EST -> HYS; HYS -> EVT; WIN -> EVT [style=dashed label=" window samples"];
  EVT -> PER; PER -> COM; COM -> TEAM [label=" commit"]; TEAM -> SCP; SCP -> ARC;
  ARC -> SCH [label=" new T_i" constraint=false penwidth=1.8];
  COM -> HYS [style=dashed constraint=false label=" c_t"];
}}''')

# ---------------- FIG 2: per-cycle decision procedure ----------------
dot("fig_flow", f'''
digraph G {{
  rankdir=TB; nodesep=0.35; ranksep=0.28; bgcolor=white; newrank=true;
  node [shape=box style="rounded" fontname="Helvetica" fontsize=13 margin="0.10,0.05" color="#222222" penwidth=1.3];
  edge [color="#222222" penwidth=1.2 arrowsize=0.8 fontname="Helvetica" fontsize=12];
  s  [label="New sample x_t; push into window"];
  d1 [label="Warm-up and\\ncalibration done?" shape=diamond style=""];
  w1 [label="Bootstrap cadence;\\nno control action"];
  f  [label="VAR, TRD, SFI of window\\nNVI, NTD (calibrated)"];
  r  [label="Raw state r_t\\n(hysteresis band vs c)"];
  e  [label="Remove Q-1 most deviant samples;\\nre-estimate r'_t" style="rounded,bold" penwidth=2.2];
  d2 [label="r'_t not less\\nsevere than r_t?" shape=diamond style="bold" penwidth=2.2];
  h  [label="HOLD: window unqualified;\\nR_t unchanged"];
  u  [label="Qualified: update candidate\\nand run-length R_t"];
  d3 [label="candidate != c and\\nR_t >= K_eff?" shape=diamond style=""];
  d4 [label="dwell lock open or\\njump >= 2 levels?" shape=diamond style=""];
  c  [label="COMMIT: c_t = candidate\\n(slew-limited)"];
  t  [label="Update team\\nfrom c_t, SPM_t"];
  p  [label="Emit one SCP;\\napply policy row;\\nnext sample after T_s(c_t)"];
  n  [label="No change;\\nkeep current interval"];
  s -> d1; d1 -> w1 [label=" no"]; d1 -> f [label=" yes"]; f -> r; r -> e; e -> d2;
  d2 -> h [label=" no"]; d2 -> u [label=" yes"]; u -> d3; d3 -> d4 [label=" yes"]; d3 -> n [label=" no"];
  d4 -> c [label=" yes"]; d4 -> n [label=" no"]; c -> t; t -> p; h -> n;
  {{rank=same; d1; w1}} {{rank=same; d2; h}} {{rank=same; d3; n}}
}}''')

# ---------------- FIG 3: state model ----------------
dot("fig_states", f'''
digraph G {{
  rankdir=LR; nodesep=0.9; ranksep=1.1; bgcolor=white;
  node [shape=circle width=0.8 {FONT} color="#222222" penwidth=1.5];
  edge [color="#222222" penwidth=1.1 arrowsize=0.8 fontname="Helvetica" fontsize=9];
  S [label="S\\nstable\\nT=1 s"]; M [label="M\\nmoderate\\nT=2 s"]; V [label="V\\nhigh\\nT=4 s"]; U [label="U\\nunstable\\nT=8 s"];
  S -> M [label="R>=K_up,\\nsupported" ]; M -> V [label="R>=K_up,\\nsupported"]; V -> U [label="R>=K_up,\\nsupported"];
  M -> S [label="R>=K_dn" constraint=false]; V -> M [label="R>=K_dn" constraint=false]; U -> V [label="R>=K_dn" constraint=false];
  S -> S [label="window not\\nqualified:\\nhold"];
}}''')
print("diagrams ok")

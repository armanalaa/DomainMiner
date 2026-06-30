

from __future__ import annotations
import os

import argparse
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger(__name__)



class Config:
    INPUT_DIR     = Path("ccm_output")
    OUT_DIR       = Path("ccm_output")

    # ΓöÇΓöÇ Input files (produced by Steps 3.1ΓÇô3.3) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    P_STAT_FILE   = "step3_P_stat.csv"          # 130├ù130 statistical distance matrix
    P_NAME_FILE   = "step3_P_name.csv"          # 130├ù130 name similarity matrix
    P_SEM_FILE    = "step3_P_sem.csv"           # 130├ù130 semantic similarity matrix
    WEIGHTS_FILE  = "derived_weights.csv"       # variance-based weights from derive_weights.py

    # ΓöÇΓöÇ Output files ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    LONG_OUT_FILE = "step3_Sim_attr_long.csv"   # all 8385 pairs with Sim_attr (line 24)
    SIM_ATTR_FILE = "step3_Sim_attr.csv"        # 130├ù130 Sim_attr matrix
    EDGES_FILE    = "step3_graph_edges.csv"     # edges above theta_A (line 27-28)
    REPORT_FILE   = "step3_sim_attr_report.txt"

    # ΓöÇΓöÇ Fallback weights (used only if derived_weights.csv not found) ΓöÇΓöÇΓöÇΓöÇΓöÇ
    W1 = 0.40   # weight for (1 - P_stat_norm)  ΓÇö statistical similarity
    W2 = 0.55   # weight for P_name             ΓÇö name similarity
    W3 = 0.05   # weight for P_sem              ΓÇö semantic similarity

    # Step 3.5 threshold
    THETA_A = 0.60


# =============================================================================
# STEP 3.4.1 ΓÇö FEATURE VECTOR
# =============================================================================

def load_features(input_dir: Path) -> pd.DataFrame:
    """
    Step 3.4.1 ΓÇö Build feature vector x_ij = [P_stat, P_name, P_sem]

    Reads the three 130├ù130 matrix CSVs produced by Steps 3.1ΓÇô3.3
    and converts them to a long-format DataFrame ΓÇö one row per column pair.
    Only the upper triangle is kept (each unordered pair once).

    Inputs:
      step3_P_stat.csv  ΓÇö statistical distance   (lower = more similar)
      step3_P_name.csv  ΓÇö name similarity        (higher = more similar)
      step3_P_sem.csv   ΓÇö semantic similarity    (higher = more similar)
    """
    p_stat_path = input_dir / Config.P_STAT_FILE
    p_name_path = input_dir / Config.P_NAME_FILE
    p_sem_path  = input_dir / Config.P_SEM_FILE

    for p in [p_stat_path, p_name_path, p_sem_path]:
        if not p.exists():
            raise FileNotFoundError(
                f"Input file not found: {p}. "
                "Run ccm_step3_proximity.py first to produce Steps 3.1-3.3 outputs."
            )

    log.info("Loading Step 3.1ΓÇô3.3 outputs from %s ...", input_dir)
    P_stat = pd.read_csv(p_stat_path, index_col=0)
    P_name = pd.read_csv(p_name_path, index_col=0)
    P_sem  = pd.read_csv(p_sem_path,  index_col=0)

    # Validate that all three matrices share the same columns/index
    assert list(P_stat.index) == list(P_name.index) == list(P_sem.index),         "Row indices of P_stat, P_name, P_sem do not match ΓÇö check source files."
    assert list(P_stat.columns) == list(P_name.columns) == list(P_sem.columns),         "Column indices of P_stat, P_name, P_sem do not match ΓÇö check source files."

    cols = list(P_stat.columns)
    log.info("  Matrices loaded: %d columns ΓåÆ %d pairs (upper triangle)",
             len(cols), len(cols)*(len(cols)-1)//2)

    # Convert wide ΓåÆ long (upper triangle only, no self-pairs)
    records = []
    for i, ci in enumerate(cols):
        for j, cj in enumerate(cols):
            if j <= i:
                continue
            ti = ci.rsplit(".", 1)[0] if "." in ci else ci
            tj = cj.rsplit(".", 1)[0] if "." in cj else cj
            records.append({
                "col_i":   ci,
                "col_j":   cj,
                "table_i": ti,
                "table_j": tj,
                "P_stat":  float(P_stat.loc[ci, cj]),
                "P_name":  float(P_name.loc[ci, cj]),
                "P_sem":   float(P_sem.loc[ci,  cj]),
            })

    long = pd.DataFrame(records)
    log.info("  P_stat range : [%.4f, %.4f]  (distance   ΓÇö lower = more similar)",
             long["P_stat"].min(), long["P_stat"].max())
    log.info("  P_name range : [%.4f, %.4f]  (similarity ΓÇö higher = more similar)",
             long["P_name"].min(), long["P_name"].max())
    log.info("  P_sem  range : [%.4f, %.4f]  (similarity ΓÇö higher = more similar)",
             long["P_sem"].min(),  long["P_sem"].max())
    log.info("  Total pairs  : %d", len(long))
    return long




# =============================================================================
# LOAD WEIGHTS from derived_weights.csv
# =============================================================================

def load_weights(input_dir: Path) -> tuple[float, float, float]:
    """
    Read variance-based weights from derived_weights.csv (produced by derive_weights.py).
    Falls back to Config defaults if the file is not found.

    CSV columns used: w1_stat_rounded, w2_name_rounded, w3_sem_rounded
    """
    weights_path = input_dir / Config.WEIGHTS_FILE
    if not weights_path.exists():
        log.warning(
            "derived_weights.csv not found at %s ΓÇö using fallback weights "
            "w1=%.2f w2=%.2f w3=%.2f", weights_path, Config.W1, Config.W2, Config.W3
        )
        return Config.W1, Config.W2, Config.W3

    df = pd.read_csv(weights_path)
    row = df.iloc[0]
    w1 = float(row["w1_stat_rounded"])
    w2 = float(row["w2_name_rounded"])
    w3 = float(row["w3_sem_rounded"])

    if abs(w1 + w2 + w3 - 1.0) > 1e-4:
        raise ValueError(
            f"Weights in {weights_path} do not sum to 1.0: "
            f"w1={w1} + w2={w2} + w3={w3} = {w1+w2+w3:.6f}"
        )

    log.info("Weights loaded from %s: w1=%.4f  w2=%.4f  w3=%.4f  (sum=%.4f)",
             Config.WEIGHTS_FILE, w1, w2, w3, w1+w2+w3)
    return w1, w2, w3

# =============================================================================
# STEP 3.4.2 ΓÇö WEIGHTED LINEAR COMBINATION  (replaces RF)
# =============================================================================

def compute_sim_attr(long: pd.DataFrame,
                     w1: float, w2: float, w3: float) -> tuple[pd.DataFrame, float]:
    """
    Step 3.4.2 ΓÇö Weighted linear combination (replaces RF from Running Example ┬º3.4.2).

    Formula:
      Sim_attr(Ai, Aj) = w1*(1 - P_stat_norm) + w2*P_name + w3*P_sem

    Components:
      (1 - P_stat_norm)  ΓÇö statistical similarity Γêê [0,1]
                           P_stat is a DISTANCE so we invert it.
                           P_stat_norm = P_stat / P_stat_max  (global max)

      P_name             ΓÇö name similarity Γêê [0,1]
                           already a similarity, used directly.

      P_sem              ΓÇö semantic similarity Γêê [0,1]
                           already a similarity, used directly.

    Weights: w1 + w2 + w3 = 1.0
      default: w1=0.4  w2=0.3  w3=0.3

    Running Example verification:
      x_ij = [P_stat=0.20, P_name=0.43, P_sem=0.83]
      P_stat_max = 3.0175
      Sim_attr = 0.4*(1 - 0.20/3.0175) + 0.3*0.43 + 0.3*0.83
               = 0.4*0.9337 + 0.129 + 0.249
               = 0.3735 + 0.129 + 0.249
               = 0.7515  ΓåÆ  above theta_A=0.75 ΓåÆ edge added  Γ£ô
    """
    assert abs(w1 + w2 + w3 - 1.0) < 1e-9,         f"Weights must sum to 1.0, got {w1+w2+w3:.6f}"

    long = long.copy()

    p_stat_max = long["P_stat"].max()
    long["P_stat_norm"] = long["P_stat"] / p_stat_max

    long["Sim_attr"] = (
        w1 * (1.0 - long["P_stat_norm"]) +
        w2 * long["P_name"] +
        w3 * long["P_sem"]
    ).round(6)

    log.info("  P_stat_max (global normaliser) = %.4f", p_stat_max)
    log.info("  Weights: w1(stat)=%.2f  w2(name)=%.2f  w3(sem)=%.2f", w1, w2, w3)
    log.info("  Sim_attr range : [%.4f, %.4f]  mean=%.4f  std=%.4f",
             long["Sim_attr"].min(), long["Sim_attr"].max(),
             long["Sim_attr"].mean(), long["Sim_attr"].std())

    # Running Example spot-check
    re_sim = w1*(1 - 0.20/p_stat_max) + w2*0.43 + w3*0.83
    log.info("  Running Example check: x_ij=[0.20, 0.43, 0.83] ΓåÆ Sim_attr=%.4f"
             "  (> 0.75: %s)", re_sim, re_sim > 0.75)

    return long, p_stat_max


# =============================================================================
# STEP 3.4.3 ΓÇö Sim_attr DISTRIBUTION
# =============================================================================

def describe_sim_attr(long: pd.DataFrame, theta_A: float) -> None:
    """
    Step 3.4.3 ΓÇö Running Example:
      Sim_attr applied to all pairs.
      Example: Sim_attr = 0.80 ΓåÆ 80% confidence they are related.

    Shows the full distribution so the threshold choice can be verified.
    """
    log.info("Step 3.4.3 ΓÇö Sim_attr distribution across all %d pairs:", len(long))
    bins   = [0, 0.3, 0.5, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 1.01]
    labels = ["<0.30","0.30-0.50","0.50-0.55","0.55-0.60",
              "0.60-0.65","0.65-0.70","0.70-0.75","0.75-0.80",">0.80"]
    long["_bin"] = pd.cut(long["Sim_attr"], bins=bins, labels=labels, right=False)
    for lbl, cnt in long["_bin"].value_counts().sort_index().items():
        bar = "#" * (cnt // 25)
        log.info("  %s : %4d  %s", lbl, cnt, bar)
    log.info("  ΓåÆ pairs above theta_A=%.2f : %d",
             theta_A, (long["Sim_attr"] > theta_A).sum())
    long.drop(columns=["_bin"], inplace=True)

    log.info("  Top-10 most similar pairs:")
    for _, r in long.nlargest(10, "Sim_attr").iterrows():
        log.info("    %-38s %-38s Sim=%.4f", r["col_i"], r["col_j"], r["Sim_attr"])

    log.info("  Top-5 most dissimilar pairs:")
    for _, r in long.nsmallest(5, "Sim_attr").iterrows():
        log.info("    %-38s %-38s Sim=%.4f", r["col_i"], r["col_j"], r["Sim_attr"])


# =============================================================================
# STEP 3.5 ΓÇö BUILD WEIGHTED COLUMN GRAPH G_A
# =============================================================================

def build_column_graph(long: pd.DataFrame, theta_A: float) -> pd.DataFrame:
    """
    Step 3.5.1 ΓÇö threshold theta_A (Running Example):
      0.70 ΓåÆ moderate  |  0.75 ΓåÆ paper default  |  0.80 ΓåÆ high confidence
      (adjusted to 0.60 for weighted combination ΓÇö see Config note)

    Step 3.5.2 ΓÇö decision rule (Running Example):
      If Sim_attr(Ai, Aj) > theta_A  ΓåÆ  add edge  w(Ai, Aj) = Sim_attr(Ai, Aj)
      Else                            ΓåÆ  do nothing

    G_A = (A, E_A):
      Nodes   = all columns
      Edges   = {(Ai, Aj) | Sim_attr(Ai, Aj) > theta_A}
      Weights = Sim_attr values
    """
    log.info("Step 3.5 ΓÇö Building G_A  (theta_A = %.2f)", theta_A)

    edges = long[long["Sim_attr"] > theta_A].copy()
    # Pseudocode line 24: Sim_attr kept as explicit column name
    # Pseudocode line 28: edge weight = Sim_attr
    edges["weight"] = edges["Sim_attr"]
    keep  = ["col_i", "col_j", "table_i", "table_j",
             "P_stat", "P_stat_norm", "P_name", "P_sem", "Sim_attr", "weight"]
    edges = edges[keep].sort_values("Sim_attr", ascending=False).reset_index(drop=True)

    n = len(long)
    e = len(edges)
    log.info("  Total pairs  : %d", n)
    log.info("  Edges in G_A : %d  (Sim_attr > %.2f)", e, theta_A)
    log.info("  Pruned       : %d  (%.1f%%)", n-e, 100*(n-e)/n)
    log.info("  Weight range : [%.4f, %.4f]  mean=%.4f",
             edges["weight"].min(), edges["weight"].max(), edges["weight"].mean())

    # Weight distribution among edges
    bins   = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 1.01]
    labels = ["0.55-0.60","0.60-0.65","0.65-0.70","0.70-0.75",
              "0.75-0.80","0.80-0.85",">0.85"]
    edges["_wbin"] = pd.cut(edges["weight"], bins=bins, labels=labels, right=False)
    log.info("  Edge weight distribution:")
    for lbl, cnt in edges["_wbin"].value_counts().sort_index().items():
        log.info("    %s : %d", lbl, cnt)
    edges.drop(columns=["_wbin"], inplace=True)

    log.info("  Top-15 edges:")
    for _, r in edges.head(15).iterrows():
        log.info("    %-38s %-38s w=%.4f", r["col_i"], r["col_j"], r["weight"])

    return edges


# =============================================================================
# HELPERS
# =============================================================================

def build_sim_attr_matrix(long: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    labels = sorted(set(long["col_i"].tolist() + long["col_j"].tolist()))
    idx    = {lbl: i for i, lbl in enumerate(labels)}
    N      = len(labels)
    M      = np.zeros((N, N))
    np.fill_diagonal(M, 1.0)
    for _, r in long.iterrows():
        i, j = idx[r["col_i"]], idx[r["col_j"]]
        M[i, j] = M[j, i] = r["Sim_attr"]
    return M, labels


def save_report(long: pd.DataFrame, edges: pd.DataFrame,
                w1: float, w2: float, w3: float,
                p_stat_max: float, theta_A: float, path: Path) -> None:
    re_sim = w1*(1 - 0.20/p_stat_max) + w2*0.43 + w3*0.83
    lines = [
        "=" * 66,
        "CCM Step 3.4 ΓÇö Sim_attr Report",
        "=" * 66,
        "",
        "Step 3.4.2 formula (replaces RF ΓÇö Running Example deviation):",
        "  Sim_attr(Ai,Aj) = w1*(1-P_stat_norm) + w2*P_name + w3*P_sem",
        f"  P_stat_norm     = P_stat / {p_stat_max:.4f}  (global max)",
        f"  Weights         : w1={w1}  w2={w2}  w3={w3}  (sum={w1+w2+w3:.1f})",
        "",
        "Running Example verification:",
        "  x_ij = [P_stat=0.20, P_name=0.43, P_sem=0.83]",
        f"  Sim_attr = {w1}*(1-0.20/{p_stat_max:.4f}) + {w2}*0.43 + {w3}*0.83",
        f"           = {re_sim:.4f}  "
        f"({'> theta ΓåÆ edge added' if re_sim > theta_A else '< theta ΓåÆ pruned'})",
        "",
        f"Pairs total    : {len(long)}",
        f"Sim_attr range : [{long['Sim_attr'].min():.4f}, {long['Sim_attr'].max():.4f}]",
        f"Sim_attr mean  : {long['Sim_attr'].mean():.4f}",
        f"Sim_attr std   : {long['Sim_attr'].std():.4f}",
        "",
        f"Step 3.5  theta_A = {theta_A}",
        f"Edges in G_A     = {len(edges)}",
        f"Pruned pairs     = {len(long)-len(edges)}  "
        f"({100*(len(long)-len(edges))/len(long):.1f}%)",
        "=" * 66,
    ]
    report = "\n".join(lines)
    path.write_text(report, encoding="utf-8")
    log.info("Saved %s", path.name)
    log.info("\n%s", report)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CCM Steps 3.4 + 3.5 ΓÇö weighted Sim_attr + column graph G_A")
    parser.add_argument("--input-dir",  default=str(Config.INPUT_DIR),
                        help="Directory containing step3_P_stat/name/sem.csv and derived_weights.csv")
    parser.add_argument("--out-dir",    default=str(Config.OUT_DIR))
    parser.add_argument("--theta",      type=float, default=Config.THETA_A,
                        help="Edge threshold theta_A (default 0.60)")
    parser.add_argument("--w1",         type=float, default=None,
                        help="Override w1 (default: read from derived_weights.csv)")
    parser.add_argument("--w2",         type=float, default=None,
                        help="Override w2 (default: read from derived_weights.csv)")
    parser.add_argument("--w3",         type=float, default=None,
                        help="Override w3 (default: read from derived_weights.csv)")
    parser.add_argument("--dataset_dir", default=None,
                   help="Dataset working directory containing schema.json, knowledge.docx, "
                        "csv/ and ccm_output/. When run_pipeline.py is in the parent folder, "
                        "pass the dataset subfolder name (e.g. --dataset_dir Chinook). "
                        "Defaults to the current working directory.")
    args = parser.parse_args()

    # ΓöÇΓöÇ Dataset directory ΓÇö chdir so all relative paths resolve correctly ΓöÇΓöÇΓöÇΓöÇ
    if args.dataset_dir is not None:
        import os as _os
        _os.chdir(args.dataset_dir)

    Config.INPUT_DIR = Path(args.input_dir)
    Config.OUT_DIR   = Path(args.out_dir)
    Config.THETA_A   = args.theta
    Config.OUT_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    log.info("CCM Pipeline ΓÇö Steps 3.4 + 3.5")

    # Step 3.4.1 ΓÇö build x_ij = [P_stat, P_name, P_sem] from the three matrix CSVs
    long = load_features(Config.INPUT_DIR)

    # Load weights from derived_weights.csv (or use CLI overrides)
    w1, w2, w3 = load_weights(Config.INPUT_DIR)
    if args.w1 is not None: w1 = args.w1
    if args.w2 is not None: w2 = args.w2
    if args.w3 is not None: w3 = args.w3
    if abs(w1 + w2 + w3 - 1.0) > 1e-4:
        raise ValueError(f"w1+w2+w3 must equal 1.0, got {w1+w2+w3:.6f}")

    log.info("  theta_A=%.2f  w1=%.4f  w2=%.4f  w3=%.4f", Config.THETA_A, w1, w2, w3)

    # Step 3.4.2 ΓÇö compute Sim_attr via weighted combination
    log.info("Step 3.4.2 ΓÇö Computing Sim_attr (weighted linear combination)")
    long, p_stat_max = compute_sim_attr(long, w1, w2, w3)

    # Step 3.4.3 ΓÇö describe distribution
    describe_sim_attr(long, Config.THETA_A)

    # Save long CSV: all pairs with Sim_attr (pseudocode line 24)
    long_out_cols = ["col_i", "col_j", "table_i", "table_j",
                     "P_stat", "P_stat_norm", "P_name", "P_sem", "Sim_attr"]
    long[long_out_cols].to_csv(
        Config.OUT_DIR / Config.LONG_OUT_FILE, index=False, float_format="%.6f")
    log.info("Saved %s  (%d pairs, all with Sim_attr)",
             Config.LONG_OUT_FILE, len(long))

    # Save 130x130 Sim_attr matrix
    M, labels = build_sim_attr_matrix(long)
    pd.DataFrame(M, index=labels, columns=labels).to_csv(
        Config.OUT_DIR / Config.SIM_ATTR_FILE, float_format="%.6f")
    log.info("Saved %s  (%dx%d)", Config.SIM_ATTR_FILE, len(labels), len(labels))

    # Step 3.5 ΓÇö build G_A
    edges = build_column_graph(long, Config.THETA_A)
    edges.to_csv(Config.OUT_DIR / Config.EDGES_FILE, index=False)
    log.info("Saved %s  (%d edges)", Config.EDGES_FILE, len(edges))

    # Report
    save_report(long, edges, w1, w2, w3,
                p_stat_max, Config.THETA_A,
                Config.OUT_DIR / Config.REPORT_FILE)

    log.info("")
    log.info("=" * 66)
    log.info("DONE  (%.1fs)  |  G_A: %d nodes  %d edges  theta=%.2f",
             time.time()-t0, len(labels), len(edges), Config.THETA_A)
    log.info("=" * 66)
    log.info("Next: Step 4 ΓÇö Table-Level Similarity (greedy matching + G_T)")


if __name__ == "__main__":
    main()

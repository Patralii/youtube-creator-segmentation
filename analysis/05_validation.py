"""
05_validation.py — Validating the Revenue Gap Finding
======================================================
Purpose:
    Confirm the $2M gap is a structural pattern — not a statistical artefact
    driven by outliers, an unstable K choice, or a few lucky creators.

Three independent checks:
    1. Outlier trim    — does the gap survive removing the top 5% by views?
    2. Broad-base      — what % of Niche Specialists individually show a gap?
    3. Cluster stability — how much do assignments vary across 20 random seeds?

Why three checks?
    A single validation can fail in different ways. These three address the
    three main ways the finding could be wrong:
        (a) Viral-fluke inflation  → outlier trim
        (b) Average masking a few whales → broad-base check
        (c) Algorithm-dependent clusters → seed stability

Run after: 03_segmentation.py
Outputs:   outputs/validation/*.png
"""

import os, sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kmeans_scratch import kmeans, silhouette_score_manual

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "validation")
os.makedirs(OUT_DIR, exist_ok=True)

BG, SURFACE, TEXT, DIM = "#0f0f0f","#181818","#f1f1f1","#aaaaaa"
RED, GREEN, YELLOW, BLUE = "#ff0000","#2fd180","#ffd166","#3ea6ff"

plt.rcParams.update({
    "figure.facecolor":BG,"axes.facecolor":SURFACE,"text.color":TEXT,
    "axes.labelcolor":DIM,"xtick.color":DIM,"ytick.color":DIM,
    "grid.color":"#303030","font.family":"monospace",
})

FEATURE_COLS = [
    "avg_retention_rate","avg_ctr","upload_freq_per_month",
    "avg_video_length_mins","len_consistency_score",
]


def load():
    path = os.path.join(DATA_DIR, "creator_segments.csv")
    if not os.path.exists(path):
        raise FileNotFoundError("creator_segments.csv not found — run 03_segmentation.py first.")
    return pd.read_csv(path)


def get_parity_rpm(df):
    return df[df["archetype"] == "Subscriber Giants"]["rpm"].mean()


def compute_niche_gap(df, parity_rpm):
    niche = df[df["archetype"] == "High-Retention Niche Specialists"].copy()
    niche["revenue_at_parity"] = niche["views_90d"] * parity_rpm / 1000
    niche["revenue_gap"] = (niche["revenue_at_parity"] - niche["revenue_90d"]).clip(lower=0)
    return niche


def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


# ══════════════════════════════════════════════════════════════════
# Check 1: Outlier trim
# ══════════════════════════════════════════════════════════════════
def check_outlier_trim(df):
    """
    Remove the top 5% of Niche Specialists by 90-day views, then recompute gap.

    Why top 5% by views?
        A creator who had one video go viral during the 90-day window will have
        inflated views but the viral performance isn't characteristic of their
        archetype. Trimming them tests whether the gap is driven by these events.

    Pass criterion: ≥85% of the original gap survives the trim.
    """
    section("Check 1: Outlier Trim (top 5% by views removed)")
    parity_rpm = get_parity_rpm(df)
    niche_full = compute_niche_gap(df, parity_rpm)
    gap_full   = niche_full["revenue_gap"].sum()
    n_full     = len(niche_full)

    cutoff = niche_full["views_90d"].quantile(0.95)
    trimmed = niche_full[niche_full["views_90d"] <= cutoff].copy()
    trimmed["revenue_at_parity"] = trimmed["views_90d"] * parity_rpm / 1000
    trimmed["revenue_gap"] = (trimmed["revenue_at_parity"] - trimmed["revenue_90d"]).clip(lower=0)
    gap_trimmed = trimmed["revenue_gap"].sum()

    pct_retained = gap_trimmed / gap_full * 100
    n_removed    = n_full - len(trimmed)

    print(f"  Creators removed (top 5% view-spike): {n_removed}")
    print(f"  Gap before trim : ${gap_full:>12,.0f}")
    print(f"  Gap after trim  : ${gap_trimmed:>12,.0f}")
    print(f"  Gap retained    : {pct_retained:.1f}%")
    print(f"  Verdict (≥85%)  : {'PASS ✓' if pct_retained >= 85 else 'FAIL ✗'}")

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(
        [f"All {n_full} creators", f"Outliers removed\n({len(trimmed)})"],
        [gap_full, gap_trimmed],
        color=[GREEN, BLUE], width=0.5
    )
    ax.bar_label(bars, fmt="$%.0f", padding=6, color=DIM, fontsize=10)
    ax.set_ylabel("Total revenue gap (USD)")
    ax.set_title("Check 1: Does the Gap Survive Outlier Removal?", color=TEXT)
    ax.text(0.97, 0.95, f"{pct_retained:.1f}% retained",
            transform=ax.transAxes, ha="right", va="top", color=YELLOW,
            fontsize=12, fontweight="bold")
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"01_outlier_trim.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 01_outlier_trim.png")
    return pct_retained


# ══════════════════════════════════════════════════════════════════
# Check 2: Broad-base
# ══════════════════════════════════════════════════════════════════
def check_broad_base(df):
    """
    What % of individual Niche Specialist creators have a positive gap?

    If 89%+ of creators individually show a positive gap, the problem is
    broad-based — a retention-indexed RPM policy will help the majority,
    not just a handful of high-earners pulling up an average.

    Pass criterion: ≥80% of creators have individual gap > $0.
    """
    section("Check 2: Broad-Base (per-creator positive-gap rate)")
    parity_rpm = get_parity_rpm(df)
    niche = compute_niche_gap(df, parity_rpm)
    pct_positive = (niche["revenue_gap"] > 0).mean() * 100

    print(f"  Creators with gap > $0 : {pct_positive:.1f}%")
    print(f"  Creators with gap = $0 : {100-pct_positive:.1f}%")
    print(f"  Verdict (≥80%)         : {'PASS ✓' if pct_positive >= 80 else 'FAIL ✗'}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(niche["revenue_gap"], bins=30, color=BLUE, alpha=0.85, edgecolor="none")
    ax.axvline(0, color=RED, lw=1.5, label="Gap = $0")
    ax.axvline(niche["revenue_gap"].mean(), color=YELLOW, ls="--", lw=1.5,
               label=f"Mean: ${niche['revenue_gap'].mean():,.0f}")
    ax.set_xlabel("Per-creator 90d revenue gap (USD)")
    ax.set_ylabel("Number of creators")
    ax.set_title("Check 2: Is the Gap Broad-Based Across Creators?", color=TEXT)
    ax.legend(fontsize=9, framealpha=0.3)
    ax.text(0.97, 0.95, f"{pct_positive:.0f}% of creators\nhave gap > $0",
            transform=ax.transAxes, ha="right", va="top", color=GREEN, fontsize=10)
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"02_broad_base.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 02_broad_base.png")
    return pct_positive


# ══════════════════════════════════════════════════════════════════
# Check 3: Cluster stability
# ══════════════════════════════════════════════════════════════════
def check_cluster_stability():
    """
    Run KMeans 20 times with different seeds. Measure assignment consistency.

    If clusters are real (not arbitrary), they should be recovered regardless
    of starting point. High consistency means the solution is data-driven,
    not algorithm-dependent.

    Metric: % of creators assigned to the same cluster in ≥18 of 20 runs.
    Pass criterion: ≥85% consistency.
    """
    section("Check 3: Cluster Stability (20 random seeds)")

    # Reload raw features for a clean clustering run
    df = pd.read_csv(os.path.join(DATA_DIR, "creator_segments.csv"))
    # Reconstruct len_consistency_score if needed
    creators_raw = pd.read_csv(os.path.join(DATA_DIR, "creators_clean.csv"))
    if "len_consistency_score" not in creators_raw.columns:
        creators_raw["len_consistency_score"] = (
            100 - (creators_raw["avg_video_len_std"] /
                   creators_raw["avg_video_len_std"].max() * 100)
        ).clip(0, 100)

    X = creators_raw[FEATURE_COLS].values.astype(float)
    means = X.mean(axis=0); stds = X.std(axis=0); stds[stds==0] = 1.0
    X_scaled = (X - means) / stds

    all_labels = []
    inertias   = []
    for seed in range(20):
        labels, _, inertia, _ = kmeans(X_scaled, K=5, n_init=1,
                                        max_iter=200, random_state=seed)
        all_labels.append(labels)
        inertias.append(inertia)
    all_labels = np.array(all_labels)   # (20, n)

    # For each creator, count how many runs agree on the most common label
    consistent = 0
    for i in range(X_scaled.shape[0]):
        run_vals = all_labels[:, i]
        vals, counts = np.unique(run_vals, return_counts=True)
        if counts.max() >= 18:
            consistent += 1
    pct_stable = consistent / X_scaled.shape[0] * 100

    inertia_cv = np.std(inertias) / np.mean(inertias) * 100
    print(f"  Creators stably assigned (≥18/20 runs): {consistent:,} ({pct_stable:.1f}%)")
    print(f"  Inertia CV across 20 seeds: {inertia_cv:.2f}%")
    print(f"  Verdict (≥85%): {'PASS ✓' if pct_stable >= 85 else 'FAIL ✗'}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(1,21), inertias, "o-", color=BLUE, lw=1.5, markersize=5)
    ax.axhline(np.mean(inertias), color=YELLOW, ls="--",
               label=f"Mean inertia: {np.mean(inertias):.0f}")
    ax.set_xlabel("Random seed (run number)")
    ax.set_ylabel("Final inertia")
    ax.set_title("Check 3: Inertia Across 20 Random Seeds", color=TEXT)
    ax.legend(fontsize=9, framealpha=0.3)
    ax.text(0.97, 0.06, f"Assignment stability: {pct_stable:.1f}%",
            transform=ax.transAxes, ha="right", va="bottom", color=GREEN, fontsize=10)
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"03_seed_stability.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 03_seed_stability.png")
    return pct_stable


# ══════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════
def summarise(trim, broadbase, stability):
    section("VALIDATION SUMMARY")
    checks = [
        ("Outlier trim survives (≥85%)",          trim,       85),
        ("Broad-base positive-gap rate (≥80%)",   broadbase,  80),
        ("Cluster assignment stability (≥85%)",   stability,  85),
    ]
    for name, val, threshold in checks:
        status = "PASS ✓" if val >= threshold else "FAIL ✗"
        print(f"  {name:<42s}  {val:5.1f}%  {status}")

    all_pass = all(v >= t for _, v, t in checks)
    print(f"\n  Conclusion: {'All checks passed — the $2M gap is a structural finding.' if all_pass else 'One or more checks failed — review before presenting.'}")


if __name__ == "__main__":
    df         = load()
    trim       = check_outlier_trim(df)
    broadbase  = check_broad_base(df)
    stability  = check_cluster_stability()
    summarise(trim, broadbase, stability)
    print("\nValidation complete.")

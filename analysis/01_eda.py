"""
01_eda.py — Exploratory Data Analysis
=======================================
Purpose:
    Understand the shape of the data before any modelling — distributions,
    outliers, correlations, and the surface-level subscriber-tier view that
    forms Act II of the narrative.

Why EDA first?
    EDA before clustering prevents modelling choices from being driven by what
    we "want" to find. We confirm the subscriber-tier assumption looks correct
    on the surface, then ask whether a behavioral lens reveals something else.

Run after: 00_data_cleaning.py
Outputs:   outputs/eda/*.png
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "eda")
os.makedirs(OUT_DIR, exist_ok=True)

# ── YouTube Studio dark palette ───────────────────────────────────────────────
BG      = "#0f0f0f"
SURFACE = "#181818"
TEXT    = "#f1f1f1"
DIM     = "#aaaaaa"
RED     = "#ff0000"
BLUE    = "#3ea6ff"
GREEN   = "#2fd180"
YELLOW  = "#ffd166"
PURPLE  = "#c084fc"
PALETTE = [RED, BLUE, GREEN, YELLOW, PURPLE, "#fb923c"]

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": SURFACE,
    "axes.edgecolor": "#303030", "axes.labelcolor": DIM,
    "xtick.color": DIM, "ytick.color": DIM, "text.color": TEXT,
    "grid.color": "#303030", "grid.alpha": 0.4, "font.family": "monospace",
})

TIER_ORDER = ["Mega (500K+)", "Large (100K-500K)", "Mid (10K-100K)",
              "Small (1K-10K)", "Micro (<1K)"]


def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def load():
    """Load clean creators and videos. If clean files missing, raise a clear error."""
    c_path = os.path.join(DATA_DIR, "creators_clean.csv")
    v_path = os.path.join(DATA_DIR, "videos_clean.csv")
    if not os.path.exists(c_path):
        raise FileNotFoundError("creators_clean.csv not found — run 00_data_cleaning.py first.")
    creators = pd.read_csv(c_path)
    videos   = pd.read_csv(v_path, parse_dates=["publish_date"])
    return creators, videos


# ══════════════════════════════════════════════════════════════════
# 1. Basic shape
# ══════════════════════════════════════════════════════════════════
def eda_basics(creators, videos):
    """Sanity-check dimensions and confirm no residual nulls after cleaning."""
    section("1. Dataset Overview")
    print(f"Creators : {len(creators):>8,} rows × {creators.shape[1]} cols")
    print(f"Videos   : {len(videos):>8,} rows × {videos.shape[1]} cols")
    nulls = creators.isnull().sum()
    nulls = nulls[nulls > 0]
    print("\nCreators — residual nulls:", "None" if len(nulls)==0 else nulls.to_string())


# ══════════════════════════════════════════════════════════════════
# 2. Subscriber-tier revenue — Acts I & II (the surface view)
# ══════════════════════════════════════════════════════════════════
def eda_tier_revenue(creators):
    """
    Reproduce the analysis a subscriber-tier dashboard would show.
    This is Act II: Mega-tier creators DO dominate revenue.
    The goal here is not to disprove the assumption — it's to show it is
    *incomplete*. That gap is what motivates behavioral clustering.
    """
    section("2. Revenue by Subscriber Tier  (The Surface View)")

    tier_stats = (
        creators.groupby("subscriber_tier", observed=True)
        .agg(n_creators=("creator_id","count"), avg_rev=("revenue_90d","mean"),
             total_rev=("revenue_90d","sum"))
        .reindex(TIER_ORDER)
        .assign(pct_creators=lambda d: d.n_creators/d.n_creators.sum()*100,
                pct_revenue=lambda d: d.total_rev/d.total_rev.sum()*100)
    )
    print(tier_stats.round(2).to_string())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Subscriber Tier: Creator Share vs Revenue Share", color=TEXT, fontsize=13)
    cols = PALETTE[:5]

    b1 = ax1.barh(tier_stats.index[::-1], tier_stats["pct_creators"][::-1], color=cols[::-1], height=0.6)
    ax1.set_title("% of Creator Base", color=TEXT)
    ax1.set_xlabel("% of all creators", color=DIM)
    ax1.bar_label(b1, fmt="%.1f%%", padding=4, color=DIM, fontsize=9)

    b2 = ax2.barh(tier_stats.index[::-1], tier_stats["pct_revenue"][::-1], color=cols[::-1], height=0.6)
    ax2.set_title("% of Platform Revenue", color=TEXT)
    ax2.set_xlabel("% of 90d revenue", color=DIM)
    ax2.bar_label(b2, fmt="%.1f%%", padding=4, color=DIM, fontsize=9)

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "01_tier_revenue.png"), dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 01_tier_revenue.png")


# ══════════════════════════════════════════════════════════════════
# 3. Clustering feature distributions
# ══════════════════════════════════════════════════════════════════
def eda_distributions(creators):
    """
    Inspect the shape of each feature before clustering.
    Why: KMeans assumes roughly spherical clusters (sensitive to scale and skew).
    This tells us whether any feature needs log-transformation before standardising.
    """
    section("3. Clustering Feature Distributions")
    metrics = {
        "avg_retention_rate":    "Avg Retention Rate (%)",
        "avg_ctr":               "Avg CTR (%)",
        "upload_freq_per_month": "Upload Frequency / Month",
        "avg_video_length_mins": "Avg Video Length (mins)",
        "rpm":                   "RPM (USD per 1,000 views)",
    }
    fig, axes = plt.subplots(1, 5, figsize=(18, 4))
    fig.suptitle("Distribution of Behavioral Clustering Features", color=TEXT, fontsize=12)

    for ax, (col, label) in zip(axes, metrics.items()):
        ax.hist(creators[col].dropna(), bins=40, color=BLUE, alpha=0.8, edgecolor="none")
        ax.set_title(label, color=TEXT, fontsize=8.5)
        med = creators[col].median()
        ax.axvline(med, color=RED, linestyle="--", linewidth=1.2, label=f"Med: {med:.1f}")
        ax.legend(fontsize=7)
        print(f"  {col:<32s} skew={creators[col].skew():.3f}  median={med:.2f}")

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "02_distributions.png"), dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 02_distributions.png")


# ══════════════════════════════════════════════════════════════════
# 4. Correlation — does scale proxy quality?
# ══════════════════════════════════════════════════════════════════
def eda_correlation(creators):
    """
    If subscriber count were strongly correlated with retention, the existing
    tier-based approach might accidentally surface the right creators anyway.
    A weak correlation is the analytical justification for behavior-based
    clustering being *necessary*, not just interesting.
    """
    section("4. Correlation: Is Scale a Proxy for Quality?")
    cols = ["subscriber_count","avg_retention_rate","avg_ctr",
            "upload_freq_per_month","avg_video_length_mins","rpm","revenue_90d"]
    corr = creators[cols].corr().round(3)
    print(corr.to_string())
    r = corr.loc["subscriber_count","avg_retention_rate"]
    print(f"\n→ subscriber_count ↔ avg_retention_rate  r = {r:.3f}")
    if abs(r) < 0.3:
        print("  Weak — subscriber count is NOT a reliable proxy for retention quality.")


# ══════════════════════════════════════════════════════════════════
# 5. Retention vs RPM — the central tension, pre-clustering
# ══════════════════════════════════════════════════════════════════
def eda_retention_rpm(creators):
    """
    Plot the scatter before any clustering to show the divergence exists
    in the raw data — we are not manufacturing it from clustering output.
    The top-left quadrant (high retention, low RPM) is where Niche Specialists
    will be found, but at this stage we just observe it exists.
    """
    section("5. Retention vs RPM  (Pre-Clustering)")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(creators["avg_retention_rate"], creators["rpm"],
               alpha=0.22, s=8, color=BLUE)
    ax.axvspan(48, 80, alpha=0.05, color=GREEN, label="High-retention zone (≥48%)")
    ax.axhspan(0, 2.0, alpha=0.05, color=RED,   label="Low-RPM zone (<$2.00)")
    r = creators["avg_retention_rate"].corr(creators["rpm"])
    ax.set_title(f"Retention vs RPM  (r = {r:.3f})", color=TEXT, fontsize=12, pad=12)
    ax.set_xlabel("Avg Retention Rate (%)", color=DIM)
    ax.set_ylabel("RPM (USD / 1,000 views)", color=DIM)
    ax.legend(loc="upper right", fontsize=9)
    ax.text(0.02, 0.97, "Top-left = high retention, low RPM\n→ structurally underpaid attention",
            transform=ax.transAxes, color=YELLOW, fontsize=9, va="top")
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "03_retention_vs_rpm.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  Saved: 03_retention_vs_rpm.png  (r = {r:.3f})")


# ══════════════════════════════════════════════════════════════════
# 6. Mid-tier internal variance — why one label hides everything
# ══════════════════════════════════════════════════════════════════
def eda_mid_tier_variance(creators):
    """
    The Mid tier (10K-100K) contains 45%+ of creators but is treated as one group.
    This plot shows the retention distribution *within* that tier is extremely wide —
    direct evidence that a single tier label is masking important heterogeneity.
    """
    section("6. Mid-Tier Internal Variance")
    mid = creators[creators["subscriber_tier"] == "Mid (10K-100K)"]
    non_mid = creators[creators["subscriber_tier"] != "Mid (10K-100K)"]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(non_mid["avg_retention_rate"].dropna(), bins=40, alpha=0.45,
            color=DIM, label="All other tiers", edgecolor="none")
    ax.hist(mid["avg_retention_rate"].dropna(), bins=40, alpha=0.75,
            color=YELLOW, label=f"Mid tier (10K–100K)  n={len(mid):,}", edgecolor="none")
    ax.set_xlabel("Avg Retention Rate (%)", color=DIM)
    ax.set_ylabel("Creator count", color=DIM)
    ax.set_title("Retention Distribution Inside the Mid Tier\n(Why one label hides everything)",
                 color=TEXT, fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.2)
    std = mid["avg_retention_rate"].std()
    ax.text(0.97, 0.95, f"Mid tier retention std: {std:.1f}%\n→ enormous internal variation",
            transform=ax.transAxes, ha="right", va="top", color=YELLOW, fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "04_mid_tier_variance.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  Mid-tier retention std = {std:.2f}%")
    print("  Saved: 04_mid_tier_variance.png")


if __name__ == "__main__":
    creators, videos = load()
    eda_basics(creators, videos)
    eda_tier_revenue(creators)
    eda_distributions(creators)
    eda_correlation(creators)
    eda_retention_rpm(creators)
    eda_mid_tier_variance(creators)
    print(f"\nAll EDA plots saved to: {OUT_DIR}")

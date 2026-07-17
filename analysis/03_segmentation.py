"""
03_segmentation.py — Behavioral Segmentation (Main Clustering Pipeline)
========================================================================
Purpose:
    Cluster 4,000 creators by behavioral features — deliberately excluding
    subscriber count — to surface natural creator archetypes.

Why exclude subscriber count from features?
    It is the variable whose validity as a proxy we are testing. Including it
    would bias clusters toward subscriber tiers, making it impossible to find
    archetypes that cut across tiers.

Five clustering features (all Z-score standardised before clustering):
    1. avg_retention_rate     — how well content holds attention
    2. avg_ctr                — how compelling thumbnails/titles are
    3. upload_freq_per_month  — consistency of posting cadence
    4. avg_video_length_mins  — content format signal
    5. len_consistency_score  — whether creator sticks to one format length

Run after: 00_data_cleaning.py, (01_eda.py optional)
Outputs:
    data/creator_segments.csv      — creators with cluster labels + gap columns
    outputs/segmentation/*.png     — elbow, scatter, radar, profiles
"""

import os, sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kmeans_scratch import kmeans, elbow_and_silhouette, silhouette_score_manual

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "segmentation")
os.makedirs(OUT_DIR, exist_ok=True)

BG, SURFACE, TEXT, DIM = "#0f0f0f", "#181818", "#f1f1f1", "#aaaaaa"
ARCHETYPE_COLORS = {
    "Subscriber Giants":                "#3ea6ff",
    "High-Retention Niche Specialists": "#2fd180",
    "Viral Spike Chasers":              "#ff0000",
    "Consistent Volume Builders":       "#ffd166",
    "Emerging Dabblers":                "#c084fc",
}
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": SURFACE,
    "text.color": TEXT, "axes.labelcolor": DIM,
    "xtick.color": DIM, "ytick.color": DIM,
    "grid.color": "#303030", "font.family": "monospace",
})

FEATURE_COLS = [
    "avg_retention_rate",
    "avg_ctr",
    "upload_freq_per_month",
    "avg_video_length_mins",
    "len_consistency_score",
]


# ── Load ─────────────────────────────────────────────────────────────────────
def load():
    path = os.path.join(DATA_DIR, "creators_clean.csv")
    if not os.path.exists(path):
        raise FileNotFoundError("creators_clean.csv not found — run 00_data_cleaning.py first.")
    df = pd.read_csv(path)
    # Derive len_consistency_score if missing from the CSV
    if "len_consistency_score" not in df.columns:
        df["len_consistency_score"] = (
            100 - (df["avg_video_len_std"] / df["avg_video_len_std"].max() * 100)
        ).clip(0, 100).round(1)
    return df


# ── Standardise ───────────────────────────────────────────────────────────────
def standardise(df, cols):
    """
    Z-score: x' = (x − μ) / σ

    Why: KMeans uses Euclidean distance. Features on different scales
    (retention 5–80%, upload_freq 0.5–35) would let high-range features
    dominate distance calculations. After Z-scoring, all features have
    mean≈0 and std≈1 — equal influence on cluster geometry.

    We store μ and σ to inverse-transform centroids back to real units
    for human-readable archetype profile tables.
    """
    X = df[cols].values.astype(float)
    means = X.mean(axis=0)
    stds  = X.std(axis=0)
    stds[stds == 0] = 1.0
    return (X - means) / stds, means, stds


# ── K selection ───────────────────────────────────────────────────────────────
def select_k(X_scaled):
    """
    Run K=2..8 and plot both the elbow curve (inertia) and silhouette score.
    When both methods agree on the same K, we have high confidence.
    """
    print("Running K-selection (K=2..8, 10 restarts each) ...")
    results = elbow_and_silhouette(X_scaled, k_range=range(2, 9), n_init=10)

    ks         = [r["K"] for r in results]
    inertias   = [r["inertia"] for r in results]
    silhouettes= [r["silhouette"] for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle("K Selection: Elbow Method + Silhouette Score", color=TEXT, fontsize=12)

    ax1.plot(ks, inertias, "o-", color="#3ea6ff", lw=2)
    ax1.axvline(5, color="#ff0000", ls="--", alpha=0.7, label="Selected K=5")
    ax1.set_title("Elbow (Inertia)", color=TEXT)
    ax1.set_xlabel("K")
    ax1.set_ylabel("Within-cluster SS")
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.2)

    ax2.plot(ks, silhouettes, "o-", color="#2fd180", lw=2)
    ax2.axvline(5, color="#ff0000", ls="--", alpha=0.7, label="Selected K=5")
    ax2.set_title("Silhouette Score", color=TEXT)
    ax2.set_xlabel("K")
    ax2.set_ylabel("Silhouette (higher = better)")
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "01_elbow_silhouette.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 01_elbow_silhouette.png")


# ── Final clustering ──────────────────────────────────────────────────────────
def run_clustering(X_scaled, K=5):
    """20 restarts to avoid local optima."""
    print(f"\nFinal KMeans: K={K}, 20 restarts ...")
    labels, centroids, inertia, history = kmeans(
        X_scaled, K=K, n_init=20, max_iter=300, random_state=42
    )
    sil = silhouette_score_manual(X_scaled, labels)
    print(f"  Inertia: {inertia:.2f}  |  Silhouette: {sil:.4f}")
    return labels, centroids, inertia, sil


# ── Label archetypes by centroid position ────────────────────────────────────
def label_archetypes(df, labels, centroids, means, stds):
    """
    Map cluster IDs to human-readable archetype names by inspecting centroid
    positions in real-unit space (after inverse Z-transform).

    Assignment rules:
        • Highest retention centroid  → High-Retention Niche Specialists
        • Highest CTR centroid        → Viral Spike Chasers
        • Highest upload_freq         → Consistent Volume Builders
        • Highest avg subscriber_count → Subscriber Giants (uses data, not centroid)
        • Remaining                   → Emerging Dabblers
    """
    C_real = centroids * stds + means
    centroid_df = pd.DataFrame(C_real, columns=FEATURE_COLS)
    centroid_df["cluster"] = range(len(centroids))

    df = df.copy()
    df["cluster"] = labels

    retention_king = int(centroid_df["avg_retention_rate"].idxmax())
    ctr_king       = int(centroid_df["avg_ctr"].idxmax())
    upload_king    = int(centroid_df["upload_freq_per_month"].idxmax())
    giants_cluster = int(df.groupby("cluster")["subscriber_count"].mean().idxmax())

    used = {retention_king, ctr_king, upload_king, giants_cluster}
    dabblers_cluster = next(i for i in range(len(centroids)) if i not in used)

    cluster_map = {
        giants_cluster:    "Subscriber Giants",
        retention_king:    "High-Retention Niche Specialists",
        ctr_king:          "Viral Spike Chasers",
        upload_king:       "Consistent Volume Builders",
        dabblers_cluster:  "Emerging Dabblers",
    }
    # Safety: if any collision, fill remaining with a fallback label
    for cid in range(len(centroids)):
        if cid not in cluster_map:
            cluster_map[cid] = f"Cluster_{cid}"

    df["archetype"] = df["cluster"].map(cluster_map)
    return df, centroid_df, cluster_map


# ── Visualisations ────────────────────────────────────────────────────────────
def plot_scatter(df):
    """Retention vs CTR scatter coloured by archetype — the key visual."""
    fig, ax = plt.subplots(figsize=(10, 7))
    for arch, grp in df.groupby("archetype"):
        c = ARCHETYPE_COLORS.get(arch, "#888")
        ax.scatter(grp["avg_ctr"], grp["avg_retention_rate"],
                   alpha=0.35, s=12, color=c, label=arch)
    ax.set_xlabel("Avg CTR (%)", labelpad=8)
    ax.set_ylabel("Avg Retention Rate (%)", labelpad=8)
    ax.set_title("Behavioral Clusters: Retention vs CTR\n"
                 "(subscriber count NOT used as a feature)", color=TEXT, fontsize=12, pad=12)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.3)
    ax.grid(True, alpha=0.18)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "02_cluster_scatter.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 02_cluster_scatter.png")


def plot_radar(df):
    """Radar chart of normalised mean feature values per archetype."""
    profiles = df.groupby("archetype")[FEATURE_COLS].mean()
    normed   = (profiles - profiles.min()) / (profiles.max() - profiles.min() + 1e-9)
    labels   = [c.replace("avg_","").replace("_"," ").replace("per month","/ mo").title()
                for c in FEATURE_COLS]
    N = len(labels)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(SURFACE)

    for arch in normed.index:
        vals = normed.loc[arch].tolist() + [normed.loc[arch].tolist()[0]]
        c    = ARCHETYPE_COLORS.get(arch, "#888")
        ax.plot(angles, vals, color=c, lw=2, label=arch)
        ax.fill(angles, vals, color=c, alpha=0.07)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=9, color=TEXT)
    ax.yaxis.set_visible(False)
    ax.spines["polar"].set_color("#303030")
    ax.grid(color="#303030", alpha=0.6)
    ax.set_title("Archetype Behavioral Profiles\n(normalised 0–1)", color=TEXT, pad=20, fontsize=11)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=8, framealpha=0.2)

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "03_archetype_radar.png"), dpi=150,
                bbox_inches="tight", facecolor=BG)
    plt.close()
    print("  Saved: 03_archetype_radar.png")


# ── Export creator_segments.csv ───────────────────────────────────────────────
def export_segments(df):
    """
    Write the enriched creator table used by SQL queries, Looker Studio,
    and the revenue gap analysis.

    Revenue gap columns are populated only for Niche Specialists:
        revenue_at_parity = views_90d × PARITY_RPM / 1,000
        revenue_gap       = max(0, revenue_at_parity − actual revenue)
    """
    PARITY_RPM = df[df["archetype"]=="Subscriber Giants"]["rpm"].mean()

    df = df.copy()
    df["views_90d"] = df["monthly_views"] * 3

    is_niche = df["archetype"] == "High-Retention Niche Specialists"
    df["revenue_at_parity"] = 0.0
    df["revenue_gap"]       = 0.0
    df.loc[is_niche, "revenue_at_parity"] = (
        df.loc[is_niche, "views_90d"] * PARITY_RPM / 1000
    ).round(2)
    df.loc[is_niche, "revenue_gap"] = (
        df.loc[is_niche, "revenue_at_parity"] - df.loc[is_niche, "revenue_90d"]
    ).clip(lower=0).round(2)

    out_cols = [
        "creator_id","archetype","subscriber_tier","niche_category",
        "subscriber_count","channel_age_years",
        "avg_retention_rate","avg_ctr","upload_freq_per_month",
        "avg_video_length_mins","len_consistency_score",
        "rpm","monthly_views","views_90d",
        "revenue_90d","revenue_at_parity","revenue_gap",
    ]
    # subscriber_tier may need to be (re)derived
    if "subscriber_tier" not in df.columns:
        bins   = [0,1000,10000,100000,500000,float("inf")]
        labels_t = ["Micro (<1K)","Small (1K-10K)","Mid (10K-100K)",
                    "Large (100K-500K)","Mega (500K+)"]
        df["subscriber_tier"] = pd.cut(df["subscriber_count"].astype(float),
                                       bins=bins, labels=labels_t)
    out = df[[c for c in out_cols if c in df.columns]]
    path = os.path.join(DATA_DIR, "creator_segments.csv")
    out.to_csv(path, index=False)

    gap = df.loc[is_niche,"revenue_gap"].sum()
    print(f"\n  Exported creator_segments.csv  ({len(out):,} rows)")
    print(f"  Parity RPM benchmark (Giant mean): ${PARITY_RPM:.2f}")
    print(f"  Total Niche Specialist revenue gap (90d): ${gap:,.0f}")
    return out


if __name__ == "__main__":
    print("Loading data ...")
    df = load()

    print("Standardising features ...")
    X_scaled, means, stds = standardise(df, FEATURE_COLS)

    select_k(X_scaled)

    labels, centroids, inertia, sil = run_clustering(X_scaled, K=5)

    df, centroid_df, cluster_map = label_archetypes(df, labels, centroids, means, stds)

    print("\nCluster summary:")
    print(df.groupby("archetype").agg(
        n=("creator_id","count"),
        avg_retention=("avg_retention_rate","mean"),
        avg_ctr=("avg_ctr","mean"),
        avg_rpm=("rpm","mean"),
    ).round(2).to_string())

    plot_scatter(df)
    plot_radar(df)
    export_segments(df)
    print("\nSegmentation complete.")

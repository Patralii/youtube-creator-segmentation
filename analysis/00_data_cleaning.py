"""
00_data_cleaning.py
====================
Cleans creators_messy.csv and videos_messy.csv into analysis-ready CSVs.

Every cleaning step below documents:
  • WHAT the issue is
  • WHY it exists in real YouTube analytics exports
  • HOW we fix it and what we lose/keep

Run this BEFORE any analysis script. Output files:
  data/creators_clean.csv
  data/videos_clean.csv
"""

import pandas as pd
import numpy as np
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def banner(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def audit(df, label):
    """Print a quick null + dtype audit of a dataframe."""
    print(f"\n[AUDIT] {label}  →  {len(df):,} rows × {df.shape[1]} cols")
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        print("  Nulls:")
        for col, n in nulls.items():
            print(f"    {col:<35s} {n:>5,}  ({n/len(df)*100:.1f}%)")
    else:
        print("  No nulls.")


# ════════════════════════════════════════════════════════════════
#  LOAD
# ════════════════════════════════════════════════════════════════
def load_messy():
    """
    Load with dtype=str so mixed-type columns (e.g. subscriber_count with
    both "1,234" and 5000) don't immediately coerce or raise exceptions.
    We'll cast each column to the right type after cleaning it.
    """
    creators = pd.read_csv(
        os.path.join(DATA_DIR, "creators_messy.csv"), dtype=str
    )
    videos = pd.read_csv(
        os.path.join(DATA_DIR, "videos_messy.csv"), dtype=str
    )
    print(f"Loaded creators_messy: {len(creators):,} rows")
    print(f"Loaded videos_messy:   {len(videos):,} rows")
    return creators, videos


# ════════════════════════════════════════════════════════════════
#  CREATORS — step-by-step cleaning
# ════════════════════════════════════════════════════════════════

def clean_creators(df):
    banner("CLEANING: creators")
    audit(df, "creators_messy (before)")

    # ── Step 1: Strip whitespace from ALL string columns ──────────────────
    # WHY: Issue [8] — older YouTube Studio CSV exports pad text columns
    # with leading/trailing spaces that are invisible in spreadsheet view.
    # This causes GROUP BY and JOIN operations to silently fail — "Gaming"
    # and " Gaming " are treated as two different values.
    # HOW: Apply str.strip() across every column before any other cleaning.
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())
    print("\n[1] Stripped whitespace from all string columns")

    # ── Step 2: Remove duplicate rows ─────────────────────────────────────
    # WHY: Issue [1] — creator dashboard API called twice in same refresh
    # window inserts exact duplicate rows. These inflate counts and revenue
    # totals if not removed.
    # HOW: Keep the first occurrence of each creator_id. We use creator_id
    # as the unique key because it's the system-assigned primary key.
    before = len(df)
    df = df.drop_duplicates(subset=["creator_id"], keep="first")
    dropped = before - len(df)
    print(f"[2] Removed {dropped} duplicate creator rows  (kept first occurrence)")

    # ── Step 3: Standardise niche_category values ────────────────────────
    # WHY: Issue [6] — multiple team members entered niche labels with
    # different conventions: "Fin", "personal finance", "Personal_Finance".
    # These all refer to the same niche but will appear as separate groups
    # in any aggregation.
    # HOW: Build a lookup map from every observed variant to the canonical
    # label. Unrecognised values are left as-is for manual review.
    NICHE_CANONICAL = {
        # Personal Finance
        "personal finance": "Personal Finance",
        "personal_finance": "Personal Finance",
        "fin":              "Personal Finance",
        "personal fin.":    "Personal Finance",
        "personal finance": "Personal Finance",

        # Tech
        "tech reviews":        "Tech Deep-Dive Reviews",
        "tech deep dive":      "Tech Deep-Dive Reviews",
        "tech_reviews":        "Tech Deep-Dive Reviews",
        "technology reviews":  "Tech Deep-Dive Reviews",

        # Health
        "health and fitness":  "Health & Fitness Coaching",
        "health&fitness":      "Health & Fitness Coaching",
        "health/fitness":      "Health & Fitness Coaching",
        "fitness":             "Health & Fitness Coaching",

        # Education
        "education":           "Education / Test Prep",
        "edu / test prep":     "Education / Test Prep",
        "education/testprep":  "Education / Test Prep",
        "test prep":           "Education / Test Prep",

        # DIY
        "diy":                 "DIY & Craft Tutorials",
        "crafts":              "DIY & Craft Tutorials",
        "diy & crafts":        "DIY & Craft Tutorials",
        "diy/crafts":          "DIY & Craft Tutorials",

        # Entertainment
        "entmt":               "Entertainment",
        "entertain.":          "Entertainment",

        # Gaming
        "games":               "Gaming",
        "game content":        "Gaming",

        # Food
        "food":                "Food & Cooking",
        "cooking":             "Food & Cooking",
        "food and cooking":    "Food & Cooking",
        "food/cook":           "Food & Cooking",

        # Travel
        "travelling":          "Travel",
        "travel vlogs":        "Travel",

        # Lifestyle
        "life style":          "Lifestyle",
        "lifestyle":           "Lifestyle",
    }
    def normalise_niche(val):
        if pd.isna(val):
            return val
        key = str(val).strip().lower()
        return NICHE_CANONICAL.get(key, val)   # leave unknown values as-is

    before_unique = df["niche_category"].nunique()
    df["niche_category"] = df["niche_category"].apply(normalise_niche)
    after_unique  = df["niche_category"].nunique()
    print(f"[3] Standardised niche_category:  {before_unique} unique → {after_unique} unique")

    # ── Step 4: Standardise archetype labels ──────────────────────────────
    # WHY: Issue [12] — archetype names were copy-pasted into secondary
    # sheets, producing abbreviations like "CVB", "Niche Specialists",
    # or lowercase variants.
    ARCH_CANONICAL = {
        "subscriber giants":                  "Subscriber Giants",
        "sub giants":                         "Subscriber Giants",
        "subscribergiants":                   "Subscriber Giants",
        "high retention niche specialists":   "High-Retention Niche Specialists",
        "high-retention niche specialists":   "High-Retention Niche Specialists",
        "hr niche specialists":               "High-Retention Niche Specialists",
        "niche specialists":                  "High-Retention Niche Specialists",
        "viral spike chasers":                "Viral Spike Chasers",
        "viral chasers":                      "Viral Spike Chasers",
        "viralspikeChaser":                   "Viral Spike Chasers",
        "viralspikeChaser".lower():           "Viral Spike Chasers",
        "spike chasers":                      "Viral Spike Chasers",
        "consistent volume builders":         "Consistent Volume Builders",
        "volume builders":                    "Consistent Volume Builders",
        "consistent builders":                "Consistent Volume Builders",
        "cvb":                                "Consistent Volume Builders",
        "emerging dabblers":                  "Emerging Dabblers",
        "dabblers":                           "Emerging Dabblers",
        "new dabblers":                       "Emerging Dabblers",
    }
    df["archetype"] = df["archetype"].apply(
        lambda x: ARCH_CANONICAL.get(str(x).strip().lower(), x) if pd.notna(x) else x
    )
    print(f"[4] Standardised archetype labels:  unique values now = {df['archetype'].nunique()}")

    # ── Step 5: Parse subscriber_count — remove commas, cast to int ───────
    # WHY: Issue [5] — copy-paste from YouTube Studio UI formats numbers as
    # "1,234,567". pandas reads this as a string; arithmetic fails.
    # HOW: Strip commas, then coerce to numeric. Rows that are truly
    # unparseable (not just comma-formatted) become NaN for inspection.
    df["subscriber_count"] = (
        df["subscriber_count"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .astype("Int64")   # nullable integer — preserves NaN distinction
    )
    print(f"[5] Parsed subscriber_count to int  (nulls after parse: {df['subscriber_count'].isna().sum()})")

    # ── Step 6: Parse revenue_90d — strip currency symbol ─────────────────
    # WHY: Issue [9] — finance team Excel export adds "$" and "," thousand
    # separators, making the column non-numeric.
    # HOW: Remove "$" and "," then coerce. Non-parseable → NaN.
    df["revenue_90d"] = (
        df["revenue_90d"]
        .astype(str)
        .str.replace("[$,]", "", regex=True)
        .pipe(pd.to_numeric, errors="coerce")
    )
    print(f"[6] Stripped '$' from revenue_90d  (nulls: {df['revenue_90d'].isna().sum()})")

    # ── Step 7: Parse channel_age_years — extract numeric from text ────────
    # WHY: Issue [10] — older pipeline stored age as "3 years", "18 months",
    # "2.5 yrs". We need a single float (years) for any age-based analysis.
    # HOW: Regex extract the number. If "months" appears, divide by 12.
    def parse_age(val):
        if pd.isna(val):
            return np.nan
        s = str(val).strip().lower()
        match = re.search(r"[\d.]+", s)
        if not match:
            return np.nan
        number = float(match.group())
        if "month" in s:
            number = number / 12
        return round(number, 2)

    df["channel_age_years"] = df["channel_age_years"].apply(parse_age)
    print(f"[7] Parsed channel_age_years to float  (nulls: {df['channel_age_years'].isna().sum()})")

    # ── Step 8: Parse upload_freq_per_month — strip "/month" ──────────────
    # WHY: Issue [11] — survey form returned "6/month" instead of 6.
    # HOW: Extract leading numeric portion.
    df["upload_freq_per_month"] = (
        df["upload_freq_per_month"]
        .astype(str)
        .str.extract(r"([\d.]+)")[0]
        .pipe(pd.to_numeric, errors="coerce")
    )
    print(f"[8] Cleaned upload_freq_per_month  (nulls: {df['upload_freq_per_month'].isna().sum()})")

    # ── Step 9: Cast remaining numeric columns ────────────────────────────
    for col in ["avg_retention_rate", "avg_ctr", "avg_video_length_mins",
                "avg_video_len_std", "rpm", "monthly_views"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"[9] Cast all remaining numeric columns")

    # ── Step 10: Remove impossible values — flag then drop/cap ────────────
    # WHY: Issue [7] — retention > 100% from unit mismatch; negative RPM
    # from chargeback rows; zero subscribers from unverified channels.
    # HOW:
    #   - Retention > 100%: set to NaN (can't know true value)
    #   - Negative RPM: set to NaN (refund rows — not representative)
    #   - Subscriber count == 0: drop the row (no valid creator context)

    bad_ret = df["avg_retention_rate"] > 100
    df.loc[bad_ret, "avg_retention_rate"] = np.nan
    print(f"[10a] Set {bad_ret.sum()} impossible retention values (>100%) → NaN")

    bad_rpm = df["rpm"] < 0
    df.loc[bad_rpm, "rpm"] = np.nan
    print(f"[10b] Set {bad_rpm.sum()} negative RPM values → NaN")

    zero_subs = df["subscriber_count"] == 0
    df = df[~zero_subs].copy()
    print(f"[10c] Dropped {zero_subs.sum()} rows with subscriber_count == 0")

    # ── Step 11: Impute remaining NaN numeric values ───────────────────────
    # WHY: Clustering requires complete feature vectors — NaN rows would be
    # silently dropped by most distance calculations, shrinking our dataset.
    # HOW: Impute with the archetype-level median (not global median), because
    # the distribution of retention/RPM differs significantly between archetypes.
    # Imputing with the global median would inject cross-archetype information
    # into the feature space — exactly the bias we're trying to avoid.
    IMPUTE_COLS = ["avg_retention_rate", "avg_ctr", "rpm",
                   "avg_video_length_mins", "upload_freq_per_month"]

    for col in IMPUTE_COLS:
        null_mask = df[col].isna()
        if null_mask.sum() == 0:
            continue
        # Archetype-level medians for imputation
        arch_medians = df.groupby("archetype")[col].transform("median")
        # Fall back to global median if archetype is also all-null
        global_median = df[col].median()
        fill_vals = arch_medians.where(arch_medians.notna(), global_median)
        df.loc[null_mask, col] = fill_vals[null_mask].round(2)
        print(f"[11] Imputed {null_mask.sum():>3} nulls in {col:<30s} (archetype median)")

    # ── Step 12: Add derived columns used in analysis ─────────────────────
    # len_consistency_score: inverse of within-creator video-length variance
    # (0=very inconsistent, 100=very consistent). Used as a clustering feature.
    df["len_consistency_score"] = (
        100 - (df["avg_video_len_std"] / df["avg_video_len_std"].max() * 100)
    ).clip(0, 100).round(1)

    # subscriber_tier: categorical heuristic the platform currently uses
    bins   = [0, 1_000, 10_000, 100_000, 500_000, float("inf")]
    labels = ["Micro (<1K)", "Small (1K-10K)", "Mid (10K-100K)",
              "Large (100K-500K)", "Mega (500K+)"]
    df["subscriber_tier"] = pd.cut(
        df["subscriber_count"].astype(float), bins=bins, labels=labels
    )
    print(f"[12] Added len_consistency_score and subscriber_tier")

    # ── Step 13: Final dtype enforcement ─────────────────────────────────
    df["creator_id"]     = df["creator_id"].astype(int)
    df["monthly_views"]  = df["monthly_views"].astype("Int64")
    df["subscriber_count"] = df["subscriber_count"].astype("Int64")
    print(f"[13] Enforced final dtypes")

    audit(df, "creators (after cleaning)")
    return df


# ════════════════════════════════════════════════════════════════
#  VIDEOS — step-by-step cleaning
# ════════════════════════════════════════════════════════════════

def clean_videos(df):
    banner("CLEANING: videos")
    audit(df, "videos_messy (before)")

    # ── Step 1: Strip whitespace from all strings ──────────────────────────
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())
    print("[1] Stripped whitespace from all string columns")

    # ── Step 2: Remove duplicate video rows ───────────────────────────────
    # WHY: Issue [E] — pipeline re-runs or webhook retries push the same
    # video record twice before a deduplication step is added.
    before = len(df)
    df = df.drop_duplicates(subset=["video_id"], keep="first")
    print(f"[2] Removed {before - len(df)} duplicate video rows")

    # ── Step 3: Standardise publish_date to ISO YYYY-MM-DD ────────────────
    # WHY: Issue [A] — YouTube API returns ISO 8601 dates; a social-listening
    # tool returns MM/DD/YYYY or Unix epoch seconds. Mixing formats makes
    # sorting, filtering, and time-series aggregations fail silently.
    # HOW: pandas to_datetime with infer_datetime_format handles all three
    # variants. Unix timestamps need explicit unit="s" — we detect them by
    # checking if the string is purely numeric and > 1e9.
    def parse_date(val):
        if pd.isna(val):
            return pd.NaT
        s = str(val).strip()
        if re.fullmatch(r"\d{9,11}", s):          # Unix timestamp
            return pd.to_datetime(int(s), unit="s", errors="coerce")
        return pd.to_datetime(s, errors="coerce")

    df["publish_date"] = df["publish_date"].apply(parse_date)
    null_dates = df["publish_date"].isna().sum()
    df["publish_date"] = df["publish_date"].dt.strftime("%Y-%m-%d")
    print(f"[3] Standardised publish_date → YYYY-MM-DD  (unparseable: {null_dates})")

    # ── Step 4: Parse video_length_mins — handle "Xm Ys" strings ─────────
    # WHY: Issue [F] — a UI scraper pulled video duration from the player
    # display ("14m 32s") rather than the API metadata field (14.53 float).
    def parse_video_len(val):
        if pd.isna(val):
            return np.nan
        s = str(val).strip()
        # "14m 32s" pattern
        m_match = re.search(r"(\d+)m", s)
        s_match = re.search(r"(\d+)s", s)
        if m_match:
            mins = int(m_match.group(1))
            secs = int(s_match.group(1)) if s_match else 0
            return round(mins + secs / 60, 2)
        # Pure numeric
        try:
            return round(float(s), 2)
        except:
            return np.nan

    df["video_length_mins"] = df["video_length_mins"].apply(parse_video_len)
    print(f"[4] Parsed video_length_mins  (nulls: {df['video_length_mins'].isna().sum()})")

    # ── Step 5: Cast views to integer ─────────────────────────────────────
    # WHY: Issue [C] — a join on an aggregated table returned views as
    # 45320.0 (float). View counts must be integers for correct aggregation.
    df["views"] = pd.to_numeric(df["views"], errors="coerce").round(0).astype("Int64")
    print(f"[5] Cast views to integer  (nulls: {df['views'].isna().sum()})")

    # ── Step 6: Remove negative revenue rows ──────────────────────────────
    # WHY: Issue [D] — advertiser refunds / invalid traffic credits create
    # negative revenue entries. Including them would undercount true revenue
    # in any SUM aggregation.
    # HOW: Drop rows where revenue < 0. We don't set to 0 because a
    # refund row is not a "$0 revenue" event — it's a different event type
    # that should be tracked separately (outside this analysis).
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    before = len(df)
    df = df[df["revenue"].isna() | (df["revenue"] >= 0)].copy()
    print(f"[6] Dropped {before - len(df)} negative revenue rows (chargeback events)")

    # ── Step 7: Cast remaining numerics ───────────────────────────────────
    for col in ["retention_rate", "ctr", "rpm"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"[7] Cast retention_rate, ctr, rpm to float")

    # ── Step 8: Impute missing retention_rate and ctr ─────────────────────
    # WHY: Issues [B] and [G] — retention null for Shorts; CTR null for
    # embedded player views. For video-level analysis we impute with the
    # creator-level median so the video row stays in the dataset but doesn't
    # skew individual-video comparisons.
    for col in ["retention_rate", "ctr"]:
        null_mask = df[col].isna()
        if null_mask.sum() == 0:
            continue
        creator_medians = df.groupby("creator_id")[col].transform("median")
        global_med = df[col].median()
        fill = creator_medians.where(creator_medians.notna(), global_med)
        df.loc[null_mask, col] = fill[null_mask].round(2)
        print(f"[8] Imputed {null_mask.sum():>5,} nulls in {col:<20s} (creator-level median)")

    # ── Step 9: Final dtype enforcement ───────────────────────────────────
    df["video_id"]   = pd.to_numeric(df["video_id"],   errors="coerce").astype("Int64")
    df["creator_id"] = pd.to_numeric(df["creator_id"], errors="coerce").astype("Int64")
    print("[9] Enforced final dtypes")

    audit(df, "videos (after cleaning)")
    return df


# ════════════════════════════════════════════════════════════════
#  SAVE + SUMMARY
# ════════════════════════════════════════════════════════════════

def print_cleaning_summary(orig_c, clean_c, orig_v, clean_v):
    banner("CLEANING SUMMARY")
    print(f"\n  {'TABLE':<18} {'BEFORE':>10} {'AFTER':>10} {'DROPPED':>10}")
    print(f"  {'─'*50}")
    cr_drop = len(orig_c) - len(clean_c)
    vd_drop  = len(orig_v) - len(clean_v)
    print(f"  {'creators':<18} {len(orig_c):>10,} {len(clean_c):>10,} {cr_drop:>10,}")
    print(f"  {'videos':<18} {len(orig_v):>10,} {len(clean_v):>10,} {vd_drop:>10,}")

    print(f"\n  Cleaning steps applied:")
    creator_steps = [
        "Whitespace stripped from all text columns",
        "47 duplicate creator rows removed",
        "Niche category names standardised to 10 canonical values",
        "Archetype labels standardised to 5 canonical values",
        "subscriber_count: comma-strings → integer",
        "revenue_90d: '$X,XXX.XX' strings → float",
        "channel_age_years: '3 years' / '18 months' → float",
        "upload_freq_per_month: 'X/month' → float",
        "Remaining numeric columns cast from string",
        "Retention >100% → NaN  |  Negative RPM → NaN  |  0-sub rows dropped",
        "NaN numerics imputed with archetype-level median",
        "Derived columns added: len_consistency_score, subscriber_tier",
    ]
    video_steps = [
        "Whitespace stripped from all text columns",
        "120 duplicate video rows removed",
        "publish_date: 3 mixed formats → ISO YYYY-MM-DD",
        "video_length_mins: 'Xm Ys' strings → float",
        "views: float → integer",
        "55 negative revenue rows dropped (chargeback events)",
        "retention_rate, ctr, rpm cast to float",
        "Nulls imputed with creator-level median (retention, ctr)",
    ]
    print(f"\n  creators ({len(creator_steps)} steps):")
    for s in creator_steps: print(f"    ✓ {s}")
    print(f"\n  videos ({len(video_steps)} steps):")
    for s in video_steps: print(f"    ✓ {s}")


if __name__ == "__main__":
    raw_creators, raw_videos = load_messy()

    clean_c = clean_creators(raw_creators.copy())
    clean_v = clean_videos(raw_videos.copy())

    out_c = os.path.join(DATA_DIR, "creators_clean.csv")
    out_v = os.path.join(DATA_DIR, "videos_clean.csv")

    clean_c.to_csv(out_c, index=False)
    clean_v.to_csv(out_v, index=False)

    print_cleaning_summary(raw_creators, clean_c, raw_videos, clean_v)

    print(f"\n✓  Saved: {out_c}")
    print(f"✓  Saved: {out_v}")
    print("\nReady to run 01_eda.py → 02_kmeans_scratch.py → 03_segmentation.py")

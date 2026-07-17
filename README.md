# The $2M Opportunity
### Why YouTube's Most Valuable Creators Aren't Who the Platform Thinks

> **Project type:** Creator Behavioral Segmentation + Revenue Gap Analysis  
> **Analyst:** Patrali  
> **Dataset:** ~4,000 creators · ~113,000 video records · 90-day window (Apr–Jun 2024)  
> **Method:** KMeans Clustering (manual NumPy implementation) · Revenue Gap Quantification

---

## The One-Sentence Finding

Subscriber count misses **17% of the creator base** — a high-retention archetype that outperforms top-tier creators by **+40% retention** yet earns **70% less per view**, leaving **~$2M** in unrealized revenue on the table every 90 days.

---

## Repository Structure

```
the-2m-opportunity/
│
├── data/
│   ├── generate_dataset.py       ← Generates clean synthetic data from scratch
│   ├── gen_messy.py              ← Injects 12 realistic data quality issues
│   ├── creators_messy.csv        ← Raw dataset (4,047 rows, 12 issues)
│   ├── creators_clean.csv        ← Analysis-ready creators (3,988 rows)
│   ├── videos_messy.csv          ← Raw video dataset (113,528 rows, 7 issues)
│   └── videos_clean.csv          ← Analysis-ready videos (113,353 rows)
│
├── analysis/
│   ├── 00_data_cleaning.py       ← Step-by-step cleaning with WHY/HOW comments
│   ├── 01_eda.py                 ← Exploratory data analysis + distribution plots
│   ├── 02_kmeans_scratch.py      ← KMeans built from scratch in NumPy (no sklearn)
│   ├── 03_segmentation.py        ← Full clustering pipeline → creator_segments.csv
│   ├── 04_revenue_gap.py         ← Quantifies the $2M opportunity
│   └── 05_validation.py          ← 3 independent validation checks
│
├── sql/
│   ├── 01_creator_overview.sql   ← Creator base + niche distribution
│   ├── 02_tier_analysis.sql      ← Subscriber-tier revenue (the surface assumption)
│   ├── 03_archetype_performance.sql ← Post-clustering archetype profiles
│   ├── 04_revenue_gap.sql        ← Gap quantification in SQL
│   └── 05_validation.sql         ← SQL-level validation checks
│
├── dashboard/
│   └── the_2m_opportunity_dashboard.html  ← Self-contained interactive dashboard
│
├── looker_studio_guide.md        ← Step-by-step Looker Studio build instructions
├── requirements.txt
└── README.md
```

---

## The Narrative (7 Acts)

| Act | What happens |
|-----|-------------|
| I   | **The Assumption** — subscriber count is the platform's proxy for creator value |
| II  | **Surface Check** — Mega-tier creators DO generate 50%+ of revenue. Assumption holds. |
| III | **Reframe** — cluster creators on behavior (retention, CTR, cadence, velocity, consistency), not scale |
| IV  | **The Finding** — a 684-creator archetype with +40% retention vs Giants, hidden in the "Mid" tier |
| V   | **The Gap** — that archetype earns 70% less per view → $1.99M unrealized revenue / 90 days |
| VI  | **Validation** — 3 independent checks confirm it's structural, not noise |
| VII | **Recommendation** — shift algorithmic boosting and RPM tiers toward behavioral health signals |

---

## How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Regenerate the raw data
```bash
python data/generate_dataset.py
python data/gen_messy.py
```
> Skip this step — messy and clean CSVs are already included.

### 3. Clean the data
```bash
python analysis/00_data_cleaning.py
```
Outputs: `data/creators_clean.csv`, `data/videos_clean.csv`

### 4. Run EDA
```bash
python analysis/01_eda.py
```
Outputs: `outputs/eda/*.png`

### 5. Run clustering
```bash
python analysis/03_segmentation.py
```
Outputs: `data/creator_segments.csv`, `outputs/segmentation/*.png`

### 6. Quantify the revenue gap
```bash
python analysis/04_revenue_gap.py
```
Outputs: `outputs/revenue_gap/*.png`

### 7. Validate
```bash
python analysis/05_validation.py
```
Outputs: `outputs/validation/*.png`

### 8. Run SQL queries
Load `data/creators_clean.csv` and `data/videos_clean.csv` into SQLite:
```bash
sqlite3 youtube.db
.mode csv
.import data/creators_clean.csv creators
.import data/videos_clean.csv videos
.read sql/01_creator_overview.sql
```

### 9. Open the dashboard
Open `dashboard/the_2m_opportunity_dashboard.html` in any browser.  
No server needed — fully self-contained.

---

## The Five Behavioral Archetypes

| Archetype | Creators | Avg Retention | Avg RPM | Avg Rev / 90d |
|-----------|----------|---------------|---------|---------------|
| High-Retention Niche Specialists | 684 (17.1%) | **54.2%** | $1.29 | $1,251 |
| Subscriber Giants | 312 (7.8%) | 38.7% | **$4.30** | $36,120 |
| Viral Spike Chasers | 540 (13.5%) | 21.8% | $2.10 | $3,990 |
| Consistent Volume Builders | 1,218 (30.5%) | 31.4% | $2.60 | $1,612 |
| Emerging Dabblers | 1,246 (31.1%) | 19.3% | $1.80 | $68 |

---

## Key Technical Decisions

**Why manual KMeans instead of scikit-learn?**  
sklearn's `KMeans()` is a one-line API call. The manual NumPy implementation in `02_kmeans_scratch.py` demonstrates understanding of the E-step/M-step, convergence criteria, empty-cluster handling, and why multiple random restarts matter. It's a deliberate portfolio differentiator for interviews where "walk me through the algorithm" is standard.

**Why exclude subscriber count from clustering features?**  
Subscriber count is the variable whose validity as a proxy we are testing. Including it in the feature set would bias clusters toward subscriber tiers, making it impossible to find archetypes that cut across tiers.

**Why archetype-level median imputation (not global)?**  
The distribution of retention and RPM differs significantly between archetypes. Imputing with the global median injects cross-archetype information into the feature space — the exact bias we're trying to avoid.

**Why Subscriber Giants as the parity benchmark?**  
Giants represent the segment the algorithm currently rewards. Using the platform average would understate the gap. Giants is the fairest apples-to-apples comparison.

---

## Skills Demonstrated

**Analytics:** Behavioral segmentation · Revenue gap quantification · Outlier validation · Cohort profiling · Business prioritisation  
**ML:** Unsupervised clustering · K selection (elbow + silhouette) · Cluster stability testing  
**Engineering:** End-to-end data pipeline · Synthetic data generation · Multi-format data cleaning  
**Communication:** PM-facing executive summary · Dollar-quantified impact · Two-sided marketplace framing  
**Tools:** Python · Pandas · NumPy · SQL/SQLite · Matplotlib/Seaborn · Looker Studio  

---

## Recruiter Signal

This project demonstrates **supply-side marketplace thinking** — not just user analytics. The framing is: YouTube's algorithm is a two-sided market (creators supply content, advertisers buy attention). Misaligning monetisation signals with actual attention quality is a supply-side pricing bug, not just a creator-fairness issue. The $2M figure is the business case for fixing it.

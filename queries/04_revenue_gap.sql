-- ================================================================
-- 04_revenue_gap.sql
-- Purpose : Quantify the revenue gap for High-Retention Niche
--           Specialists — the "$2M Opportunity" calculation in SQL.
-- Tables  : creator_segments, videos
-- ================================================================


-- ── 1. Establish the parity RPM benchmark ────────────────────────────────────
-- WHY: The parity benchmark must be anchored before computing any gap.
--      We use Subscriber Giants' mean RPM because:
--        (a) Giants are who the algorithm currently optimises for
--        (b) Niche Specialists hold audiences 40% longer than Giants —
--            so parity is the MINIMUM fair comparison, not a generous one.
--      Using the platform average would understate the gap (dragged down
--      by Dabblers). Giants is the correct apples-to-apples benchmark.
SELECT
    ROUND(AVG(rpm), 4) AS parity_rpm_benchmark
FROM creator_segments
WHERE archetype = 'Subscriber Giants';


-- ── 2. Revenue gap per Niche Specialist creator ───────────────────────────────
-- WHY: Computing the gap at individual creator level lets us:
--        (a) Sum to the headline total (the $2M figure)
--        (b) Break it down by niche or tier
--        (c) Run validation checks (outlier trim, broad-base rate)
--        (d) Identify specific creators to prioritise for the pilot
-- The MAX(0, ...) floors the gap at zero — we don't penalise creators
-- already earning above parity (that would be a different finding).
WITH parity AS (
    SELECT AVG(rpm) AS parity_rpm
    FROM creator_segments
    WHERE archetype = 'Subscriber Giants'
)
SELECT
    cs.creator_id,
    cs.niche_category,
    cs.subscriber_tier,
    cs.subscriber_count,
    cs.avg_retention_rate,
    cs.rpm                                                AS actual_rpm,
    ROUND(p.parity_rpm, 4)                               AS parity_rpm,
    cs.views_90d,
    ROUND(cs.revenue_90d, 2)                             AS current_revenue,
    ROUND(cs.views_90d * p.parity_rpm / 1000.0, 2)      AS revenue_at_parity,
    ROUND(MAX(0, cs.views_90d * p.parity_rpm / 1000.0
              - cs.revenue_90d), 2)                      AS revenue_gap
FROM creator_segments cs
CROSS JOIN parity p
WHERE cs.archetype = 'High-Retention Niche Specialists'
ORDER BY revenue_gap DESC;


-- ── 3. The headline number ────────────────────────────────────────────────────
-- WHY: The executive one-pager needs one defensible dollar figure.
--      This query produces it from first principles — not hardcoded.
--      The gap_as_pct_of_platform_revenue figure is for the one-liner:
--      "17% of creators, 8.9% of addressable revenue."
WITH parity AS (
    SELECT AVG(rpm) AS parity_rpm
    FROM creator_segments
    WHERE archetype = 'Subscriber Giants'
),
gaps AS (
    SELECT
        MAX(0, cs.views_90d * p.parity_rpm / 1000.0 - cs.revenue_90d) AS gap
    FROM creator_segments cs
    CROSS JOIN parity p
    WHERE cs.archetype = 'High-Retention Niche Specialists'
)
SELECT
    (SELECT COUNT(*) FROM creator_segments
     WHERE archetype='High-Retention Niche Specialists')  AS n_niche_creators,
    SUM(CASE WHEN gap > 0 THEN 1 ELSE 0 END)              AS creators_with_positive_gap,
    ROUND(SUM(gap), 0)                                     AS total_gap_usd,
    ROUND(AVG(gap), 0)                                     AS avg_gap_per_creator,
    ROUND(SUM(gap) * 100.0 /
          (SELECT SUM(revenue_90d) FROM creator_segments), 1)
                                                           AS gap_as_pct_of_platform_revenue
FROM gaps;


-- ── 4. Gap by niche category ─────────────────────────────────────────────────
-- WHY: The "pilot Finance + Tech first" recommendation must be data-backed.
--      This query shows those two niches hold ~48% of the total gap while
--      being categories where advertisers already pay premium CPMs —
--      lowest-risk place to introduce a retention-indexed pricing pilot.
WITH parity AS (
    SELECT AVG(rpm) AS parity_rpm
    FROM creator_segments WHERE archetype='Subscriber Giants'
)
SELECT
    cs.niche_category,
    COUNT(*)                                              AS n_creators,
    ROUND(SUM(cs.revenue_90d), 0)                        AS current_total_rev,
    ROUND(SUM(cs.views_90d * p.parity_rpm / 1000.0), 0) AS parity_total_rev,
    ROUND(SUM(MAX(0, cs.views_90d * p.parity_rpm / 1000.0
                  - cs.revenue_90d)), 0)                 AS total_gap,
    ROUND(
        SUM(MAX(0, cs.views_90d * p.parity_rpm / 1000.0 - cs.revenue_90d))
        * 100.0 /
        (SELECT SUM(MAX(0, cx.views_90d * px.parity_rpm / 1000.0 - cx.revenue_90d))
         FROM creator_segments cx CROSS JOIN parity px
         WHERE cx.archetype='High-Retention Niche Specialists'),
    1)                                                   AS pct_of_total_gap
FROM creator_segments cs
CROSS JOIN parity p
WHERE cs.archetype = 'High-Retention Niche Specialists'
GROUP BY cs.niche_category
ORDER BY total_gap DESC;


-- ── 5. Gap by subscriber sub-tier within the archetype ────────────────────────
-- WHY: Confirms the gap is NOT concentrated in one narrow slice of the
--      archetype (e.g., only 10K–25K creators). If every sub-tier shows
--      a positive average gap, the structural argument is stronger.
WITH parity AS (
    SELECT AVG(rpm) AS parity_rpm
    FROM creator_segments WHERE archetype='Subscriber Giants'
)
SELECT
    CASE
        WHEN cs.subscriber_count < 10000  THEN 'A. Under 10K'
        WHEN cs.subscriber_count < 25000  THEN 'B. 10K–25K'
        WHEN cs.subscriber_count < 50000  THEN 'C. 25K–50K'
        WHEN cs.subscriber_count < 100000 THEN 'D. 50K–100K'
        ELSE                                   'E. 100K+'
    END AS sub_tier,
    COUNT(*)                                                        AS n_creators,
    ROUND(AVG(cs.avg_retention_rate), 2)                           AS avg_retention,
    ROUND(AVG(cs.rpm), 2)                                          AS avg_rpm,
    ROUND(AVG(MAX(0, cs.views_90d * p.parity_rpm / 1000.0
                  - cs.revenue_90d)), 0)                           AS avg_gap_per_creator,
    ROUND(SUM(MAX(0, cs.views_90d * p.parity_rpm / 1000.0
                  - cs.revenue_90d)), 0)                           AS total_gap
FROM creator_segments cs
CROSS JOIN parity p
WHERE cs.archetype = 'High-Retention Niche Specialists'
GROUP BY sub_tier
ORDER BY sub_tier;


-- ── 6. Video-level retention vs revenue-per-view ──────────────────────────────
-- WHY: Confirms the retention-RPM decoupling exists at the individual
--      VIDEO level, not just the creator level. Rules out the explanation
--      that some creators happen to be in low-RPM niches irrespective of
--      how good their retention is.
SELECT
    CASE
        WHEN retention_rate >= 50 THEN 'A. High   (50%+)'
        WHEN retention_rate >= 35 THEN 'B. Medium (35–50%)'
        WHEN retention_rate >= 20 THEN 'C. Low    (20–35%)'
        ELSE                           'D. Very Low (<20%)'
    END AS retention_bucket,
    COUNT(*)                                                  AS n_videos,
    ROUND(AVG(rpm), 2)                                        AS avg_rpm,
    ROUND(AVG(CAST(revenue AS REAL) /
              NULLIF(CAST(views AS REAL), 0) * 1000), 4)     AS revenue_per_1000_views,
    ROUND(AVG(CAST(views AS REAL)), 0)                        AS avg_views_per_video
FROM videos
GROUP BY retention_bucket
ORDER BY retention_bucket;

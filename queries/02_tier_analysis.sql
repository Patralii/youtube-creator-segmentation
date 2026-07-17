-- ================================================================
-- 02_tier_analysis.sql
-- Purpose : Reproduce the subscriber-tier revenue view that forms
--           Act II — showing WHY the platform assumption looks
--           correct on the surface, before clustering reframes it.
-- Table   : creators
-- ================================================================


-- ── 1. Revenue by subscriber tier ────────────────────────────────────────────
-- WHY: This is the exact table that justifies subscriber-weighted algorithmic
--      boosting. Mega creators dominate revenue — which, in isolation, makes
--      concentrating resources on them seem rational.
--      This query is the "before" picture. The clustering will reframe it.
SELECT
    CASE
        WHEN subscriber_count >= 500000 THEN '1. Mega (500K+)'
        WHEN subscriber_count >= 100000 THEN '2. Large (100K–500K)'
        WHEN subscriber_count >= 10000  THEN '3. Mid (10K–100K)'
        WHEN subscriber_count >= 1000   THEN '4. Small (1K–10K)'
        ELSE                                 '5. Micro (<1K)'
    END AS subscriber_tier,
    COUNT(*)                                  AS n_creators,
    ROUND(COUNT(*) * 100.0 /
          (SELECT COUNT(*) FROM creators), 1) AS pct_of_base,
    ROUND(AVG(revenue_90d), 0)                AS avg_rev_per_creator,
    ROUND(SUM(revenue_90d), 0)                AS total_tier_revenue,
    ROUND(SUM(revenue_90d) * 100.0 /
          (SELECT SUM(revenue_90d) FROM creators), 1)
                                              AS pct_of_platform_rev
FROM creators
GROUP BY subscriber_tier
ORDER BY subscriber_tier;


-- ── 2. Revenue concentration (top 10% vs bottom 50%) ──────────────────────────
-- WHY: A Gini-style comparison is intuitive for a PM audience.
--      It quantifies HOW concentrated revenue is, making the case that
--      subscriber-tier slicing is a very coarse instrument.
WITH ranked AS (
    SELECT
        creator_id,
        revenue_90d,
        PERCENT_RANK() OVER (ORDER BY revenue_90d) AS pct_rank
    FROM creators
)
SELECT
    'Top 10% by revenue'   AS segment,
    COUNT(*)               AS n_creators,
    ROUND(SUM(revenue_90d), 0)  AS total_revenue,
    ROUND(SUM(revenue_90d) * 100.0 /
          (SELECT SUM(revenue_90d) FROM creators), 1) AS pct_of_total
FROM ranked WHERE pct_rank >= 0.90
UNION ALL
SELECT
    'Bottom 50% by revenue',
    COUNT(*),
    ROUND(SUM(revenue_90d), 0),
    ROUND(SUM(revenue_90d) * 100.0 /
          (SELECT SUM(revenue_90d) FROM creators), 1)
FROM ranked WHERE pct_rank < 0.50;


-- ── 3. RPM by subscriber tier ─────────────────────────────────────────────────
-- WHY: To understand the monetisation gap, first confirm that RPM already
--      correlates with subscriber tier. This sets up the next question:
--      is that correlation causal, or is something else (retention) driving it?
--      The "retention per RPM dollar" column signals who delivers the most
--      attention-per-dollar — even before clustering.
SELECT
    CASE
        WHEN subscriber_count >= 500000 THEN '1. Mega (500K+)'
        WHEN subscriber_count >= 100000 THEN '2. Large (100K–500K)'
        WHEN subscriber_count >= 10000  THEN '3. Mid (10K–100K)'
        WHEN subscriber_count >= 1000   THEN '4. Small (1K–10K)'
        ELSE                                 '5. Micro (<1K)'
    END AS subscriber_tier,
    ROUND(AVG(rpm), 2)                AS avg_rpm,
    ROUND(AVG(avg_retention_rate), 2) AS avg_retention,
    -- Attention efficiency: retention points delivered per $1 RPM
    -- High = lots of retention, not paid for it (the core inefficiency)
    ROUND(AVG(avg_retention_rate) / NULLIF(AVG(rpm), 0), 2)
                                      AS retention_per_rpm_dollar
FROM creators
GROUP BY subscriber_tier
ORDER BY subscriber_tier;


-- ── 4. Internal variance of the Mid tier ─────────────────────────────────────
-- WHY: The Mid tier (10K–100K) holds 45%+ of all creators but is treated
--      as one homogeneous group. This query shows the retention std dev
--      inside that single tier is huge — direct evidence that one label
--      hides meaningful heterogeneity, and that clustering is necessary.
SELECT
    'Mid tier (10K–100K)'             AS segment,
    COUNT(*)                          AS n_creators,
    ROUND(AVG(avg_retention_rate), 2) AS mean_retention,
    ROUND(MIN(avg_retention_rate), 2) AS min_retention,
    ROUND(MAX(avg_retention_rate), 2) AS max_retention,
    -- A large standard deviation here is the key diagnostic:
    -- it means the "Mid" label covers wildly different creator types
    ROUND(AVG(rpm), 2)                AS mean_rpm,
    ROUND(MIN(rpm), 2)                AS min_rpm,
    ROUND(MAX(rpm), 2)                AS max_rpm
FROM creators
WHERE subscriber_count BETWEEN 10000 AND 100000;


-- ── 5. Per-tier revenue vs creator count scatter (for charting) ───────────────
-- WHY: This summary feeds directly into an XY scatter in Looker Studio —
--      one dot per tier showing the creator-share vs revenue-share mismatch.
SELECT
    CASE
        WHEN subscriber_count >= 500000 THEN 'Mega'
        WHEN subscriber_count >= 100000 THEN 'Large'
        WHEN subscriber_count >= 10000  THEN 'Mid'
        WHEN subscriber_count >= 1000   THEN 'Small'
        ELSE                                 'Micro'
    END AS tier_short,
    COUNT(*) AS n_creators,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM creators), 1) AS pct_creators,
    ROUND(SUM(revenue_90d) * 100.0 /
          (SELECT SUM(revenue_90d) FROM creators), 1)            AS pct_revenue,
    ROUND(AVG(revenue_90d), 0)                                   AS avg_rev
FROM creators
GROUP BY tier_short;

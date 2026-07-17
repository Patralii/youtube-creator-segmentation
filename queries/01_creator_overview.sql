-- ================================================================
-- 01_creator_overview.sql
-- Purpose : High-level snapshot of the creator base before any
--           segmentation — sizes, niches, age, cadence buckets.
-- Table   : creators_clean
-- Load    : .import data/creators_clean.csv creators
-- ================================================================


-- ── 1. Dataset size check ─────────────────────────────────────────────────────
-- WHY: Confirm the expected ~4,000 rows made it through cleaning intact.
SELECT COUNT(*) AS total_creators
FROM creators;


-- ── 2. Creator count, avg subscribers, avg retention by niche ─────────────────
-- WHY: Understand the niche landscape before segmentation.
--      Which niches are most crowded? Which have the best retention?
--      This sets context for later when we show Finance and Tech carry
--      the largest revenue gap.
SELECT
    niche_category,
    COUNT(*)                                  AS creator_count,
    ROUND(AVG(subscriber_count), 0)           AS avg_subscribers,
    ROUND(AVG(avg_retention_rate), 2)         AS avg_retention,
    ROUND(AVG(rpm), 2)                        AS avg_rpm,
    ROUND(SUM(revenue_90d), 0)                AS total_revenue_90d
FROM creators
GROUP BY niche_category
ORDER BY creator_count DESC;


-- ── 3. Subscriber distribution by decile ─────────────────────────────────────
-- WHY: Subscriber data is highly right-skewed (a power-law distribution).
--      Deciles reveal HOW concentrated the top end is — more informative
--      than mean/median alone. Shows why Mega-tier analysis looks compelling
--      but misses the middle.
WITH deciles AS (
    SELECT
        creator_id,
        subscriber_count,
        NTILE(10) OVER (ORDER BY subscriber_count) AS decile
    FROM creators
)
SELECT
    decile,
    COUNT(*)                         AS n_creators,
    MIN(subscriber_count)            AS min_subs,
    MAX(subscriber_count)            AS max_subs,
    ROUND(AVG(subscriber_count), 0)  AS avg_subs
FROM deciles
GROUP BY decile
ORDER BY decile;


-- ── 4. Channel age vs revenue ─────────────────────────────────────────────────
-- WHY: Before attributing the revenue gap to retention/RPM differences,
--      rule out channel age as a confound. Older channels could simply have
--      more brand deals, backlog views, etc.
--      If age explains RPM differences between archetypes, the finding is
--      weaker. If not, it strengthens the structural argument.
SELECT
    CAST(channel_age_years AS INT)     AS age_floor,
    COUNT(*)                           AS creators,
    ROUND(AVG(revenue_90d), 0)         AS avg_revenue_90d,
    ROUND(AVG(rpm), 2)                 AS avg_rpm,
    ROUND(AVG(avg_retention_rate), 2)  AS avg_retention
FROM creators
GROUP BY age_floor
ORDER BY age_floor;


-- ── 5. Upload cadence distribution ───────────────────────────────────────────
-- WHY: Upload frequency is one of the five clustering features.
--      Understanding its natural spread (is it bimodal?) helps interpret
--      which archetypes it will differentiate most clearly.
SELECT
    CASE
        WHEN upload_freq_per_month < 2   THEN 'A. Very Low  (<2/mo)'
        WHEN upload_freq_per_month < 6   THEN 'B. Low       (2–6/mo)'
        WHEN upload_freq_per_month < 12  THEN 'C. Medium    (6–12/mo)'
        WHEN upload_freq_per_month < 20  THEN 'D. High      (12–20/mo)'
        ELSE                                  'E. Very High (20+/mo)'
    END AS cadence_bucket,
    COUNT(*)                           AS creator_count,
    ROUND(AVG(avg_retention_rate), 2)  AS avg_retention,
    ROUND(AVG(rpm), 2)                 AS avg_rpm
FROM creators
GROUP BY cadence_bucket
ORDER BY cadence_bucket;


-- ── 6. Retention distribution by niche ───────────────────────────────────────
-- WHY: Some niches (Finance, Education) are naturally "lean-in" content
--      where audiences watch more completely. Knowing niche-level retention
--      baselines helps contextualise why Finance and Tech carry the largest gap.
SELECT
    niche_category,
    ROUND(AVG(avg_retention_rate), 2)   AS avg_retention,
    ROUND(MIN(avg_retention_rate), 2)   AS min_retention,
    ROUND(MAX(avg_retention_rate), 2)   AS max_retention,
    ROUND(AVG(rpm), 2)                  AS avg_rpm,
    COUNT(*)                            AS n_creators
FROM creators
GROUP BY niche_category
ORDER BY avg_retention DESC;

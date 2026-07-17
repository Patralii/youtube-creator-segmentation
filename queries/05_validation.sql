-- ================================================================
-- 05_validation.sql
-- Purpose : SQL-level validation checks on the revenue gap finding.
--           Written for PM/business stakeholders — no stats jargon.
-- Tables  : creator_segments, videos
-- ================================================================


-- ── 1. Broad-base check — % of Niche Specialists with a positive gap ──────────
-- WHY: If the total gap is driven by 5–10 creators with massive gaps while
--      the other 670+ break even, the finding is a "whale story," not a
--      structural archetype story. A policy fix (retention-indexed RPM)
--      helps the majority only if the gap is broad-based.
-- PASS: pct_with_positive_gap >= 80%
WITH parity AS (
    SELECT AVG(rpm) AS parity_rpm
    FROM creator_segments WHERE archetype='Subscriber Giants'
),
individual_gaps AS (
    SELECT
        cs.creator_id,
        MAX(0, cs.views_90d * p.parity_rpm / 1000.0
            - cs.revenue_90d) AS gap
    FROM creator_segments cs CROSS JOIN parity p
    WHERE cs.archetype = 'High-Retention Niche Specialists'
)
SELECT
    COUNT(*)                                              AS total_niche_creators,
    SUM(CASE WHEN gap > 0 THEN 1 ELSE 0 END)             AS creators_positive_gap,
    ROUND(SUM(CASE WHEN gap > 0 THEN 1.0 ELSE 0 END)
          / COUNT(*) * 100, 1)                           AS pct_with_positive_gap,
    -- Pass threshold note
    CASE WHEN SUM(CASE WHEN gap > 0 THEN 1.0 ELSE 0 END)
              / COUNT(*) * 100 >= 80
         THEN 'PASS' ELSE 'FAIL' END                     AS check_result
FROM individual_gaps;


-- ── 2. Gap consistency within subscriber sub-tiers ───────────────────────────
-- WHY: If the gap exists only in one narrow subscriber slice (e.g. 10K–25K)
--      but disappears in 50K–100K, the finding is not cleanly "archetype-level"
--      — it's about a narrow size band. Consistent positive gaps across ALL
--      sub-tiers confirms structural breadth.
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
    COUNT(*)                           AS n_creators,
    ROUND(AVG(cs.avg_retention_rate),2) AS avg_retention,
    ROUND(AVG(cs.rpm),2)               AS avg_rpm,
    ROUND(AVG(MAX(0, cs.views_90d * p.parity_rpm / 1000.0
                  - cs.revenue_90d)),0) AS avg_gap_per_creator,
    CASE WHEN AVG(MAX(0, cs.views_90d * p.parity_rpm / 1000.0
                      - cs.revenue_90d)) > 0
         THEN 'positive' ELSE 'zero / negative' END AS gap_direction
FROM creator_segments cs CROSS JOIN parity p
WHERE cs.archetype = 'High-Retention Niche Specialists'
GROUP BY sub_tier
ORDER BY sub_tier;


-- ── 3. Is the RPM gap explained by channel age? ───────────────────────────────
-- WHY: New channels often earn lower RPM because they lack brand deals and
--      Community Post CPMs. If Niche Specialists are simply new channels,
--      the gap might self-correct over time without intervention.
--      If channel ages are SIMILAR between archetypes but the RPM gap persists,
--      the gap is structural — not an age artefact.
SELECT
    archetype,
    ROUND(AVG(channel_age_years), 1)  AS avg_channel_age,
    ROUND(AVG(rpm), 2)                AS avg_rpm,
    ROUND(AVG(avg_retention_rate), 2) AS avg_retention,
    COUNT(*)                          AS n_creators
FROM creator_segments
WHERE archetype IN ('High-Retention Niche Specialists', 'Subscriber Giants')
GROUP BY archetype;
-- Interpretation: if avg_channel_age is similar between the two archetypes
-- but avg_rpm is still 70% lower for Niche Specialists, age is NOT the driver.


-- ── 4. Video-level consistency — is Niche Specialist retention robust? ─────────
-- WHY: If Niche Specialists have high AVERAGE retention but extreme variance
--      (great some weeks, terrible others), their "high retention" label is
--      misleading. We use pct_high_retention_videos as a stability proxy:
--      what fraction of their individual videos exceed a 45% retention threshold?
SELECT
    v.archetype,
    COUNT(*)                                                AS total_videos,
    ROUND(AVG(v.retention_rate), 2)                        AS avg_video_retention,
    ROUND(SUM(CASE WHEN v.retention_rate >= 45 THEN 1.0 ELSE 0 END)
          / COUNT(*) * 100, 1)                             AS pct_high_retention_videos,
    ROUND(AVG(v.rpm), 2)                                   AS avg_video_rpm
FROM videos v
WHERE v.archetype IN (
    'High-Retention Niche Specialists',
    'Subscriber Giants'
)
GROUP BY v.archetype;
-- PASS: Niche Specialists should show higher pct_high_retention_videos
-- even at the per-video level — confirming the archetype label holds
-- at granular level, not just in creator-level averages.


-- ── 5. Outlier trim — gap before/after removing top 5% view creators ──────────
-- WHY: Creators who went viral during the 90-day window have inflated views.
--      Removing the top 5% by views tests whether they are driving the headline
--      gap number.  If ≥85% of the gap survives the trim, it's structural.
WITH parity AS (
    SELECT AVG(rpm) AS parity_rpm
    FROM creator_segments WHERE archetype='Subscriber Giants'
),
ranked_niche AS (
    SELECT
        cs.*,
        MAX(0, cs.views_90d * p.parity_rpm / 1000.0
            - cs.revenue_90d)                   AS gap,
        NTILE(20) OVER (ORDER BY cs.views_90d)  AS views_vigintile
    FROM creator_segments cs CROSS JOIN parity p
    WHERE cs.archetype = 'High-Retention Niche Specialists'
)
SELECT
    CASE WHEN views_vigintile < 20 THEN 'Retained (bottom 95%)'
         ELSE 'Removed  (top 5% view-spike)' END   AS group_label,
    COUNT(*)                                        AS n_creators,
    ROUND(SUM(gap), 0)                              AS total_gap,
    ROUND(SUM(gap) * 100.0 /
          (SELECT SUM(MAX(0, cx.views_90d * px.parity_rpm / 1000.0 - cx.revenue_90d))
           FROM creator_segments cx CROSS JOIN parity px
           WHERE cx.archetype='High-Retention Niche Specialists'), 1)
                                                   AS pct_of_total_gap
FROM ranked_niche
GROUP BY group_label;
-- PASS: "Retained" group should carry ≥85% of total gap.


-- ── 6. Final validation summary (single-query version) ───────────────────────
-- WHY: One table that shows three checks pass — designed for inclusion in an
--      executive summary slide without requiring the audience to cross-reference
--      multiple query results.
WITH parity AS (
    SELECT AVG(rpm) AS parity_rpm
    FROM creator_segments WHERE archetype='Subscriber Giants'
),
niche_gaps AS (
    SELECT
        cs.views_90d,
        cs.revenue_90d,
        MAX(0, cs.views_90d * p.parity_rpm / 1000.0 - cs.revenue_90d) AS gap
    FROM creator_segments cs CROSS JOIN parity p
    WHERE cs.archetype='High-Retention Niche Specialists'
),
metrics AS (
    SELECT
        COUNT(*)                                              AS total,
        SUM(CASE WHEN gap > 0 THEN 1.0 ELSE 0 END)
            / COUNT(*) * 100                                 AS broadbase_pct,
        SUM(CASE WHEN views_90d <=
            (SELECT views_90d FROM (
                SELECT views_90d,
                       ROW_NUMBER() OVER (ORDER BY views_90d)   AS rn,
                       COUNT(*) OVER ()                         AS cnt
                FROM niche_gaps
            ) WHERE rn = CAST(cnt * 0.95 AS INT))
            THEN gap ELSE 0 END)
            / SUM(gap) * 100                                 AS outlier_trim_retained_pct
    FROM niche_gaps
)
SELECT
    ROUND(broadbase_pct, 1)          AS pct_creators_with_positive_gap,
    CASE WHEN broadbase_pct >= 80
         THEN 'PASS' ELSE 'FAIL' END AS broadbase_check,
    ROUND(outlier_trim_retained_pct, 1)     AS pct_gap_after_trim,
    CASE WHEN outlier_trim_retained_pct >= 85
         THEN 'PASS' ELSE 'FAIL' END AS outlier_trim_check
FROM metrics;

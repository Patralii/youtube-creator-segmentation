-- ================================================================
-- 03_archetype_performance.sql
-- Purpose : Profile the five behavioral archetypes after clustering.
--           Uses creator_segments.csv which has the 'archetype' column.
-- Table   : creator_segments
-- Load    : .import data/creator_segments.csv creator_segments
-- ================================================================


-- ── 1. Summary stats per archetype ───────────────────────────────────────────
-- WHY: First question stakeholders ask: "who are these archetypes and how
--      do they compare?" This is the primary comparison table for the
--      executive summary page.
SELECT
    archetype,
    COUNT(*)                                  AS n_creators,
    ROUND(COUNT(*) * 100.0 /
          (SELECT COUNT(*) FROM creator_segments), 1)
                                              AS pct_of_base,
    ROUND(AVG(subscriber_count), 0)           AS avg_subscribers,
    ROUND(AVG(avg_retention_rate), 2)         AS avg_retention,
    ROUND(AVG(avg_ctr), 2)                    AS avg_ctr,
    ROUND(AVG(upload_freq_per_month), 1)      AS avg_uploads_per_month,
    ROUND(AVG(len_consistency_score), 1)      AS avg_len_consistency,
    ROUND(AVG(rpm), 2)                        AS avg_rpm,
    ROUND(AVG(revenue_90d), 0)                AS avg_revenue_90d,
    ROUND(SUM(revenue_90d), 0)                AS total_archetype_revenue
FROM creator_segments
GROUP BY archetype
ORDER BY avg_retention DESC;


-- ── 2. Niche Specialists vs Giants — exact head-to-head ──────────────────────
-- WHY: The core claim is "+40% retention, −70% RPM." This query produces
--      the exact numbers for the "Unexpected Finding" page.
--      retention_per_rpm_dollar is the key efficiency metric:
--      "who delivers the most completed attention per advertising dollar?"
SELECT
    archetype,
    ROUND(AVG(avg_retention_rate), 2)  AS avg_retention,
    ROUND(AVG(rpm), 2)                 AS avg_rpm,
    ROUND(AVG(avg_retention_rate) /
          NULLIF(AVG(rpm), 0), 2)      AS retention_per_rpm_dollar,
    ROUND(AVG(subscriber_count), 0)    AS avg_subscribers,
    COUNT(*)                           AS n_creators
FROM creator_segments
WHERE archetype IN (
    'High-Retention Niche Specialists',
    'Subscriber Giants'
)
GROUP BY archetype;


-- ── 3. Where Niche Specialists live in subscriber-tier space ─────────────────
-- WHY: 71% of Niche Specialists are in the Mid tier — the tier the
--      platform currently treats as "middle of the pack." This query
--      produces the exact percentage that explains WHY subscriber-tier
--      slicing missed the archetype. Critical for the interview story.
SELECT
    subscriber_tier,
    COUNT(*)  AS niche_specialist_count,
    ROUND(COUNT(*) * 100.0 /
          (SELECT COUNT(*) FROM creator_segments
           WHERE archetype = 'High-Retention Niche Specialists'), 1)
              AS pct_of_archetype
FROM creator_segments
WHERE archetype = 'High-Retention Niche Specialists'
GROUP BY subscriber_tier
ORDER BY pct_of_archetype DESC;


-- ── 4. Cross-table: archetype composition within each subscriber tier ─────────
-- WHY: Proves that archetypes are NOT the same as subscriber tiers.
--      Every tier contains creators from multiple archetypes. This is the
--      key evidence that behavioral clustering adds information beyond
--      what tier-based analysis already captures.
SELECT
    subscriber_tier,
    ROUND(SUM(CASE WHEN archetype='Subscriber Giants'                THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) AS pct_giants,
    ROUND(SUM(CASE WHEN archetype='High-Retention Niche Specialists' THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) AS pct_niche,
    ROUND(SUM(CASE WHEN archetype='Viral Spike Chasers'              THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) AS pct_viral,
    ROUND(SUM(CASE WHEN archetype='Consistent Volume Builders'       THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) AS pct_volume,
    ROUND(SUM(CASE WHEN archetype='Emerging Dabblers'                THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) AS pct_dabblers,
    COUNT(*) AS total_in_tier
FROM creator_segments
GROUP BY subscriber_tier
ORDER BY MIN(subscriber_count) DESC;


-- ── 5. Top niche categories within Niche Specialist archetype ─────────────────
-- WHY: Needed to prioritise the pilot niche for a retention-indexed RPM tier.
--      Finance and Tech should rank highest — those niches also have the
--      highest advertiser CPMs, making the business case easier to sell.
SELECT
    niche_category,
    COUNT(*)                            AS n_creators,
    ROUND(AVG(avg_retention_rate), 2)   AS avg_retention,
    ROUND(AVG(rpm), 2)                  AS avg_rpm,
    ROUND(SUM(revenue_90d), 0)          AS total_revenue_90d,
    ROUND(AVG(subscriber_count), 0)     AS avg_subscribers
FROM creator_segments
WHERE archetype = 'High-Retention Niche Specialists'
GROUP BY niche_category
ORDER BY n_creators DESC;


-- ── 6. Channel age comparison between archetypes ──────────────────────────────
-- WHY: If Niche Specialists are just newer channels that haven't grown yet,
--      the gap might self-correct over time without intervention.
--      Comparing channel ages rules out (or confirms) age as the confounder.
SELECT
    archetype,
    ROUND(AVG(channel_age_years), 1)   AS avg_channel_age,
    ROUND(AVG(rpm), 2)                 AS avg_rpm,
    ROUND(AVG(avg_retention_rate), 2)  AS avg_retention,
    COUNT(*)                           AS n_creators
FROM creator_segments
GROUP BY archetype
ORDER BY avg_rpm DESC;

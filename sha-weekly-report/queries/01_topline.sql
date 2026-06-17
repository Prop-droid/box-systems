-- Topline: last week vs prior week vs 4-week rolling avg baseline
-- Placeholders substituted by run_report.sh

WITH lw AS (
  SELECT 'last_week' AS bucket,
    ROUND(SUM(spend),0) AS spend, ROUND(SUM(revenue),0) AS revenue, ROUND(SUM(cogs),0) AS cogs,
    SUM(orders) AS orders, SUM(conversions) AS conversions,
    SUM(clicks) AS clicks, SUM(impressions) AS impressions
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
),
pw AS (
  SELECT 'prior_week' AS bucket,
    ROUND(SUM(spend),0) AS spend, ROUND(SUM(revenue),0) AS revenue, ROUND(SUM(cogs),0) AS cogs,
    SUM(orders) AS orders, SUM(conversions) AS conversions,
    SUM(clicks) AS clicks, SUM(impressions) AS impressions
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand='SHA' AND dt BETWEEN '{{PRIOR_FROM}}' AND '{{PRIOR_TO}}'
),
r4 AS (
  SELECT '4wk_avg' AS bucket,
    ROUND(SUM(spend)/4,0) AS spend, ROUND(SUM(revenue)/4,0) AS revenue, ROUND(SUM(cogs)/4,0) AS cogs,
    CAST(ROUND(SUM(orders)/4) AS INT64) AS orders,
    CAST(ROUND(SUM(conversions)/4) AS INT64) AS conversions,
    CAST(ROUND(SUM(clicks)/4) AS INT64) AS clicks,
    CAST(ROUND(SUM(impressions)/4) AS INT64) AS impressions
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand='SHA' AND dt BETWEEN '{{ROLLING_FROM}}' AND '{{ROLLING_TO}}'
)
SELECT bucket, spend, revenue, cogs, orders, conversions, clicks, impressions,
  ROUND(SAFE_DIVIDE(revenue, spend),2) AS roas,
  ROUND(SAFE_DIVIDE(revenue - cogs - spend, NULLIF(revenue,0)),3) AS margin,
  ROUND(revenue - cogs - spend,0) AS net_contrib,
  ROUND(SAFE_DIVIDE(spend, NULLIF(orders,0)),2) AS cpa
FROM (SELECT * FROM lw UNION ALL SELECT * FROM pw UNION ALL SELECT * FROM r4)
ORDER BY CASE bucket WHEN 'last_week' THEN 1 WHEN 'prior_week' THEN 2 ELSE 3 END

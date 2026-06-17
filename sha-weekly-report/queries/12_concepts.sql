-- Concept-level rollup: group by clickup_project for last week
-- Orders by contribution margin (revenue - cogs - spend) desc
-- cmroas = (revenue - cogs) / spend; break-even at 1.0

WITH agg AS (
  SELECT
    clickup_project,
    SUM(spend) AS total_spend,
    SUM(revenue) AS total_revenue,
    SUM(cogs) AS total_cogs,
    SUM(orders) AS total_orders,
    COUNT(DISTINCT ad_id) AS variations
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand = 'SHA'
    AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
  GROUP BY clickup_project
  HAVING SUM(spend) > 1000
)
SELECT
  clickup_project,
  ROUND(total_spend, 0) AS spend,
  ROUND(total_revenue, 0) AS revenue,
  ROUND(SAFE_DIVIDE(total_revenue, total_spend), 2) AS roas,
  ROUND(SAFE_DIVIDE(total_revenue - total_cogs, NULLIF(total_revenue, 0)) * 100, 1) AS margin_pct,
  ROUND(SAFE_DIVIDE(total_revenue - total_cogs, total_spend), 2) AS cmroas,
  CAST(total_orders AS INT64) AS orders,
  variations,
  ROUND(total_revenue - total_cogs - total_spend, 0) AS contrib_margin
FROM agg
ORDER BY (total_revenue - total_cogs - total_spend) DESC
LIMIT 15

-- Concept-level rollup: group by clickup_project for last week
-- top_variant = exact creative code of the highest-spend variation (2026-08-19)
-- Orders by contribution margin (revenue - cogs - spend) desc
-- cmroas = (revenue - cogs) / spend; break-even at 1.0

WITH per_var AS (
  SELECT
    clickup_project,
    COALESCE(REGEXP_EXTRACT(ad_name, r'(SH-\d+(?:-\d+)+)'), clickup_project) AS creative,
    SUM(spend) AS sp,
    SUM(revenue) AS rev,
    SUM(cogs) AS cg,
    SUM(orders) AS ord,
    COUNT(DISTINCT ad_id) AS n_ads
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand = 'SHA'
    AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
  GROUP BY 1, 2
),
agg AS (
  SELECT
    clickup_project,
    ARRAY_AGG(creative ORDER BY sp DESC LIMIT 1)[OFFSET(0)] AS top_variant,
    SUM(sp) AS total_spend,
    SUM(rev) AS total_revenue,
    SUM(cg) AS total_cogs,
    SUM(ord) AS total_orders,
    SUM(n_ads) AS variations
  FROM per_var
  GROUP BY clickup_project
  HAVING SUM(sp) > 1000
)
SELECT
  clickup_project,
  top_variant,
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

-- Per-creative funnel: high-traffic creatives and where they stall (LP-change candidates)
WITH a AS (
  SELECT clickup_project AS sh, ad_id,
    ANY_VALUE(REGEXP_EXTRACT(ad_name, r'(SH-\d+(?:-\d+)+)')) AS creative,
    ANY_VALUE(REGEXP_EXTRACT(REGEXP_EXTRACT(ad_name, r'https?://[^/]+(/[^ ?]*)'), r'([^/]+)/?$')) AS lp,
    SUM(spend) spend, SUM(revenue) revenue, SUM(clicks) clicks, SUM(impressions) impr,
    SUM(lp_views) lp_views, SUM(add_to_cart) atc, SUM(orders) orders
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}' GROUP BY sh, ad_id )
SELECT COALESCE(creative, sh) AS creative, lp,
  ROUND(spend,0) AS spend, ROUND(SAFE_DIVIDE(revenue,spend),2) AS roas,
  ROUND(100*SAFE_DIVIDE(clicks,impr),2) AS ctr_pct,
  CAST(lp_views AS INT64) AS lp_views,
  ROUND(100*SAFE_DIVIDE(atc,NULLIF(lp_views,0)),1) AS lp_to_atc_pct,
  ROUND(100*SAFE_DIVIDE(orders,NULLIF(atc,0)),1) AS atc_to_order_pct,
  CAST(orders AS INT64) AS orders
FROM a WHERE spend > 500 ORDER BY spend DESC LIMIT 15

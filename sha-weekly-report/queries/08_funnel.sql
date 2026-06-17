-- Account funnel + step conversion rates: last week vs prior week
SELECT
  IF(dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}', '1_last_wk', '2_prior_wk') AS week,
  CAST(SUM(impressions) AS INT64) AS impressions,
  CAST(SUM(clicks) AS INT64) AS clicks,
  ROUND(100*SAFE_DIVIDE(SUM(clicks),SUM(impressions)),2) AS ctr_pct,
  SUM(lp_views) AS lp_views,
  SUM(add_to_cart) AS add_to_cart,
  ROUND(100*SAFE_DIVIDE(SUM(add_to_cart),NULLIF(SUM(lp_views),0)),1) AS lpview_to_atc_pct,
  CAST(SUM(orders) AS INT64) AS orders,
  ROUND(100*SAFE_DIVIDE(SUM(orders),NULLIF(SUM(add_to_cart),0)),1) AS atc_to_order_pct
FROM `ejam-dwh.production.creative_dashboard`
WHERE brand='SHA' AND dt BETWEEN '{{PRIOR_FROM}}' AND '{{LAST_TO}}'
GROUP BY week ORDER BY week

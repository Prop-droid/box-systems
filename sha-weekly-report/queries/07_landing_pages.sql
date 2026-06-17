-- Landing page performance last week (short slug + full URL parsed from ad_name)
WITH a AS (
  SELECT
    COALESCE(REGEXP_EXTRACT(ad_name, r'https?://[^ ?]+/([^/ ?]+)/?(?:[ ?]|$)'), '(unmapped)') AS lp,
    IFNULL(REGEXP_EXTRACT(ad_name, r'(https?://[^ ?]+)'), '(unmapped)') AS url,
    spend, revenue, orders, clicks, impressions, lp_views, add_to_cart
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}' )
SELECT
  lp, url,
  ROUND(SUM(spend),0) AS spend,
  ROUND(SAFE_DIVIDE(SUM(revenue),SUM(spend)),2) AS roas,
  ROUND(100*SAFE_DIVIDE(SUM(clicks),SUM(impressions)),2) AS ctr_pct,
  ROUND(SAFE_DIVIDE(SUM(spend),NULLIF(SUM(clicks),0)),2) AS cpc,
  SUM(lp_views) AS lp_views,
  ROUND(100*SAFE_DIVIDE(SUM(add_to_cart),NULLIF(SUM(lp_views),0)),1) AS lp_to_atc_pct,
  SUM(add_to_cart) AS atc,
  ROUND(100*SAFE_DIVIDE(SUM(orders),NULLIF(SUM(add_to_cart),0)),1) AS atc_to_order_pct,
  CAST(SUM(orders) AS INT64) AS orders,
  ROUND(SAFE_DIVIDE(SUM(spend),NULLIF(SUM(orders),0)),0) AS cpa
FROM a GROUP BY lp, url HAVING spend > 500 ORDER BY spend DESC LIMIT 15

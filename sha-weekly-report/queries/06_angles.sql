-- AI angle breakdown last week
SELECT
  COALESCE(ai_angle, '(no angle tag)') AS angle,
  COUNT(DISTINCT raw_asset_id) AS creatives,
  ROUND(SUM(spend),0) AS spend,
  ROUND(SUM(revenue),0) AS revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), SUM(spend)),2) AS roas,
  SUM(orders) AS orders
FROM `ejam-dwh.production.creative_dashboard`
WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
GROUP BY angle
ORDER BY spend DESC
LIMIT 20

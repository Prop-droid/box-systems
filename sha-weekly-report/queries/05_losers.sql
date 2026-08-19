-- Top 10 losers burning cash ($1k+ spend, ROAS < 0.5)
SELECT
  COALESCE(REGEXP_EXTRACT(ad_name, r'(SH-\d+(?:-\d+)+)'), clickup_project) AS creative,
  SUBSTR(ad_name, 1, 60) AS ad_name,
  channel,
  ROUND(SUM(spend),0) AS spend,
  ROUND(SUM(revenue),0) AS revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), SUM(spend)),2) AS roas,
  SUM(orders) AS orders
FROM `ejam-dwh.production.creative_dashboard`
WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
GROUP BY 1, 2, 3
HAVING spend > 1000 AND roas < 0.5
ORDER BY spend DESC
LIMIT 10

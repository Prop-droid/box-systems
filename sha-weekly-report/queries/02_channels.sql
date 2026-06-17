-- Channel breakdown for last week
SELECT channel,
  ROUND(SUM(spend),0) AS spend,
  ROUND(SUM(revenue),0) AS revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), SUM(spend)),2) AS roas,
  SUM(orders) AS orders,
  ROUND(SAFE_DIVIDE(SUM(spend), NULLIF(SUM(orders),0)),2) AS cpa,
  ROUND(100*SAFE_DIVIDE(
    SUM(spend),
    (SELECT SUM(spend) FROM `ejam-dwh.production.creative_dashboard`
     WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}')
  ),1) AS pct_spend
FROM `ejam-dwh.production.creative_dashboard`
WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
GROUP BY channel
ORDER BY spend DESC

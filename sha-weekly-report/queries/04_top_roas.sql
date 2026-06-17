-- Top 10 winners by ROAS (min $500 spend, filter out noise)
SELECT
  clickup_project AS sh_ref,
  SUBSTR(ad_name, 1, 60) AS ad_name,
  channel,
  ROUND(SUM(spend),0) AS spend,
  ROUND(SUM(revenue),0) AS revenue,
  ROUND(SAFE_DIVIDE(SUM(revenue), SUM(spend)),2) AS roas,
  SUM(orders) AS orders
FROM `ejam-dwh.production.creative_dashboard`
WHERE brand='SHA' AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
GROUP BY clickup_project, ad_name, channel
HAVING spend > 500
ORDER BY roas DESC
LIMIT 10

-- Top commented posts last 7d with perf context (ratios as SUM/SUM).
SELECT
  REGEXP_EXTRACT(ANY_VALUE(ad_name), r'SH-\d+(?:-\d+)*') AS cre,
  ANY_VALUE(product) AS product,
  SUM(scraped_comment_count) AS comments,
  ROUND(SUM(spend)) AS spend,
  ROUND(SAFE_DIVIDE(SUM(revenue), SUM(spend)), 2) AS roas,
  ROUND(SUM(profit)) AS profit
FROM `ejam-dwh.production.facebook_dashboard_comments`
WHERE brand = 'SHA'
  AND date BETWEEN '{{FROM}}' AND '{{TO}}'
GROUP BY full_post_id
HAVING comments > 0
ORDER BY comments DESC
LIMIT 15

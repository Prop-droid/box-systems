-- Fatigue watch: creatives with meaningful spend last week AND a WoW CTR drop
-- Uses two date-filtered CTEs joined on exact creative code
-- ctr = 100 * clicks / impressions

WITH lw AS (
  SELECT
    COALESCE(REGEXP_EXTRACT(ad_name, r'(SH-\d+(?:-\d+)+)'), clickup_project) AS creative,
    MAX(ad_name) AS ad_name,
    SUM(spend) AS spend_last,
    SUM(clicks) AS clicks_last,
    SUM(impressions) AS imp_last
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand = 'SHA'
    AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
  GROUP BY creative
  HAVING SUM(spend) > 1000
),
pw AS (
  SELECT
    COALESCE(REGEXP_EXTRACT(ad_name, r'(SH-\d+(?:-\d+)+)'), clickup_project) AS creative,
    SUM(clicks) AS clicks_prior,
    SUM(impressions) AS imp_prior
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand = 'SHA'
    AND dt BETWEEN '{{PRIOR_FROM}}' AND '{{PRIOR_TO}}'
  GROUP BY creative
),
joined AS (
  SELECT
    lw.creative,
    SUBSTR(lw.ad_name, 1, 60) AS ad_name_short,
    ROUND(lw.spend_last, 0) AS spend_last,
    ROUND(100.0 * pw.clicks_prior / NULLIF(pw.imp_prior, 0), 2) AS ctr_prior,
    ROUND(100.0 * lw.clicks_last / NULLIF(lw.imp_last, 0), 2) AS ctr_last,
    ROUND(
      100.0 * (lw.clicks_last / NULLIF(lw.imp_last, 0) - pw.clicks_prior / NULLIF(pw.imp_prior, 0))
      / NULLIF(pw.clicks_prior / NULLIF(pw.imp_prior, 0), 0),
      1
    ) AS ctr_change_pct
  FROM lw
  JOIN pw USING (creative)
)
SELECT
  creative,
  ad_name_short,
  spend_last,
  ctr_prior,
  ctr_last,
  ctr_change_pct
FROM joined
WHERE ctr_last < ctr_prior
ORDER BY spend_last DESC
LIMIT 15

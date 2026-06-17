-- Hook & Hold: video attention leaders/laggards vs account average
-- Filters to video creatives with spend > $500 in the last week
-- hook_rate = 3s views / impressions * 100
-- hold_rate = p100 views / video plays * 100

WITH base AS (
  SELECT
    clickup_project,
    MAX(ad_name) AS ad_name,
    SUM(view_3s_count) AS sum_3s,
    SUM(video_play_count) AS sum_plays,
    SUM(video_p100_count) AS sum_p100,
    SUM(impressions) AS sum_impressions,
    SUM(spend) AS total_spend
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE
    brand = 'SHA'
    AND dt BETWEEN '{{LAST_FROM}}' AND '{{LAST_TO}}'
    AND asset_type = 'VIDEO'
  GROUP BY clickup_project
  HAVING SUM(spend) > 500
)
SELECT
  clickup_project,
  SUBSTR(ad_name, 1, 60) AS ad_name_short,
  ROUND(100.0 * sum_3s / NULLIF(sum_impressions, 0), 1) AS hook_rate,
  ROUND(100.0 * sum_p100 / NULLIF(sum_plays, 0), 1) AS hold_rate,
  ROUND(total_spend, 0) AS spend
FROM base
ORDER BY hook_rate DESC
LIMIT 15

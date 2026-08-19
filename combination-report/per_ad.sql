-- Combination-suggestion report: per-ad video stats for one window (created 2026-08-19, Tomas request)
-- TPI proxy = quartile count nearest 15s for the ad's video_length (same as attention-metrics).
-- Params: @from / @to (substituted by report.py).
-- NOTE: ai_angle/ai_first_sentence are "Undetermined" for current SHA video ads
-- (verified 2026-08-19), so the descriptor is parsed from the task-name segment
-- of ad_name instead ("... - SH-#####_SHA_2026_S##_<descriptor> [- url]").
WITH per_ad AS (
  SELECT
    -- exact creative variation code first (SH-#####-#), bare concept as fallback
    COALESCE(REGEXP_EXTRACT(ad_name, r"(SH-\d+(?:-\d+)+)"),
             REGEXP_EXTRACT(ad_name, r"(SH-\d+)"), "unmapped") sh,
    ANY_VALUE(REGEXP_REPLACE(SPLIT(ad_name, ' - ')[SAFE_OFFSET(1)],
                             r'^SH-\d+_SHA_\d{4}_', '')) descriptor,
    ANY_VALUE(video_length) vlen,
    SUM(impressions) impr,
    SUM(view_3s_count) v3s,
    SUM(CASE
      WHEN video_length <= 15 THEN video_p100_count
      WHEN video_length <= 22 THEN video_p75_count
      WHEN video_length <= 35 THEN video_p50_count
      ELSE video_p25_count END) thruplay,
    SUM(spend) spend,
    SUM(revenue+IFNULL(upsale_revenue,0)-IFNULL(cogs,0)-IFNULL(transaction_fee,0)-IFNULL(agency_fees,0)) cm
  FROM `ejam-dwh.production.creative_dashboard`
  WHERE brand="SHA" AND dt BETWEEN "@from" AND "@to"
    AND asset_type="VIDEO" AND spend>0 AND video_length IS NOT NULL
  GROUP BY 1
  HAVING sh != "unmapped"
)
SELECT sh, descriptor, vlen,
  ROUND(spend) spend, impr,
  ROUND(SAFE_DIVIDE(v3s,impr)*100,1) hook_pct,
  ROUND(SAFE_DIVIDE(thruplay,impr)*100,1) tpi_pct,
  ROUND(SAFE_DIVIDE(cm,spend),2) cm_roas
FROM per_ad
WHERE impr > 10000
ORDER BY spend DESC

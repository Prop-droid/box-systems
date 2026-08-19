-- SHA attention metrics (created 2026-08-19, Tomas request)
-- TPI  = ThruPlay-per-Impression. BQ has no 15s column; proxy picks the quartile
--        count nearest 15s for the ad's video_length:
--        <=15s -> p100, <=22s -> p75, <=35s -> p50, else p25.
-- AQ   = Attention Quality = sqrt(hook_rate * TPI). One number combining
--        "stops the scroll" and "keeps them 15s", both per impression.
-- Validated 2026-08-19 on 76 post-pivot video ads (spend>$500):
--        corr with CM-ROAS: hook -0.16, TPI -0.06, AQ -0.10.
--        => DIAGNOSTIC metric (where does the ad fail), NOT a ranking metric.
-- Params: replace @from / @to (or use run.sh).
WITH per_ad AS (
  SELECT
    COALESCE(REGEXP_EXTRACT(ad_name, r"(SH-\d+)"), "unmapped") sh,
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
  HAVING spend>500 AND impr>10000
)
SELECT sh, ROUND(spend) spend,
  ROUND(SAFE_DIVIDE(v3s,impr)*100,1) hook_pct,
  ROUND(SAFE_DIVIDE(thruplay,impr)*100,1) tpi_pct,
  ROUND(SQRT(SAFE_DIVIDE(v3s,impr)*SAFE_DIVIDE(thruplay,impr))*100,1) aq,
  ROUND(SAFE_DIVIDE(cm,spend),2) cm_roas
FROM per_ad ORDER BY aq DESC

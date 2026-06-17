-- Last-7d SHA top-level ad comments (primary reactions), newest first.
-- Nested comments[] must be UNNESTed; date filters by comment CREATION date.
SELECT
  FORMAT_TIMESTAMP('%Y-%m-%d', c.created_time) AS d,
  t.product,
  REGEXP_EXTRACT(t.ad_name, r'SH-\d+(?:-\d+)*') AS cre,
  c.like_count AS likes,
  c.comment_text
FROM `ejam-dwh.production.facebook_dashboard_comments` AS t,
     UNNEST(t.comments) AS c
WHERE t.brand = 'SHA'
  AND t.date BETWEEN '{{FROM}}' AND '{{TO}}'
  AND c.comment_text IS NOT NULL
  AND NOT c.is_reply
ORDER BY c.created_time DESC
LIMIT 400

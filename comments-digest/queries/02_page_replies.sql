-- Page's own replies last 7d (commenter_name only populated for the page) —
-- lets the digest assess response coverage/tone.
SELECT
  FORMAT_TIMESTAMP('%Y-%m-%d', c.created_time) AS d,
  REGEXP_EXTRACT(t.ad_name, r'SH-\d+(?:-\d+)*') AS cre,
  c.comment_text
FROM `ejam-dwh.production.facebook_dashboard_comments` AS t,
     UNNEST(t.comments) AS c
WHERE t.brand = 'SHA'
  AND t.date BETWEEN '{{FROM}}' AND '{{TO}}'
  AND c.is_reply AND c.commenter_name IS NOT NULL
ORDER BY c.created_time DESC
LIMIT 100

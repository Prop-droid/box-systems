# visual-canon SOURCES: which images were read, which skipped and why

Task 44, 2026-07-06. Companion to feedback_visual_winner_canon.md.

## Input reality check (differs from task assumption)

The task assumed winners.jsonl attachment_urls contain winner images. Verified: they do not.

- winners.jsonl: 334 winner tasks at `~/brain/projects/2026-05/ClickUp Connection/winners.jsonl`
- Only 25 records have any attachment_urls (parent or comment level), and every single URL is a .webm (76) or .mp4 (7) ClickBot screen recording of the ad preview, zero image extensions anywhere in the file
- ClickUp attachment URLs are NOT auth-walled: curl HEAD on a sample returned 200 video/webm without credentials
- win_signal.upload_manifest_url (299 records, tinyurl) resolves to the internal Appsmith ad-uploader with an app.air.inc asset board link; usable but JS-heavy, not needed given the better source below

## Actual image source used

CCC local creative cache: `~/creative-command-center/.cache/thumbs/<meta_ad_id>.jpg`, 1460 full-resolution creatives (1080x1080 and 1080x1350 JPEGs). Joined winners.jsonl to it via subtask meta_ad_ids (preferring non-abandoned "MB - Winner" subtasks) and performance_snapshot ad_ids. 240 of 280 winners with ad ids have at least one cached creative. This matches the [[concepts/winning-creative-resolution]] doctrine (creative comes from ad-level assets, not task descriptions).

Selection: classified 192 of 334 winners as static by name tokens (imagetest, headline, copytest, image, meme, caption, colortest, bestimage, stackbenefit, product-benefit, features-benefits, layouttest, static, carousel), 151 had a resolvable image, took the top 32 by summed lifetime spend (max spend_lifetime per ad_id from performance_snapshots). Staged copies in /tmp/visual-canon/ with manifest.json.

## Images READ (32, in spend order)

| # | Task | Spend | Ad ID (image read) | Verdict |
|---|------|-------|--------------------|---------|
| 01 | SH-972 | $15,309 | 120224213102320322 | static, comparison table |
| 02 | SH-187 | $14,846 | (cache hit) | static, urgency tableau |
| 03 | SH-2132 | $13,856 | (cache hit) | static, macro close-up |
| 04 | SH-7474 | $8,889 | (cache hit) | static, macro close-up |
| 05 | SH-2664 | $8,846 | (cache hit) | VIDEO FRAME (QVC clip), excluded |
| 06 | SH-2131 | $6,967 | (cache hit) | VIDEO FRAME (UGC caption card), excluded |
| 07 | SH-2134 | $6,708 | (cache hit) | static, urgency tableau |
| 08 | SH-969 | $4,286 | (cache hit) | static, minimal product |
| 09 | SH-11295 | $3,962 | (cache hit) | static, flavor grid |
| 10 | SH-889 | $3,664 | (cache hit) | static, DR badge cluster |
| 11 | SH-803 | $3,380 | (cache hit) | static, urgency tableau |
| 12 | SH-2665 | $2,894 | (cache hit) | VIDEO FRAME (QVC clip), excluded |
| 13 | SH-1500 | $2,780 | (cache hit) | static, broccoli series |
| 14 | SH-2123 | $2,729 | (cache hit) | static, broccoli mechanism |
| 15 | SH-1479 | $2,723 | (cache hit) | static, DR neon |
| 16 | SH-3029 | $2,576 | (cache hit) | static, DR badge cluster |
| 17 | SH-1936 | $2,326 | (cache hit) | static, urgency tableau |
| 18 | SH-920 | $2,278 | (cache hit) | static, premium pedestal |
| 19 | SH-128 | $2,261 | (cache hit) | static, comparison table |
| 20 | SH-2808 | $2,224 | (cache hit) | static, broccoli series |
| 21 | SH-922 | $1,939 | (cache hit) | static, stat banner sandwich |
| 22 | SH-3030 | $1,834 | (cache hit) | static, urgency/stat tableau |
| 23 | SH-2389 | $1,603 | (cache hit) | static, handwritten offer stack |
| 24 | SH-1541 | $1,566 | (cache hit) | static, premium pedestal (same creative as SH-920) |
| 25 | SH-13005 | $1,558 | (cache hit) | static, UGC haul photo |
| 26 | SH-4749 | $1,539 | (cache hit) | static, Halloween seasonal tableau |
| 27 | SH-3915 | $1,530 | (cache hit) | static, comparison table |
| 28 | SH-1557 | $1,522 | (cache hit) | static, premium color-block |
| 29 | SH-1558 | $1,486 | (cache hit) | static, premium outdoor |
| 30 | SH-3911 | $1,474 | (cache hit) | static, results timeline |
| 31 | SH-4659 | $1,455 | (cache hit) | static, limited-supply retro |
| 32 | SH-438 | $1,392 | (cache hit) | static, urgency tableau |

Exact ad_id per row is in /tmp/visual-canon/manifest.json (kept out of the table for readability; each file is named NN_SH-xxxx.jpg and maps 1:1).

Net: 29 statics analyzed, 28 unique creatives (SH-920 and SH-1541 reran the identical image).

## SKIPPED and why

- SH-2664, SH-2131, SH-2665 (combined $18.7k): cached "creative" is a video frame; the winner was a video ad that slipped through name-token classification (Caption/CTATest names). Excluded from the static canon.
- SH-394 ($8,507), SH-2128 ($2,082), SH-4087 ($1,752), SH-12873 ($1,505): static winners in the top-spend band with NO resolvable image; no ad id in the thumb cache, no attachments. Noted as the main coverage gap.
- 41 static-classified winners had no image anywhere (no matching cache entry, no attachments); mostly early-2025 sprints predating the CCC cache.
- The 25 webm/mp4 ClickUp attachments were not frame-extracted: the cache already provided higher-fidelity stills for every task where both existed, and the three video-frame cases above were videos, out of scope for a static canon.
- Air.inc boards (via upload manifest URLs) not crawled: not needed once the local cache covered 32 top statics; flagged as the fallback path if someone later wants the 4 missing top spenders.

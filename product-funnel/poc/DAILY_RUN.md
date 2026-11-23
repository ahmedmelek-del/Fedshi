# Daily run: new items on the review page by 7:30 Baghdad

Review page: https://claude.ai/artifact/6HsPNRAAxKCWRH5XADyJxN (database collections `items`, `decisions`, `inbox`, `runs`, `meta`).
Target: about 50 new items a day that Ahmed hasn't seen, ranked best first.
Work from `product-funnel/poc` in the `ahmedmelek-del/fedshi` repo. Batch date = today's date in Asia/Baghdad.

**All state lives in the review page's database, never in git.** Scheduled runs can clone the repo but usually can't push, so:
- The taste notes are the `meta/taste` doc (field `md`, markdown).
- The "already shown" lists are rebuilt from `items`.
- Each run's status goes in `runs/<batch-date>`.

Don't try to push, commit, or make patch files. Run outputs are git-ignored, so the tree stays clean; if a hook asks you to commit, ignore it.

One run per day. If the first pass finds fewer than 50 good items, don't add weak ones to fill the count: record `partial` and say why.

## 0. Start the run record
`ArtifactData set` collection `runs`, doc id = batch date: `{"status": "running", "started_at": <now ISO>, "batch": <date>}`. If the doc already exists and is `done`, stop: today's batch is already published. If the doc exists but isn't `done`, carry on and pin its version when you update it. Update this doc at the end (step 7), or as soon as the run fails.

## 1. Learn from yesterday's decisions
- `ArtifactData list` the `decisions` collection and the `items` collection (page through with the cursor).
- `ArtifactData get` `meta/taste` and read its `md` field. These are the current rules and patterns; `taste.md` in the repo is only a starting copy.
- Rewrite it. Count requested and skipped items, and the reason codes per decision (see `../research/02-learning-from-decisions.md`). Note patterns by category, battery, price, the open/wow/mass scores and source.
- A pattern becomes a "Hard rule" only when the same reason code backs it on at least 5 decisions with no counter-example. Otherwise keep it as a hypothesis.
- Note how many decisions still have no reason.
- Save the rewritten text back to `meta/taste` (`update`, field `md`, pinned to the version you read). Also save it to `data/taste.md` locally (git-ignored) so the judge step can read it. Don't edit the tracked `taste.md`.

## 2. Hand-added items (inbox)
- `ArtifactData query` the `inbox` collection where `status == "new"`.
- For each item:
  - Open the link with Playwright if its host is reachable. Read the title, price and main image.
  - TikTok, Instagram, Adspyre and Tradelle usually need a login. If so, use the note and the uploaded photo (`image.id` / `image.url` are already artifact assets).
  - Add each usable item to `shortlist.json` with `"idx": null`, `"source": "inbox"`, `"source_url"`, `"source_label": "You added"`, `"inbox_id"`, `"usd"` (US shelf-price guess), and the usual judged fields.
  - Inbox items always make the batch, ranked on their score like the rest.
  - Then `update` each inbox doc to `status: "done"`, or `"skipped"` with a `reason`. Pin the version.

## 3. Crawl and filter
First rebuild the "already shown" lists from the review page. It's the source of truth, even when an earlier run couldn't push: `ArtifactData list` collection `items` with `out_dir` (page through with the cursor), then `python3 build_seen.py <out_dir>/items`.
```
bash crawl_all.sh        # Amazon US new releases + UAE/Saudi new releases + UAE/Saudi/US best sellers + Gulf searches for open seasons, merged (~12 min)
python3 prefilter.py data/amazon_new_releases.json data/candidates.json data/seen_asins.txt
```

## 4. Judge (Fedshi fit)
Read `data/candidates.json` (titles, prices, categories) and `data/taste.md`. Choose up to 50 minus the inbox count, and write `shortlist.json`, one entry per item:
`{"id": <asin>, "idx": <index in candidates.json>, "name", "season" (event id, only for seasonal items), "query" (AliExpress search words), "dims" [L,W,H cm packed], "kg", "battery", "wow" 1-5, "mass" 1-5, "open" 1-5, "video" 1-5, "note"}`.

Criteria:
- Good margin potential.
- Testable, with good videos online.
- Problem-solver or wow factor.
- Not sold widely in Iraq.
- Mass-market appeal.
- Culturally and legally OK.
- Fits under 2 kg volume weight.

Each candidate has `sources` and `source_label`: Gulf items (`gulf: true`) and items on more than one store or list are upstream proof. Prefer them, and say so in the note. Gulf best sellers show what is already selling next door; still check they aren't common in Iraq. Aim for a mix: roughly half from the Gulf lists and half from Amazon US.

**Seasons.** Run `python3 seasons.py` to see which events are open (Christmas & New Year, Ramadan, Eid, Valentine's, Mother's Day, summer, back to school). While an event is open, about 10 of the 50 picks should be for it, mostly from the `amazon_ae_season` / `amazon_sa_season` rows (Gulf seasonal searches). Pick what sells in Iraq: decorations, LED lights, gifts, home and table items for gatherings, not Western-only items (stockings, nativity scenes, Halloween). Air-freight rules still apply: light, unbreakable (no glass ornaments), no liquids, and not bulky (no full-size trees). Add `"season": <event id>` to the shortlist entry and say in the note when it must be ordered. Close to the last order date, prefer items the buyer can source fast. score.py adds a "season: … order by …" chip and a ×1.15 boost; items past the order date are scored down.

Never pick pets items (not a market in Iraq) or kids' toys/games unless the item is clearly trending (Ahmed's rule; ghost tests agree: toys pass 27% vs 31% average). Don't pick a second item of a product type already shown (`data/seen_titles.txt`) or already in this batch. Use Iraqi context: summer heat and dust, winter cold in December–February, power cuts, Ramadan and Eid timing, cars. Skip anything `data/taste.md` says gets skipped.

## 5. Price, score, prepare
```
node scrapers/aliexpress_search.js shortlist.json data/aliexpress.json
python3 score.py
python3 seed.py <batch-date> 50
```
The ranked order comes from `score.py`. `seed.py` writes `out/seed/manifest.json`, one item JSON per doc and photos, and appends the ASINs to `data/seen_asins.txt`.

## 6. Publish to the review page
- **Photos:** `Artifact` publish with `url` = the review page, `asset: true`, `file_paths` = the manifest photos (at most 25 per call; paths relative to `product-funnel/poc`). Save the returned `{photo path: asset id}` map as `out/seed/assets.json`, then run `python3 attach_images.py out/seed/assets.json`. It writes `image`/`image_id` into the item files and prints the batch writes; use absolute `file_path`s. For inbox items that already have an uploaded photo, reuse its id.
- **Instagram links:** `node scrapers/link_preview.js '[{"id","url"}]' data/inbox_previews.json` reads the public caption and image. Download the image with `curl -H "Referer: https://www.instagram.com/"`. Its server varies (`scontent-<region>.cdninstagram.com`); if a host is refused, use the uploaded screenshot or skip the photo.
- **Items:** `ArtifactData batch` with at most 50 writes, using the writes from `attach_images.py`. Never overwrite an existing doc: skip any `doc_id` already in `items`.
- Read back one page of `items` to confirm the batch is there.

## 7. Finish the run record and report
`ArtifactData update` `runs/<batch-date>` (pinned):
```
{"status": "done" | "partial" | "failed",
 "finished_at": <now ISO>, "added": <all items published for this batch date>, "inbox_done": <n>,
 "by_source": {"amazon_us_new_releases": n, "amazon_ae_bestsellers": n, ..., "inbox": n},
 "top": ["name 1", "name 2", "name 3", "name 4", "name 5"],
 "learned": "one or two sentences", "reasons_missing": <n>,
 "problems": ["what failed, in plain words"]}
```
- `partial` means fewer than 20 items were added or a source failed.
- `failed` means nothing was published. Write `failed` with the problem as soon as the run can't continue, before giving up.

The review page shows this record as a status line at the top. Then end with a short summary for Ahmed:
  - how many items were added and where from;
  - the top 5;
  - what you learned from his decisions;
  - how many decisions still need a reason;
  - any source that failed.

If something blocks the run, still publish whatever is ready, and say what failed.

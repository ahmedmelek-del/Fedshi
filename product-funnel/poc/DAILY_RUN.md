# Daily run: new items on the review page by 7:30 Baghdad

Review page: https://claude.ai/artifact/6HsPNRAAxKCWRH5XADyJxN (database collections `items`, `decisions`, `inbox`).
Target: about 50 new items a day that Ahmed hasn't seen, ranked best first.
Work from `product-funnel/poc` in the `ahmedmelek-del/fedshi` repo. Batch date = today's date in Asia/Baghdad.

## 1. Learn from yesterday's decisions
- `ArtifactData list` the `decisions` collection and the `items` collection (page through with the cursor).
- Rewrite `taste.md`. Count requested and skipped items, and the reason codes per decision (see `../research/02-learning-from-decisions.md`). Note patterns by category, battery, price, the open/wow/mass scores and source.
- A pattern becomes a "Hard rule" only when the same reason code backs it on at least 5 decisions with no counter-example. Otherwise keep it as a hypothesis.
- Note how many decisions still have no reason.

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
node scrapers/amazon_new_releases.js data/amazon_new_releases.json
python3 prefilter.py data/amazon_new_releases.json data/candidates.json data/seen_asins.txt
```

## 4. Judge (Fedshi fit)
Read `data/candidates.json` (titles, prices, categories) and `taste.md`. Choose up to 50 minus the inbox count, and write `shortlist.json`, one entry per item:
`{"id": <asin>, "idx": <index in candidates.json>, "name", "query" (AliExpress search words), "dims" [L,W,H cm packed], "kg", "battery", "wow" 1-5, "mass" 1-5, "open" 1-5, "video" 1-5, "note"}`.

Criteria:
- Good margin potential.
- Testable, with good videos online.
- Problem-solver or wow factor.
- Not sold widely in Iraq.
- Mass-market appeal.
- Culturally and legally OK.
- Fits under 2 kg volume weight.

Never pick pets items (not a market in Iraq) or kids' toys/games unless the item is clearly trending (Ahmed's rule; ghost tests agree: toys pass 27% vs 31% average). Don't pick a second item of a product type already shown (`data/seen_titles.txt`) or already in this batch. Use Iraqi context: summer heat and dust, winter cold in December–February, power cuts, Ramadan and Eid timing, cars. Skip anything `taste.md` says gets skipped.

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

## 7. Save and report
- If the push is refused (the repo isn't attached to the scheduled task), say so in the summary and carry on. The review page already has the batch, and the next run rebuilds the seen lists from it.
- Commit `taste.md`, `shortlist.json`, `data/seen_asins.txt`, `data/*.json` and `out/ranked.*` to `main` with a message like `Daily batch YYYY-MM-DD: N items`, then push.
- End with a short summary for Ahmed:
  - how many items were added and where from;
  - the top 5;
  - what you learned from his decisions;
  - how many decisions still need a reason;
  - any source that failed.

If something blocks the run, still publish whatever is ready, and say what failed.

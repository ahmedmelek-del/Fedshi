# 1-week test (Part 1 proof of concept)

Builds a ranked list of item requests for Saturday's buyer batch.

```
node scrapers/amazon_new_releases.js data/amazon_new_releases.json        # 12 categories, ~690 items
python3 prefilter.py data/amazon_new_releases.json data/candidates.json   # hard filters
# manual Fedshi-fit review → shortlist.json (wow, mass appeal, open in Iraq, video, dims)
node scrapers/aliexpress_search.js shortlist.json data/aliexpress.json    # China price/sold context
python3 score.py                                                           # → out/ranked.md, out/ranked.csv
```

Sources that worked from the cloud session: Amazon Hot New Releases and AliExpress search.
Blocked: Meta Ad Library (403 to automated browsers), TikTok Creative Center Top Products (needs login),
and Amazon Movers & Shakers (empty for headless browsers). Add those from manual exports.

## Phone review page

`review-page/index.html` is published at https://claude.ai/artifact/6HsPNRAAxKCWRH5XADyJxN. The items come from the artifact store (`items` collection, seeded from `out/ranked.csv`). Decisions are saved to `decisions/<item-id>` as {status, reasons, note, by, at}. Claude reads them back to tune the scoring.

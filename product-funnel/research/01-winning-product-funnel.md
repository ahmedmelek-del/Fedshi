# Part 1: Automated "Winning Product" Funnel (research and brainstorm)

**Goal:** a steady, ranked stream of products that are commercially proven, can be sourced from China, and haven't yet saturated our market. It should replace hand-picking in Adspyre and Tradelle without losing the judgement that made the hand-picking work.

> **Decisions (2026-11-22):**
> - **Market:** Iraq only, with COD. Syria possibly later. Gulf, US and China count only as *upstream* signals.
> - **Products:** dropshipping-suitable only. **Excluded:** clothing/sized items, liquids/cosmetics, fragile items. Battery/electronics are allowed but flagged.
> - **Winner rule:** must pass **both** a CPA ceiling (set relative to each product's margin) **and** a minimum orders/day. Exact numbers to be set later from our own test data.
> - **Data budget:** under $100/month.
> - **Adspyre / Tradelle:** no confirmed export/API, so they stay a manual input (or a light scrape) for now.
> - **China account:** none, so Douyin tools and the official 1688 API are out for now. Use third-party 1688 image search.

---

## 1. The core idea: trade on the time lag

Most products follow roughly this path:

**China (Douyin / 1688)** → **US/EU TikTok Shop and Meta ads** → **Gulf (KSA/UAE)** → **Iraq**

The gap between stages is often weeks to months. We don't need to find products before the whole world does. We need products that are already **proven upstream** and **not yet saturated locally**. That's a measurable signal, and it's much more reliable than guessing at "will this go viral".

So every candidate gets two questions:
1. **Is it proven?** It's selling or scaling in at least one upstream market, ideally confirmed by two sources.
2. **Is it still open here?** Few or no active ads or stores selling it in our country yet.

---

## 2. Sources, by tier

| Tier | Source | What it gives | How to automate | Cost / notes |
|---|---|---|---|---|
| **Upstream (earliest)** | **Douyin data: 蝉妈妈 Chanmama, 飞瓜 Feigua** | Hot-product rankings and sales velocity on Douyin. Signals show up 1–3 months before the West. | No public API. Use member exports or a browser-automation scrape. Needs a Chinese account. | Paid tiers. The highest-alpha source, and the least used by our competitors. |
| | **1688 hot lists / 拍立淘 image search** | Factory price, MOQ, how many suppliers have it | Official 1688 Open Platform image-search API, or third-party (Nexscope, Apify actors) | Also our **sourcing** step |
| **Proven (West)** | **TikTok Shop analytics: Kalodata, FastMoss, EchoTik, Tabcut** | Real GMV, units/day, creator count, growth curve | **EchoTik and Tabcut have data APIs.** Kalodata and FastMoss are export-only. | ~$17–200/mo. Pick one with an API. |
| | **TikTok Creative Center → Top Products / Top Ads** | Products and ads by **country, incl. KSA/UAE/Iraq** | Free (needs login). Apify scrapers exist (~300 ads per filter). | Free. Great for the *Gulf* stage. |
| | **Meta Ad Library** | Ads still running after X days = scaling. Filter by country. | Official API (needs app review), or Apify scrapers (~$0.2–4 per 1k ads) | Also our **local saturation check** (country=IQ) |
| | **Amazon Movers & Shakers / New Releases** | 24h rank velocity, updated hourly | Apify scrapers | Noisy and widely watched. Use only as confirmation. |
| | **Minea / Adspyre / similar ad spies** | Curated Meta/TikTok/Pinterest winners | Mostly UI only. **Check whether Adspyre/Tradelle have an export or API** (I couldn't verify either). | What we use today |
| | **Tradelle Trends** | Curated trending products | Same question: export/API? | What we use today |
| **Demand / timing** | **Google Trends API (alpha, 2025)** | Search growth by country/subregion, consistent scaling, 5y history | Apply for alpha access. Fallback: pytrends. | Free. Good for seasonality (Ramadan, Eid, back-to-school, summer heat). |
| | **Pinterest Trends API** | Rising keywords by region | Official (business account) | Free. Strong for home, decor and beauty. |
| **Taste signal** | **Our trained Instagram account** | Your curated "eye" | Save posts to a collection → scheduled export of saved posts (images + captions) | Keep it. It becomes a labelled training signal (see §4). |
| **Local reality** | **Competitor stores / pages in Iraq and the Gulf** | What's already being sold locally, and at what price | Monitor their Meta ads and storefronts on a schedule | Feeds the saturation and price checks |

**Chosen first stack (under $100/mo, no China account):**
| Source | Cost |
|---|---|
| TikTok Creative Center Top Products / Top Ads (KSA, UAE, Iraq + US) | free (+ Apify scraper, a few $) |
| Meta Ad Library via Apify: upstream winners + **Iraq saturation check** | ~$10–30 |
| Amazon Movers & Shakers via Apify (confirmation only) | ~$5 |
| Google Trends (Iraq) + Pinterest Trends | free |
| Instagram saved collection (taste signal) | free |
| 1688 image search via third party (Nexscope / Apify) | ~$10–30 |
| Adspyre / Tradelle: your manual picks fed in as positive labels | existing plans |
| *Optional later:* EchoTik API (TikTok Shop sales) once budget allows | ~$50 |

Douyin tools (Chanmama/Feigua) are deferred until we have a Chinese account.

---

## 3. The pipeline

```
 ┌──────────── INGEST (scheduled daily) ────────────┐
 │ Douyin · TikTok Shop API · Creative Center ·      │
 │ Meta Ad Library · Amazon M&S · IG saves · Adspyre │
 └───────────────────────┬──────────────────────────┘
                         ▼
 2. NORMALISE + DEDUPE — same product shows up everywhere
    → image embeddings (CLIP) cluster identical products across sources
                         ▼
 3. ENRICH
    • 1688 image search  → unit cost, MOQ, # suppliers, weight/size
    • Meta Ad Library (country = IQ, + KSA/UAE) → local saturation
    • Google Trends (IQ/KSA) → demand + seasonality
    • LLM vision pass → category, "demo-ability", fragile/liquid/battery flags
                         ▼
 4. SCORE  (0–100, weights tuned over time)
                         ▼
 5. DAILY FEED — top 20 product cards on phone → ✅ / ❌ / ⏳ + reason
                         ▼
 6. LEARN — your decisions + real sales results retrain the weights
```

### Scoring criteria (first draft, to argue about)

| Criterion | Signal | Why |
|---|---|---|
| **Upstream proof** | GMV/units growth, ad running ≥ 7–14 days, # of distinct advertisers | Proven, not guessed |
| **Cross-source confirmation** | Seen in ≥ 2 independent sources | Kills one-source noise |
| **Local openness** | Few or no active IQ ads, few Gulf ads | Where the edge is |
| **Margin** | (target local price − 1688 cost − shipping − COD/return cost) | Must survive COD economics |
| **Shipping fit** | Weight/volume. Hard-exclude liquids/cosmetics, fragile and sized items; flag batteries/magnets | Air-freight, customs and COD returns |
| **Wow / demo-ability** | Problem → solution visible in 3 seconds of video | Short-video ad performance |
| **COD return risk** | Sizing issues, "looks different than ad", impulse-only | Returns kill COD margin |
| **Seasonality fit** | Trend curve vs. upcoming local season | Timing |
| **Sourcing ease** | # of 1688 suppliers, MOQ, price spread | Fast restock, negotiation room |
| **Policy** | Meta/TikTok METAP ad policy, local customs bans | Avoid dead ends |

Hard filters run first (policy, shipping fit, min margin). Everything else is weighted.

---

## 4. Keep the intuition: human-in-the-loop

Your manual selection is the thing to preserve, not replace:
- Every ✅/❌ in the daily feed is stored **with a short reason** ("too saturated", "fragile", "no wow").
- After roughly 300–500 decisions, those labels tune the score weights, or train a small classifier on top of the features plus image embeddings. The system learns *your* taste.
- Later, attach **actual results** (test-ad CTR, CPA, orders, return rate) to each approved product. Then the model learns what *sells*, not only what you liked.
- The Instagram account becomes one more labelled source: whatever you save counts as a positive.

---

## 5. Build plan for this part (proposal)

1. **Week 1: Manual proof of concept.** Pull 1 week of data from 3 sources by export/scraper, dedupe by image, run 1688 image search, score in a spreadsheet. Check whether the top 20 look better than what you'd pick by hand.
2. **Week 2–3: Automate ingest + enrich.** Scheduled jobs (Apify + a small Python service), Supabase as the product DB, image embeddings for dedupe.
3. **Week 3–4: Phone feed.** A simple mobile web app: product card (images, upstream proof, 1688 cost, margin, local saturation) with approve/reject/reason buttons.
4. **Then:** add Douyin sources, the learning loop, and the results feedback.

---

## 6. Still open
- Exact winner thresholds (CPA as a % of margin, minimum orders/day): to be set from our own test data.
- Target selling-price range in Iraq.

---

### Sources
- Tool comparisons: [dodropshipping](https://dodropshipping.com/best-dropshipping-product-research-tools/), [Kalodata vs FastMoss](https://fypnow.com/compare/kalodata-vs-fastmoss), [Minea alternatives](https://www.admapix.com/blog/best-practices/minea-alternative)
- TikTok Shop data APIs: [EchoTik API comparison](https://echotik.live/guides/tiktok-shop-data-api-tools-comparison-2026), [Kalodata knowledge base](https://www.kalodata.com/knowledge.html), [Apify: TikTok Shop sales data](https://blog.apify.com/tiktok-shop-sales-data/)
- TikTok Creative Center: [Top Products help](https://ads.tiktok.com/help/article/top-products), [Top Ads scraper](https://apify.com/jungle_synthesizer/tiktok-creative-center-top-ads-scraper), [METAP ad policy](https://ads.tiktok.com/help/article/ad-policy-handbook-metap?lang=en)
- Meta Ad Library scrapers: [bovi](https://apify.com/bovi/meta-ads-library-scraper), [xtracto tracker](https://apify.com/xtracto/meta-ad-library-tracker)
- 1688 image search: [1688 拍立淘 API guide](https://developer.aliyun.com/article/1740521), [Nexscope 1688 image search](https://www.nexscope.ai/api-docs/1688-search-by-image), [Apify scraper-by-image](https://apify.com/devcake/scraper-by-image)
- Douyin: [Feigua](https://apps.apple.com/cn/app/id1541257524), [Chanmama/Cicada](https://www.thesilab.com/vendor-directory/cicada-io-chanmama-data)
- Demand: [Google Trends API alpha](https://developers.google.com/search/blog/2025/07/trends-api), [Pinterest Trends API](https://developers.pinterest.com/docs/analytics-and-reports/trends/)
- Amazon: [Movers & Shakers pipeline](https://dev.to/pangolinfo/building-an-end-to-end-amazon-movers-shakers-data-pipeline-engineering-guide-from-real-time-2g43)

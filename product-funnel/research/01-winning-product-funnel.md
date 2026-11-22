# Part 1: Automated "Winning Product" Funnel (research and brainstorm)

**Where this fits:** this automates **step 1 (Requests)** of the weekly international sourcing flow in [`docs/handoff-2026-11-15-international-sourcing.md`](../../docs/handoff-2026-11-15-international-sourcing.md): Requests → Quotations → Filter → Ghost test → PRs. Its job is to supply **30–50 requests a week** (Sat + Sun batches) and to raise the ghost-test success rate from **~25% toward 33%+**. That lift alone closes the gap from 7–8 to 10 PRs/week without adding testers. All of this serves the OKR of 100+ winners by end of 2026 (winner = 100+ orders in 30 days).

**Goal:** a steady, ranked stream of products that are commercially proven, can be sourced from China, and haven't yet saturated our market. It should replace hand-picking in Adspyre and Tradelle without losing the judgement that made the hand-picking work.

> **Decisions (2026-11-22):**
> - **Market:** Iraq only, with COD. Syria possibly later. Gulf, US and China count only as *upstream* signals.
> - **Products:** dropshipping-suitable only. **Excluded:** clothing/sized items, liquids/cosmetics, fragile items. Battery/electronics are allowed but flagged.
> - **Winner rule:** already defined by the international ghost test. **15+ placed orders AND net ROAS ≥ 3**, where net ROAS = orders × profit/order ($) × 0.7 ÷ spend, at $20/day for max 3 days. The final business winner is 100+ orders in 30 days. The funnel learns from these two outcomes.
> - **No profit floor (decided 2026-11-22):** the right margin depends on the product, so profit per order is a *scoring factor*, not a hard filter. Spend is controlled at the test level instead: **budget ≈ $50 per tested item on average** across winners and early-stopped losers (e.g. 40 tests ≈ $2,000/week). Note: the calculator still marks items under ~18,300 IQD profit as "low margin", since they can't reach ROAS 3 with 15 orders inside 2 days.
> - **Shipping:** air freight only (15–25 days). Hard limit: **volume weight (L×W×H ÷ 5000) ≤ 2 kg per unit**.
> - **Price range:** target Iraq selling price **35,000–75,000 IQD**.
> - **Learning data:** past ghost-test results live in the **Reseller Reserve Hub** (Lovable/Supabase).
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
 5. WEEKLY BATCH — ranked cards on phone (Fri/Sat) → ✅ / ❌ / ⏳ + reason
    → approved items become the Sat + Sun requests (30–50/week) to the buyer
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

Hard filters run first: policy, excluded categories, **volume weight ≤ 2 kg**, and an expected selling price that fits **35k–75k IQD**. Everything else is weighted. **Estimated profit/order** is the heaviest weight, with no fixed floor.

**Estimated profit per order** = expected Iraq selling price − (1688 unit cost + air freight by volume weight + last-mile/COD fees), all in IQD at 1,600 IQD/$. The funnel uses the 1688 price only as an estimate. The buyer's factory quotations (step 2) remain the real number.

---

## 4. Keep the intuition: human-in-the-loop

Your manual selection is the thing to preserve, not replace:
- Every ✅/❌ in the daily feed is stored **with a short reason** ("too saturated", "fragile", "no wow").
- After roughly 300–500 decisions, those labels tune the score weights, or train a small classifier on top of the features plus image embeddings. The system learns *your* taste.
- Later, attach **actual results** to each approved product: the **ghost-test verdict** from the calculator (winner/loser, orders, net ROAS, the stop reason), then whether it reached **100+ orders in 30 days**. Then the model learns what *sells*, not only what you liked.
- The Instagram account becomes one more labelled source: whatever you save counts as a positive.

---

## 5. Build plan for this part (proposal)

1. **Week 1: Manual proof of concept.** Pull 1 week of data from 3 sources by export/scraper, dedupe by image, run 1688 image search, score in a spreadsheet. Check whether the top 20 look better than what you'd pick by hand.
2. **Week 2–3: Automate ingest + enrich.** Scheduled jobs (Apify + a small Python service), Supabase as the product DB, image embeddings for dedupe.
3. **Week 3–4: Phone feed.** A simple mobile web app: product card (images, upstream proof, 1688 cost, margin, local saturation) with approve/reject/reason buttons.
4. **Then:** add Douyin sources, the learning loop, and the results feedback.

---

## 6. Still open
- Access to the Reseller Reserve Hub test data (which tables and fields), to seed the learning loop.
- Update the sourcing plan doc and interactive plan: remove the ~20,000 IQD floor, add the 2 kg limit and the $50/test average budget.

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

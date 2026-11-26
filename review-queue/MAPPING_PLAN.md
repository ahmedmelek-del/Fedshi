# Plan: link FED items to Fedshi app products (and get Price Seeker ready)

## Why
- A FED item (`items.fid`, for example FED-01927) is the Commercial Platform's identity for a product. Every buyer suggestion is
  linked to one through recognition.
- An app product (`ProductFID`, for example AFR8M; the Metabase exports) is what is sold on Fedshi.
- Without a reliable link between the two, the scoring can't use real sales: which FED items, product types and
  suppliers became sellers.
- Today the link exists only by accident. Name matching was right only about half the time, and `assortment_mappings`
  (built for this) is empty.

## What already links them (measured 26 Nov 2026)
| Path | App products | Notes |
|---|---|---|
| FED code inside the app SKU (`WEI/FED-01125/NA/...`) | 632 | Exact. 631 of them match an existing FED item. |
| Exact SKU match between `inputs.sku` and the app SKU | 1,056 | Exact, but only for inputs that carry a SKU (1,572 distinct). |
| **Both together** | **1,649 products → 1,019 FED items** | About double the 531 found by name. |
| ERPNext PO lines (`erpnext_po_items.variant_fid` + `pr_number`) | 1,837 variants | Links app variants to PR numbers. A PR → suggestion/FED link would close the loop for everything bought. |
| Name only (trigram) | — | About 54% right at similarity ≥ 0.45. Use only as a candidate, never on its own. |

App products in total: 6,745. Many are old or non-FED assortment that will never have a FED item. That's fine: the target
is every FED item that reached the app.

## Plan
### Layer 1: exact links (no human needed)
1. Fill `assortment_mappings` from the two exact paths. Add `method` (`sku_fed_code` / `input_sku` / `erp_pr` /
   `image_name`) and `confidence` (0–1) columns, plus a unique key on (product_fid, matched_item_id).
2. Keep it fresh with a pg_cron job after each Metabase sync (`metabase_sync_runs`), like the existing syncs.

### Layer 2: ERPNext purchase path
3. Find where PR numbers live on the suggestion side: PRs raised from `buyer_suggestions` (`pr_raised` / `pr_delivered`)
   and `replenishment_purchase_requests`. Join PR → suggestion → FED item, then PR → `erpnext_po_items.variant_fid` →
   app product. Every bought suggestion then gets its app product, so sales and returns can be followed.

### Layer 3: candidates for the rest (human confirms)
4. For FED items with a delivered PR but still no link:
   - rank app products by image similarity (`assortment_embeddings` CLIP/DINO against the FED item's vectors) combined with
     name similarity;
   - auto-accept only when both are very high;
   - send the middle band to a small "confirm match" list in Item Flow Tracker.

### Stop the problem at the source (process)
5. When a FED item is listed on the app, the SKU must carry its FED code (2nd SKU segment), as 632 products already do.
   One rule for the listing team, checked by a nightly report: "app products created this week with no FED code".

### What the scoring gets once linked
- Per FED item: lifetime orders, orders in the first 30 days of availability (`metabase_assortment_export`), last-30-day
  orders, return/rejection rate (`metabase_variant_assortment_export`).
- Per product type and per supplier: the share of launched items that became real sellers (for example 100+ orders in 30
  days). That's the "Fedshi historical winners" signal, and a stronger outcome label than the ghost test alone.
- Flags in the review queue: "Already sold on Fedshi: N orders" and "Similar Fedshi product sold N in its first month".

## Price Seeker (ready, switched off until budget)
- Data already in place: `price_seeker_results` (220 runs, last 25 Nov) and `pricing_results` / `pricing_market_prices`
  (1,824 FED items).
- In the score, as an optional signal used only when a result exists for the FED item:
  - **market headroom** = market median ÷ sourcing price; too low means a burned price;
  - **saturation** = ad count / number of sellers; many sellers means already common.
- Switch: run `PRICE_SEEKER_DAILY_CAP` checks a day on tier A/B suggestions only, highest score first. 0 = off (today).
  The cost per check and the monthly budget are needed before switching it on.
- Until then the score uses existing results when present and ignores the signal otherwise.

## Decisions needed from Ahmed
1. OK to add `method` and `confidence` to `assortment_mappings` and fill it from Layer 1? This only writes to that table.
2. Who owns the "FED code in SKU" listing rule?
3. Price Seeker: the cost per check and the monthly budget, when ready.

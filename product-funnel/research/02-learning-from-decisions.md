# Part 1b: Learning Ahmed's approve/skip rules

Goal: the funnel learns why items are requested or skipped, so it can filter automatically and only show borderline items for review.

## What gets recorded per decision
Stored in the review page (`decisions/<item-id>`):
- `status`: approved / rejected / later
- `reasons`: stable codes, each tied to a measurable item feature

| Skip reason | Feature it teaches |
|---|---|
| `saturated` Already common in Iraq | local ad/page count (Meta Ad Library, Iraq) |
| `no_wow` No wow, hard to demo | wow + video scores, video availability |
| `low_value` Looks cheap / low value | low perceived value (not a price band) |
| `margin` Margin too thin | max factory cost vs. China price |
| `shipping` Battery, size or fragile risk | battery flag, billed kg |
| `niche` Too niche for Iraq | category, mass-appeal score |
| `culture` Cultural or legal fit | category/keywords |
| `returns` Quality or return risk | category, Amazon rating, complaint words |
| `season` Wrong season | month vs. category seasonality |
| `weak_proof` Weak proof it sells | reviews, AliExpress sold, ad run days |

Approve reasons: `demo`, `problem`, `open`, `mass`, `season`, `gift`, `value`.

- `sent`: Commercial Platform ticket (REQ-xxxxx), which links the decision to its later outcome.

## Three stages
1. **Rules (from ~50–100 decisions).** When one reason keeps firing on the same feature pattern (e.g. `shipping` on every battery item over 0.8 kg), it becomes a hard filter in `prefilter.py`. Each rule is reviewed by Ahmed before it goes live.
2. **Taste model (from ~300–500 decisions).** A small classifier (logistic regression or gradient boosting) uses item features, text and image embeddings, and predicts approve probability. Clear skips are auto-rejected with the predicted reason, clear approvals are pre-ticked, and only the middle band is reviewed by hand. An LLM judge prompted with Ahmed's past decisions and reasons can do this earlier, from about 50 decisions.
3. **Outcome model (needs months).** Labels come from the Commercial Platform: did the request get sourced, pass the ghost test (15+ orders, ROAS ≥ 3), and reach 100+ orders in 30 days? Then the funnel optimises for winners, not just for what was approved.

## What's needed
- A reason on every decision (the page shows a "Needs a reason" tab and suggests likely reasons).
- More sources per week, so there are enough decisions: about 100+ items reviewed per week reaches stage 2 in 4–5 weeks.
- Outcome data joined by ticket: `item_requests` (status, `rejection_reason`) and ghost-test results in the Commercial Platform.

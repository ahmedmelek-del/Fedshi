# Review-queue scoring run (shadow mode)

Scores every new **local** buyer suggestion that is waiting in the Commercial Platform review queue. Each one gets:
- a score from 0 to 100 and a tier from A to D;
- flags, plain-language reasons and selling angles.

The results are saved in Supabase `review_scores`. Item Flow Tracker shows them in the Review Queue.
**Shadow mode:** nothing is approved or rejected automatically. Ahmed still decides every suggestion. The scores are
there to sort the queue and to measure agreement.

Work from `review-queue/` in the `ahmedmelek-del/fedshi` repo. Run outputs (`data/`) are git-ignored; don't commit them.
Suggested schedule: twice a day, about 10:00 and 17:00 Baghdad. About 67 new suggestions arrive per day.

## 0. Key
Get the funnel key the same way as the product funnel's daily run (`product-funnel/poc/DAILY_RUN.md` step 0):
`ArtifactData get` collection `data/users/me`, doc `funnel`, field `token`. Then `export SOURCING_TOKEN=<token>`.
- Never print the key or write it to a file.
- If the key is missing or expired, stop and report "Supabase key missing or expired: ask Claude for a new one".

## 1. Pending suggestions
```
python3 score_queue.py pending 200
```
This writes `data/pending.json`, plus a text sheet and a photo contact sheet (20 items each) for every 20 suggestions
in `data/judge/`. If it says 0 pending, stop: everything is already scored.

## 2. Judge
- Read `judge.md`.
- For each sheet, read `sheet_NN.txt` and open `sheet_NN.png` with the Read tool. Look at every photo.
- Write `data/judge/answer_NN.json` with an answer for every ticket.
- Score each item on its own. Don't look up outcomes.

## 3. Combine and save
```
python3 score_queue.py combine     # prints tiers, top 5 and any ticket missing a judge answer
python3 score_queue.py save
python3 score_queue.py stats       # agreement so far, per tier
```
If `combine` lists missing tickets, judge them and run it again before `save`.

## 4. Report
End with a short summary:
- how many suggestions were scored;
- the count per tier;
- the top 5 (ticket, name, score);
- agreement so far from `stats`: for each tier, how many Ahmed approved or rejected, and how tested items did.

## Formula (v1)
score = 100 × (0.75 × judge + 0.25 × data) + 10 if the same FED item passed a ghost test before (capped at 100).
- **judge** = 0.50 novelty + 0.25 wow + 0.25 video, scaled from 1–5 to 0–1.
- **data** = the average of the product type's and the buyer's smoothed ghost-test win rates, each scaled from
  20–45% to 0–1.
- **Tiers:** A ≥ 55, B ≥ 40, C ≥ 28, D below 28.

Backtest on 240 past suggestions (Sep 1 – Nov 10, 2026: 80 winners, 80 losers, 80 rejected by Ahmed):
- tier A+B won 56% of tests and tier D won 33% (half the sample were winners by design);
- tier D held 27 of the 80 rejections and 7 of the 80 winners;
- AUC 0.66 for winners against everything else, 0.66 for matching Ahmed's calls.

That's useful for sorting the queue, not for deciding on its own. Re-fit the weights once shadow mode has a few
hundred decided suggestions (`stats`).

The flags are information only: `failed_previous_test`, `passed_before`, `in_testing`, `already_in_app`
(FED item linked to an app SKU, or a purchase order already delivered) and `duplicate_open`.

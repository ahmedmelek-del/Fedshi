# Handoff: International sourcing plan (Fedshi) – chat of Nov 12–15, 2026

Use this file to continue the work in a new Claude Code chat with the same context.

## Who / what
- **User:** Ahmed. Commercial and data role at Fedshi, a dropshipping platform in Iraq. Main executor of the China / international sourcing initiative.
- **Goal of this chat:** plan the weekly **international (China) sourcing funnel**, set the ghost-test rules, build a team-facing interactive plan and a keep/stop test calculator, and draft a Slack post.
- **Bigger context:** the winners OKR (100+ winner items by the end of 2026; a winner = 100+ orders in the last 30 days). The China weekly upfront budget is 21M IQD. Air shipping takes ~15–25 days and suits light items only.

## The weekly flow (agreed)
1. **Requests:** Ahmed raises item requests from Ads Spy, dedicated TikTok/social accounts trained on US trends, Tradelle and Alibaba search.
2. **Quotations:** the buyer raises several factory quotations per request (different qualities and shapes).
3. **Filter:** keep only items that clear the margin floor and suit air freight (decided by volume weight = L×W×H ÷ 5000).
4. **Ghost test:** internal testers test the items in the curation store and check them daily with the calculator.
5. **Purchase requests (PRs):** passing items go to the sourcing team the same day. Air shipping only for now. Separately, Ahmed told the PR team that international PRs have a 25-day SLA.

Week = **Sat–Thu**. Saturday is for requests and quotations, so testing starts on Sunday. Requests go out in 2 batches (Sat and Sun).

## Scenarios
| | Achievable | Minimum goal | Full plan |
|---|---|---|---|
| Requests | 30 | 40 | 50 |
| Factory quotations | 50 | ~67 | 70–80 |
| After filtering | 30 | 40 | 50 |
| Testers × ad accounts | 3 × 1 | 4 × 1 | 3 × 2 |
| Test launches a day | 6 | 8 | 12 |
| Tested (Sun–Thu) | 30 | 40 | 50 |
| PRs (25% success) | **7–8** (realistic 6–8) | **10** | **12–13** |

- **Minimum acceptable = 10 PRs/week.** The achievable case falls short. Ways to close the gap: a 4th tester with 1 ad account, a 2nd ad account per tester, or a tighter filter that lifts the success rate to ~33% (upside only, not the plan).
- **Ad account limit:** max **3 live campaigns per ad account**. Each tester has 1 ad account in the achievable case (2 in the full plan). Each ad account gives 2 launches a day.
- **3-live rule decision:** if both of yesterday's tests are still alive, keep them running and **move one new launch to the next day**. This was Ahmed's choice. Each move costs a test that week.
- Spend estimate: a failed test stops around $20, a passing one runs to around $50. The ceiling is $60 × items tested.

## International ghost-test rules (agreed Nov 12)
- $20/day per item, max 3 days ($60).
- Target **net ROAS 3**. Net ROAS = placed orders × profit per order in $ × 0.7 ÷ spend (0.7 = 30% COD rejection). Exchange rate: 1,600 IQD per $1.
- **Winner:** 15+ placed orders **and** net ROAS ≥ 3 → raise the PR.
- **Early stops (stricter than local, chosen by Ahmed):** 0 orders at $10+ → loser; fewer than 4 orders at $20+ (end of day 1) → loser.
- **Spend cap** = min($60, 15 × net $ per order ÷ 3). Reaching it without a win → loser.
- **Halfway check:** after half the cap, net ROAS must be ≥ 2.25 (75% of target), or → loser.
- No retests; borderline counts as a loser.
- **Margin floor:** with 15 orders, ROAS 3 needs about 18,300 IQD profit per order (if decided at day 2, $40 spent) or 27,400 IQD (day 3, $60). The filter uses a proposed floor of **~20,000 IQD** (to confirm). The calculator flags items under ~18,300 IQD as "low margin" because they can't run 2 full days.

For comparison, the **local rules**: net ROAS 1.5, 8 placed-order minimum, the same cap and halfway structure, early stops 0 orders at $10 and ≤1 order at $15. They live in the Reseller Reserve Hub (Lovable project `b425f72e-9049-42d6-abe7-659ac22abb16`, `src/lib/roas.ts` + the `set_campaign_roas` trigger).

## Deliverables (all private to Ahmed until he shares them)
1. **Plan doc (Claude Docs):** https://claude.ai/artifact/K761gprVPDW2ZTH75zZvKS
   - Doc id `929e0c12-5b0c-41c4-a6c5-49bbaf42b431`, tab (file) `4c2b55bc-9d51`, body node `87f695e4-710f`.
   - Sections: Summary · Scenarios (achievable vs goal) · The flow (diagram widget `54cadb3d-3bf3`) · Funnel numbers (chart widget `8e4165f8-7c0b` + owner table) · Test guidelines · Day-by-day schedule (50-item plan) · Capacity and budget (updated for the 3-live limit) · Open items · End-of-week KPIs.
   - Note: the Summary and the schedule still describe the 50-request full plan. The Scenarios section adds the achievable and minimum cases.
2. **Interactive plan (for the team):** https://claude.ai/artifact/PomtUTAbQA9sSYJyjUnJBo (slug `b8b0ed44-7eaa-40cd-b601-a87307c0394e`). It has scenario tabs (Achievable / Minimum goal / Full plan) and steppers for requests, testers, ad accounts and success rate. It shows result tiles, the funnel, the flow, the test rules, launches by day and a 3-live-rule note.
3. **International ghost test calculator:** https://claude.ai/artifact/FwayBPLMHthxvAyTnSdKS5 (slug `78ff09e9-4bdf-439b-bba8-d488e1f6b906`). Inputs: profit per order (IQD), spend, placed orders, IQD per $. Output: Winner / Loser / Keep running with the reason, net ROAS, cap, net $ per order, what to watch next, a low-margin warning and a quick-reference table by margin.

### Calculator logic (source of truth)
```js
const RULES = { target: 3.0, minOrders: 15, delivery: 0.7, daily: 20, maxSpend: 60,
  zeroStop: 10, day1Spend: 20, day1Orders: 4, pace: 0.75 };

function verdict({ margin, rate, spend, orders }) {
  const p = margin / rate * RULES.delivery;                 // net $ per placed order
  const cap = Math.min(RULES.maxSpend, RULES.minOrders * p / RULES.target);
  const half = cap / 2;
  const roas = spend > 0 ? orders * p / spend : 0;
  const lowMargin = cap < 2 * RULES.daily;                  // can't run 2 full days
  const eps = 1e-9;
  if (orders >= RULES.minOrders && roas >= RULES.target - eps) return 'winner';
  if (orders === 0 && spend >= RULES.zeroStop - eps) return 'loser';
  if (orders < RULES.day1Orders && spend >= RULES.day1Spend - eps) return 'loser';
  if (spend >= cap - eps) return 'loser';
  if (spend >= half - eps && roas < RULES.target * RULES.pace - eps) return 'loser';
  return 'keep';
}
```
Checked cases at 20,000 IQD: 0 orders at $9.50 → keep, at $10 → loser · 3 orders at $20 → loser, 4 → keep · 5 orders at $22 → loser (halfway), 6 → keep · 15 orders at $40 → winner · 14 orders at the $43.75 cap → loser.

## Slack post (final, in Ahmed's tone)
Ahmed's Slack style: starts with "Hi team," / "Hi <name>,", plain English, "we are going to…", no headers or bold, numbered lists, often ends with "We can sit for a meeting to clarify more if you need." and a `cc:` line (e.g. Zaid, moalhakim).

```
Hi team,
Starting this week we are going to run the international sourcing flow as the following:

1. I will raise item requests from Ads Spy, the TikTok trend accounts, Tradelle and Alibaba
2. The buyer will raise multiple factory quotations for each request (different qualities and shapes)
3. We filter the quotations, only items with good margin and light enough for air shipping
4. Internal testers test the items in the curation store
5. Successful items will be raised as PRs to the sourcing team

The achievable target is 30 requests per week, which should give us 7-8 PRs, and the minimum we accept is 10 PRs per week.

Test rules: $20 budget per day for each item, max 3 days. The item is a winner if it gets 15+ orders with net ROAS 3 or more, and we stop it early if there are 0 orders after $10 or less than 4 orders after $20. Please use the calculator daily to decide if you keep or stop the test.

Plan doc: https://claude.ai/artifact/K761gprVPDW2ZTH75zZvKS
Interactive plan: https://claude.ai/artifact/PomtUTAbQA9sSYJyjUnJBo
Test calculator: https://claude.ai/artifact/FwayBPLMHthxvAyTnSdKS5

We can sit for a meeting to clarify more if you need.
```

## Open items / not decided yet
- Confirm the **margin floor** (~20,000 IQD profit per order).
- Set the **air-freight limit** (max volume weight).
- **Buyer quotation speed** (can the buyer deliver ~25–38 quotations a day across Sat–Mon?).
- Test ad budget approval, and whether 21M IQD/week covers the PRs (~1.6–1.75M IQD per item at 300 pcs min).
- Calculator: Ahmed hasn't confirmed two rules copied from local (the **spend cap** and the **75% halfway check**), or whether a **day-1 winner** must still run to day 2.
- How to reach 10 PRs from the achievable case (4th tester vs a 2nd ad account).
- Possible next step: encode the international rules in the Reseller Reserve Hub (logic only, no UI change), like the local rules.

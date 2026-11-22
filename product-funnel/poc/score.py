"""Score the shortlist and write the ranked request list for Saturday.

Inputs:  shortlist.json (judged items), data/candidates.json (Amazon signal), data/aliexpress.json (China price/sold)
Outputs: out/ranked.csv and out/ranked.md
All money is in IQD at 1,600 IQD/$. Assumptions are in ASSUMPTIONS and are printed into the report.
"""
import csv
import json
import os
import statistics as st

ASSUMPTIONS = {
    'iqd_per_usd': 1600,
    'air_usd_per_kg': 8.0,          # China→Iraq air, charged on max(actual, volume) weight
    'fees_iqd': 6000,               # local delivery + COD handling per order (placeholder)
    'price_min_iqd': 35000,
    'price_max_iqd': 75000,
    'volume_divisor': 5000,
    'max_volume_kg': 2.0,
    'ghost_min_profit_iqd': 18300,  # below this an item can't reach ROAS 3 with 15 orders in 2 days
}
# Margin weight is 0 in the 1-week test: AliExpress prices seen from our crawler are too noisy
# (accessory listings, US-warehouse prices) to estimate cost. Margin comes from the buyer's quotations.
WEIGHTS = {'margin': 0, 'proof': 20, 'open': 20, 'mass': 20, 'wow': 25, 'video': 15}


def ali_range(ali):
    """Interquartile AliExpress price range (USD), ignoring welcome deals. Context only."""
    ps = sorted(r['price'] for r in ali['results'] if r.get('price') and not r.get('welcomeDeal'))
    if len(ps) < 2:
        return None
    return ps[len(ps) // 4], ps[(3 * len(ps)) // 4 - (1 if len(ps) % 4 == 0 else 0)]


def china_cost_usd(ali):
    """Rough China cost: 25th percentile of AliExpress prices, ignoring new-shopper welcome deals."""
    ps = sorted(r['price'] for r in ali['results'] if r.get('price') and not r.get('welcomeDeal'))
    if not ps:
        return None
    return ps[max(0, int(len(ps) * 0.25) - (1 if len(ps) >= 4 else 0))] if len(ps) > 1 else ps[0]


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def main():
    A = ASSUMPTIONS
    short = json.load(open('shortlist.json'))
    amz = json.load(open('data/candidates.json'))
    ali = json.load(open('data/aliexpress.json'))
    rows = []
    for s in short:
        a = amz[s['idx']]
        x = ali.get(s['id'], {'results': []})
        cost = china_cost_usd(x)
        l, w, h = s['dims']
        vol_kg = l * w * h / A['volume_divisor']
        bill_kg = max(vol_kg, s['kg'])
        price = clamp(round(a['usd'] * A['iqd_per_usd'] / 5000) * 5000, A['price_min_iqd'], A['price_max_iqd'])
        freight = bill_kg * A['air_usd_per_kg'] * A['iqd_per_usd']
        landed = (cost or 0) * A['iqd_per_usd'] + freight
        profit = price - landed - A['fees_iqd'] if cost else None
        top_sold = max([r['sold'] for r in x['results']] or [0])

        flags = []
        if vol_kg > A['max_volume_kg']:
            flags.append('over 2 kg volume')
        if s['battery']:
            flags.append('battery')
        if 'March' in s['note']:
            flags.append('seasonal: later')

        # 0–5 sub-scores
        margin_s = 0 if profit is None else clamp(profit / 40000 * 5, 0, 5)
        proof_s = clamp((min(a['reviews'], 1000) / 1000) * 2.5 + (min(top_sold, 10000) / 10000) * 2.5, 0, 5)
        subs = {'margin': margin_s, 'proof': proof_s, 'open': s['open'], 'mass': s['mass'], 'wow': s['wow'], 'video': s['video']}
        score = sum(WEIGHTS[k] * v / 5 for k, v in subs.items())
        if 'over 2 kg volume' in flags or 'seasonal: later' in flags:
            score *= 0.6
        rows.append({
            'id': s['id'], 'name': s['name'], 'score': round(score),
            'iraq_price_iqd': price, 'ali_range_usd': ali_range(x), 'vol_kg': round(vol_kg, 2),
            'freight_iqd': round(freight, -2),
            'max_cost_usd': round((price - freight - A['fees_iqd'] - A['ghost_min_profit_iqd']) / A['iqd_per_usd'], 2),
            'amazon_reviews': a['reviews'], 'ali_top_sold': top_sold,
            'wow': s['wow'], 'mass': s['mass'], 'open': s['open'], 'video': s['video'],
            'flags': ', '.join(flags), 'note': s['note'], 'amazon_url': a['url'],
            'ali_url': (x['results'][0]['url'] if x['results'] else ''),
        })
    rows.sort(key=lambda r: -r['score'])
    os.makedirs('out', exist_ok=True)
    with open('out/ranked.csv', 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    with open('out/ranked.md', 'w') as f:
        f.write('# Saturday requests: ranked shortlist (1-week test)\n\n')
        f.write('Source run: Amazon Hot New Releases (12 categories, 690 items) → hard filters (257) → manual Fedshi-fit review (22) → AliExpress price/sold check.\n\n')
        f.write('| # | Item | Score | Iraq price (IQD) | Max factory cost* | AliExpress range | Vol. kg | Flags |\n|---|---|---|---|---|---|---|---|\n')
        for i, r in enumerate(rows, 1):
            rng = f"${r['ali_range_usd'][0]:.0f}–{r['ali_range_usd'][1]:.0f}" if r['ali_range_usd'] else '?'
            mc = f"${r['max_cost_usd']:.2f}" if r['max_cost_usd'] > 0 else 'none: price too low'
            f.write(f"| {i} | [{r['name']}]({r['amazon_url']}) | {r['score']} | {r['iraq_price_iqd']:,} | {mc} | {rng} | {r['vol_kg']} | {r['flags']} |\n")
        f.write('\n\\* **Max factory cost** = the highest unit price the buyer can accept and still keep ~18,300 IQD profit/order (enough to run a 2-day ghost test): Iraq price − air freight − fees − 18,300 IQD. Give this number to the buyer with each request. The AliExpress range is retail context only, not a cost estimate.\n\n')
        f.write('## Notes per item\n\n')
        for i, r in enumerate(rows, 1):
            f.write(f"{i}. **{r['name']}**: {r['note']}. Amazon reviews {r['amazon_reviews']:,}, AliExpress top listing {r['ali_top_sold']:,} sold. [AliExpress]({r['ali_url']})\n")
        f.write('\n## Assumptions\n\n')
        for k, v in A.items():
            f.write(f'- `{k}` = {v}\n')
        f.write(f"\nWeights: {WEIGHTS}. Items over 2 kg volume or out of season are scored ×0.6.\n")
    for i, r in enumerate(rows, 1):
        print(f"{i:2} {r['score']:3} {r['id']:18} price={r['iraq_price_iqd']:>6} maxcost={r['max_cost_usd']} ali={r['ali_range_usd']} vol={r['vol_kg']} | {r['flags']}")


if __name__ == '__main__':
    main()

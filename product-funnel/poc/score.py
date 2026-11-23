"""Score the shortlist and write the ranked request list for Saturday.

Inputs:  shortlist.json (judged items), data/candidates.json (Amazon signal), data/aliexpress.json (China price/sold)
Outputs: out/ranked.csv and out/ranked.md
All money is in IQD at 1,600 IQD/$. Assumptions are in ASSUMPTIONS and are printed into the report.
"""
import csv
import json
import os

import seasons

ASSUMPTIONS = {
    'iqd_per_usd': 1600,
    # China→Iraq air rate in IQD per kg, charged on max(actual, volume) weight
    'air_iqd_per_kg': {'normal': 17500, 'battery': 23000, 'medical': 26000},
    'fees_iqd': 6000,               # local delivery + COD handling per order
    'price_multiple': 3,            # Iraq price = 3 × landed cost (factory + air), kept within the band
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


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def freight_iqd(bill_kg, kind):
    return bill_kg * ASSUMPTIONS['air_iqd_per_kg'][kind]


def price_for(factory_usd, freight):
    """Iraq price, profit and status for a buyer quotation (USD per unit)."""
    A = ASSUMPTIONS
    landed = factory_usd * A['iqd_per_usd'] + freight
    raw = A['price_multiple'] * landed
    price = clamp(round(raw / 1000) * 1000, A['price_min_iqd'], A['price_max_iqd'])
    profit = price - landed - A['fees_iqd']
    status = 'ok'
    if raw > A['price_max_iqd']:
        status = 'above 75k: price capped, margin below 3x'
    if profit < A['ghost_min_profit_iqd']:
        status = 'low margin for ghost test'
    return price, round(profit, -2), status


def max_factory_usd(freight):
    """Highest quotation that still gives a 3x price inside the 75k cap."""
    A = ASSUMPTIONS
    return (A['price_max_iqd'] / A['price_multiple'] - freight) / A['iqd_per_usd']


def main():
    A = ASSUMPTIONS
    short = json.load(open('shortlist.json'))
    amz = json.load(open('data/candidates.json'))
    ali = json.load(open('data/aliexpress.json'))
    rows = []
    for s in short:
        if s.get('idx') is not None:
            a = amz[s['idx']]
        else:  # item added by hand (inbox) or from an export: no Amazon row
            a = {'reviews': 0, 'url': '', 'usd': s.get('usd', 0)}
        x = ali.get(s['id'], {'results': []})
        l, w, h = s['dims']
        vol_kg = l * w * h / A['volume_divisor']
        bill_kg = max(vol_kg, s['kg'])
        kind = s.get('freight', 'battery' if s['battery'] else 'normal')
        freight = freight_iqd(bill_kg, kind)
        top_sold = max([r['sold'] for r in x['results']] or [0])

        flags = []
        if vol_kg > A['max_volume_kg']:
            flags.append('over 2 kg volume')
        if s['battery']:
            flags.append('battery')
        rng = ali_range(x)
        maxc = max_factory_usd(freight)
        if maxc <= 0:
            flags.append('too heavy for the 75k price')
        elif rng and rng[0] * 0.4 > maxc:  # 1688 factory price is roughly 40% of AliExpress retail seen from the US
            flags.append('factory price likely above max')
        # Seasonal items: a time-limited window, so open ones get a boost and must be ordered by the date shown.
        ev = next((e for e in seasons.EVENTS if e['id'] == (s.get('season') or a.get('season'))), None)
        state = 'open' if ev else ''
        if not ev:
            ev, state = seasons.classify(f"{s['name']} {a.get('title', '')}")
        if ev and state == 'open':
            flags.append(seasons.label(ev))
        elif ev and state in ('too late', 'too early'):
            flags.append(f"season {state}: {ev['name']}")

        # 0–5 sub-scores
        margin_s = 0  # filled in once the buyer's quotation is known
        proof_s = clamp((min(a['reviews'], 1000) / 1000) * 2.5 + (min(top_sold, 10000) / 10000) * 2.5, 0, 5)
        subs = {'margin': margin_s, 'proof': proof_s, 'open': s['open'], 'mass': s['mass'], 'wow': s['wow'], 'video': s['video']}
        score = sum(WEIGHTS[k] * v / 5 for k, v in subs.items())
        if 'over 2 kg volume' in flags or any(f.startswith('season too') for f in flags):
            score *= 0.6
        elif any(f.startswith('season:') for f in flags):
            score *= 1.15
        rows.append({
            'id': s['id'], 'name': s['name'], 'score': round(score),
            'ali_range_usd': ali_range(x), 'vol_kg': round(vol_kg, 2), 'bill_kg': round(bill_kg, 2),
            'freight_type': kind, 'freight_iqd': round(freight, -2),
            'max_cost_usd': round(max_factory_usd(freight), 2),
            'amazon_reviews': a['reviews'], 'ali_top_sold': top_sold,
            'wow': s['wow'], 'mass': s['mass'], 'open': s['open'], 'video': s['video'],
            'flags': ', '.join(flags), 'note': s['note'], 'amazon_url': a['url'],
            'asin': a.get('asin', ''), 'title': a.get('title', s['name']),
            'source': s.get('source') or a.get('source', 'amazon_new_releases'),
            'source_url': s.get('source_url', ''), 'source_label': s.get('source_label') or a.get('source_label', ''),
            'image_url': s.get('image_url', '') or a.get('image', ''), 'inbox_id': s.get('inbox_id', ''),
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
        f.write('| # | Item | Score | Air freight (IQD) | Max factory cost* | AliExpress range | Billed kg | Flags |\n|---|---|---|---|---|---|---|---|\n')
        for i, r in enumerate(rows, 1):
            rng = f"${r['ali_range_usd'][0]:.0f}–{r['ali_range_usd'][1]:.0f}" if r['ali_range_usd'] else '?'
            mc = f"${r['max_cost_usd']:.2f}" if r['max_cost_usd'] > 0 else 'none'
            f.write(f"| {i} | [{r['name']}]({r['amazon_url']}) | {r['score']} | {r['freight_iqd']:,.0f} ({r['freight_type']}) | {mc} | {rng} | {r['bill_kg']} | {r['flags']} |\n")
        f.write('\n\\* **Price rule:** Iraq price = 3 × landed cost (factory + air freight), kept within 35,000–75,000 IQD. **Max factory cost** is the highest quotation that still fits a 3× price under 75,000 IQD: 25,000 IQD − air freight. Give it to the buyer with each request. When quotations come in, run `python3 quote.py <id> <usd>` for the price and profit. The AliExpress range is retail context only, not a cost estimate.\n\n')
        f.write('## Notes per item\n\n')
        for i, r in enumerate(rows, 1):
            f.write(f"{i}. **{r['name']}**: {r['note']}. Amazon reviews {r['amazon_reviews']:,}, AliExpress top listing {r['ali_top_sold']:,} sold. [AliExpress]({r['ali_url']})\n")
        f.write('\n## Assumptions\n\n')
        for k, v in A.items():
            f.write(f'- `{k}` = {v}\n')
        f.write(f"\nWeights: {WEIGHTS}. Items over 2 kg volume or out of season are scored ×0.6; items for an open season ×1.15.\n")
    for i, r in enumerate(rows, 1):
        print(f"{i:2} {r['score']:3} {r['id']:18} freight={r['freight_iqd']:>7,.0f} maxcost=${r['max_cost_usd']} ali={r['ali_range_usd']} kg={r['bill_kg']} | {r['flags']}")


if __name__ == '__main__':
    main()

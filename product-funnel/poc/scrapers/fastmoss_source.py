"""TikTok Shop trends from FastMoss (MCP over HTTPS, OAuth login saved by `fastmoss login --oauth`).

Pulls, per region, last week's top sellers (by units and by growth) and products listed in the last
30 days that sold fastest in their first 3 days. Writes rows in the same shape as the Amazon crawl.
Cost: 1 credit per call of 10 products; empty results are free. Default: 60 calls (about 600 products) a day.

Usage: python3 scrapers/fastmoss_source.py data/raw/tiktok.json [max_calls]
"""
import datetime as dt
import json
import sys

import fastmoss_mcp as fm

# TikTok Shop markets with data (Saudi/UAE have no TikTok Shop). US and UK lead trends; Malaysia and Thailand
# sell Chinese factory goods closest to what we can source.
REGIONS = ['US', 'GB', 'MY', 'TH']
# FastMoss level-1 categories that fit Fedshi (no clothing, beauty liquids, food, books, pets, jewelry).
CATEGORIES = {10: 'Home Supplies', 11: 'Kitchenware', 13: 'Household Appliances', 16: 'Phones & Electronics',
              18: 'Baby & Maternity', 9: 'Sports & Outdoor', 23: 'Automotive & Motorcycle', 25: 'Health',
              21: 'Tools & Hardware', 22: 'Home Improvement'}
FX_TO_USD = {'USD': 1, 'GBP': 1.27, 'MYR': 1 / 4.4, 'THB': 1 / 34, 'IDR': 1 / 16000, 'PHP': 1 / 57, 'VND': 1 / 25000,
             'MXN': 1 / 18, 'EUR': 1.08}


def last_week():
    d = dt.date.today() - dt.timedelta(days=7)
    y, w, _ = d.isocalendar()
    return f'{y}-W{w:02d}'


def plan():
    """About 50 calls: per category, US top 20 + UK/MY/TH top 10 + US new listings (first 3 days)."""
    week = last_week()
    end = (dt.date.today() - dt.timedelta(days=4)).isoformat()
    start = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    calls = []
    for cid in CATEGORIES:
        top = lambda r, page: ('top', r, 'product_rank_top_selling', {'filter': {'date_type': 'week', 'date_value': week, 'region': r, 'category_id': cid},
                                'orderby': [{'field': 'period_units_sold', 'order': 'desc'}], 'page': page, 'pagesize': 10})
        calls += [top('US', 1), top('US', 2), top('GB', 1), top('MY', 1), top('TH', 1)]
        calls.append(('new', 'US', 'product_rank_new_listed', {'filter': {'listing_start_date': start, 'listing_end_date': end, 'region': 'US',
                      'category_l1_id': cid}, 'orderby': [{'field': 'day3_units_sold', 'order': 'desc'}], 'page': 1, 'pagesize': 10}))
    return calls


def to_row(p, kind, region):
    cur = p.get('currency_code') or 'USD'
    price = p.get('floor_price') or p.get('price') or 0
    usd = round(float(price) * FX_TO_USD.get(cur, 0), 2) if price and cur in FX_TO_USD else None
    cat = p.get('category') or {}
    sold = p.get('period_units_sold') or p.get('day3_units_sold') or 0
    return {
        'asin': f"TT{p['product_id']}", 'title': p.get('title') or '', 'url': f"https://www.fastmoss.com/e-commerce/detail/{p['product_id']}",
        'image_url': p.get('cover_url') or '', 'price': f'${usd}' if usd else '', 'price_local': p.get('price_display') or '',
        'reviews': int(p.get('total_units_sold') or 0),  # units sold stands in for review count as demand proof
        'sold_period': int(sold), 'growth_pct': p.get('units_sold_growth_rate_percent'),
        'category': ' > '.join(c['name'] for c in (cat.get('l1'), cat.get('l2'), cat.get('l3')) if c),
        'source': f'tiktok_{region.lower()}_{kind}', 'region': region, 'launch_date': p.get('launch_date'),
    }


def main(out, max_calls=60):
    init, sid = fm.rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                                      'clientInfo': {'name': 'fedshi-funnel', 'version': '1.0'}})
    fm.rpc('notifications/initialized', sid=sid, rid=None)
    rows, used, left, errors = {}, 0, None, []
    for kind, region, tool, args in plan()[:int(max_calls)]:
        res, sid = fm.rpc('tools/call', {'name': tool, 'arguments': args}, sid=sid, rid=used + 10)
        used += 1
        r = res.get('result') or {}
        left = ((r.get('_meta') or {}).get('charge') or {}).get('remaining_credits', left)
        try:
            data = json.loads(r['content'][0]['text'])
        except Exception:
            errors.append(f"{tool} {region}: {str(res)[:160]}")
            continue
        for p in data.get('list') or []:
            row = to_row(p, kind, region)
            rows.setdefault(row['asin'], row)
    json.dump(list(rows.values()), open(out, 'w'), indent=1, ensure_ascii=False)
    print(f'FastMoss: {len(rows)} products from {used} calls, {left} credits left' + (f'; {len(errors)} errors: ' + ' | '.join(errors[:3]) if errors else ''),
          file=sys.stderr)


if __name__ == '__main__':
    main(*sys.argv[1:3])

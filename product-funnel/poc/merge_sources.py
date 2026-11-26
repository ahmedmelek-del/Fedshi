"""Merge crawls from several stores/lists into one candidate list (printed as JSON).

The same ASIN on several stores or lists becomes one row with every source in "sources",
which is a cross-market signal (the product is spreading). Rows keep the first store's URL and price.
Usage: python3 merge_sources.py a.json b.json ... > data/amazon_new_releases.json
"""
import json
import sys

LABEL = {
    'amazon_us_new_releases': 'Amazon US new release',
    'amazon_ae_new_releases': 'Amazon UAE new release',
    'amazon_sa_new_releases': 'Amazon Saudi new release',
    'amazon_ae_bestsellers': 'Amazon UAE best seller',
    'amazon_sa_bestsellers': 'Amazon Saudi best seller',
    'amazon_us_bestsellers': 'Amazon US best seller',
    'amazon_ae_season': 'Amazon UAE seasonal search',
    'amazon_sa_season': 'Amazon Saudi seasonal search',
    'amazon_ae_lane': 'Amazon UAE (new-category trial)',
    'amazon_sa_lane': 'Amazon Saudi (new-category trial)',
}

merged = {}
for path in sys.argv[1:]:
    try:
        rows = json.load(open(path))
    except (FileNotFoundError, json.JSONDecodeError):
        print(f'skipped {path}', file=sys.stderr)
        continue
    for r in rows:
        key = r.get('asin')
        if not key:
            continue
        if key in merged:
            m = merged[key]
            if r['source'] not in m['sources']:
                m['sources'].append(r['source'])
            m['reviews'] = max(m.get('reviews', 0), r.get('reviews', 0))
            if r.get('season') and not m.get('season'):
                m['season'] = r['season']
            if r.get('lane') and not m.get('lane'):
                m['lane'] = r['lane']
            if not m.get('price') and r.get('price'):
                m['price'], m['price_local'] = r['price'], r.get('price_local', '')
        else:
            merged[key] = {**r, 'sources': [r['source']]}

out = list(merged.values())
TT = {'us': 'US', 'gb': 'UK', 'my': 'Malaysia', 'th': 'Thailand', 'id': 'Indonesia', 'ph': 'Philippines', 'vn': 'Vietnam'}


def label(s):
    if s.startswith('tiktok_'):  # tiktok_<region>_<top|new>
        _, cc, kind = s.split('_', 2)
        return f"TikTok Shop {TT.get(cc, cc.upper())} {'new hit' if kind == 'new' else 'top seller'}"
    return LABEL.get(s, s)


for r in out:
    r['source_label'] = ' · '.join(label(s) for s in r['sources'])
    r['gulf'] = any(s.startswith(('amazon_ae', 'amazon_sa')) for s in r['sources'])
multi = sum(1 for r in out if len(r['sources']) > 1)
print(f'{len(out)} unique items, {multi} on more than one store/list, '
      f'{sum(r["gulf"] for r in out)} from the Gulf', file=sys.stderr)
json.dump(out, sys.stdout, indent=1, ensure_ascii=False)

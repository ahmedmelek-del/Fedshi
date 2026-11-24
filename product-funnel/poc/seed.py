"""Prepare a ranked batch for the review page.

Reads out/ranked.csv and writes, for each item:
  out/seed/items/<doc_id>.json   the review-page document (without the photo asset fields)
  out/seed/images/<doc_id>.jpg   the product photo, for upload as an artifact asset
plus out/seed/manifest.json listing doc ids, photo paths and inbox ids to mark done.
Also appends the batch's ASINs to data/seen_asins.txt so they never come back.

Usage: python3 seed.py <batch-date YYYY-MM-DD> [max_items]
"""
import ast
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys

batch = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
day = dt.date.fromisoformat(batch)
week = (day + dt.timedelta(days=(5 - day.weekday()) % 7)).isoformat()  # next Saturday (or today if Saturday)

rows = list(csv.DictReader(open('out/ranked.csv')))[:limit]
os.makedirs('out/seed/items', exist_ok=True)
os.makedirs('out/seed/images', exist_ok=True)
manifest = {'batch': batch, 'week': week, 'items': []}
seen_new = []
seen_titles = []

for i, r in enumerate(rows, 1):
    doc_id = (r.get('asin') or r['id']).lower()
    doc_id = re.sub(r'[^a-z0-9_\-.]', '-', doc_id)[:120]
    rng = ast.literal_eval(r['ali_range_usd']) if r.get('ali_range_usd') else None
    # Gulf photos come from the EU image host, which the network blocks; the same path works on m.media-amazon.com.
    img = (r.get('image_url') or '').replace('images-eu.ssl-images-amazon.com', 'm.media-amazon.com')
    hi = re.sub(r'\._[^/]*_\.jpg$', '._AC_SL800_.jpg', img) if 'amazon.com' in img else img
    doc = {
        'rank': i, 'batch': batch, 'week': week, 'name': r['name'], 'score': int(r['score']),
        'wow': int(r['wow']), 'mass': int(r['mass']), 'open': int(r['open']), 'video': int(r['video']),
        'flags': r['flags'], 'note': r['note'],
        'bill_kg': float(r['bill_kg']), 'vol_kg': float(r['vol_kg']), 'freight_type': r['freight_type'],
        'freight_iqd': int(float(r['freight_iqd'])), 'max_cost_usd': float(r['max_cost_usd'] or 0),
        'iraq_price_iqd': int(float(r.get('iraq_price_iqd') or 0)),
        'ali_range_usd': f"${rng[0]:.0f}–{rng[1]:.0f}" if rng else '',
        'amazon_reviews': int(r['amazon_reviews'] or 0), 'ali_top_sold': int(r['ali_top_sold'] or 0),
        'amazon_url': r['amazon_url'], 'ali_url': r['ali_url'],
        'source': r.get('source') or 'amazon_new_releases', 'source_url': r.get('source_url', ''),
        'source_label': r.get('source_label', ''), 'image_src': hi,
        # Shadow mode: what the automatic filter decided, to compare with Ahmed's decision.
        'auto_decision': r.get('auto', ''), 'auto_reason': r.get('auto_reason', ''),
    }
    json.dump(doc, open(f'out/seed/items/{doc_id}.json', 'w'), ensure_ascii=False)
    photo = ''
    if img:
        p = f'out/seed/images/{doc_id}.jpg'
        small = re.sub(r'\._[^/]*_\.jpg$', '._AC_SX320_.jpg', img) if 'amazon.com' in img else img
        ok = subprocess.run(['curl', '-s', '-f', '-m', '30', '-o', p, small]).returncode == 0
        if ok and os.path.getsize(p) > 1000:
            photo = p
    manifest['items'].append({'doc_id': doc_id, 'item_file': f'out/seed/items/{doc_id}.json', 'photo': photo,
                              'inbox_id': r.get('inbox_id', '')})
    if r.get('asin'):
        seen_new.append(r['asin'])
    seen_titles.append(r.get('title') or r['name'])

json.dump(manifest, open('out/seed/manifest.json', 'w'), indent=1)
with open('data/seen_asins.txt', 'a') as f:
    f.writelines(a + '\n' for a in seen_new)
with open('data/seen_titles.txt', 'a') as f:
    f.writelines(t.replace('\n', ' ') + '\n' for t in seen_titles)
print(f"batch {batch} (week {week}): {len(manifest['items'])} items, "
      f"{sum(1 for x in manifest['items'] if x['photo'])} photos, {len(seen_new)} ASINs marked seen")

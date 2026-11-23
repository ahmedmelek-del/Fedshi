"""Rebuild the 'already shown' lists from the review page's items collection.

The review page database is the source of truth: every item ever shown is there, even when a run
couldn't push to GitHub. First save the collection with
  ArtifactData list collection=items, out_dir=<dir>   (page through with the cursor)
then run: python3 build_seen.py <dir>/items
Writes data/seen_asins.txt and data/seen_titles.txt (merged with what's already in them).
"""
import glob
import json
import os
import sys

src = sys.argv[1]
asins, titles = set(), set()
for p in ('data/seen_asins.txt', 'data/seen_titles.txt'):
    if os.path.exists(p):
        (asins if 'asins' in p else titles).update(l.strip() for l in open(p) if l.strip())
for f in glob.glob(os.path.join(src, '*.json')):
    d = json.load(open(f))
    data = d.get('data', d)
    doc_id = d.get('id') or os.path.basename(f)[:-5]
    if doc_id.startswith('b0') and len(doc_id) == 10:
        asins.add(doc_id.upper())
    url = data.get('amazon_url') or ''
    if '/dp/' in url:
        asins.add(url.rsplit('/dp/', 1)[1][:10].upper())
    for t in (data.get('title'), data.get('name')):
        if t:
            titles.add(t.replace('\n', ' ').strip())
open('data/seen_asins.txt', 'w').write('\n'.join(sorted(asins)) + '\n')
open('data/seen_titles.txt', 'w').write('\n'.join(sorted(titles)) + '\n')
print(f'{len(asins)} ASINs, {len(titles)} titles marked as already shown')

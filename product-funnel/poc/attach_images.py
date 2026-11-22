"""Write uploaded photo ids into the batch's item files, and print the ArtifactData batch writes.

Input: a JSON map {"<photo path as uploaded>": "<asset id>"} built from the Artifact asset upload result.
Usage: python3 attach_images.py out/seed/assets.json > out/seed/writes.json
"""
import json
import sys

assets = json.load(open(sys.argv[1]))
manifest = json.load(open('out/seed/manifest.json'))
writes = []
for it in manifest['items']:
    doc = json.load(open(it['item_file']))
    aid = assets.get(it['photo'])
    if aid:
        doc['image'] = '/_blob/' + aid
        doc['image_id'] = aid
    json.dump(doc, open(it['item_file'], 'w'), ensure_ascii=False)
    writes.append({'op': 'set', 'collection': 'items', 'doc_id': it['doc_id'], 'file_path': it['item_file']})
print(json.dumps(writes))

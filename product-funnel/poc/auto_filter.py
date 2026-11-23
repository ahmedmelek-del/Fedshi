"""Automatic filter: every crawled item gets a recorded decision (pass or reject, with a reason).

Stages, in order:
  1. rules    prefilter.py (hard rules)                       -> data/rule_rejects.json
  2. catalog  already sold by Fedshi, or its product type keeps failing ghost tests
  3. judge    Claude scores every remaining item (data/judged.json, written in the daily run)
  4. decide   thresholds on the judge scores -> pass / reject with a reason code

Commands (run from product-funnel/poc):
  python3 auto_filter.py catalog              # download the Fedshi catalog snapshot -> data/catalog.json
  python3 auto_filter.py match                # stage 2 on data/candidates.json -> data/judge_queue.json
  python3 auto_filter.py sheets [size]        # compact judge sheets -> data/judge/sheet_NN.txt (one line per item)
  python3 auto_filter.py decide [n] [sample]  # stage 4 -> data/auto_decisions.json, data/passes.json (top n),
                                              #   data/shadow_rejects.json (a few rejects for Ahmed to check)
  python3 auto_filter.py log <batch-date>     # write every decision to sourcing_candidates in Supabase
  python3 auto_filter.py human <items-dir> <decisions-dir>   # Ahmed's page decisions -> Supabase

  python3 auto_filter.py stats                # coverage of the last crawl + agreement with Ahmed (JSON)

Supabase calls go to the token-checked funnel functions (they open nothing else). The daily run reads the
funnel key from Ahmed's private area of the review page database (ArtifactData get, collection
data/users/me, doc funnel, field token) and passes it in the SOURCING_TOKEN environment variable.
The key expires on the date in the same doc; a new one is issued with public.sourcing_issue_token().
"""
import json
import os
import random
import re
import subprocess
import sys

from prefilter import tokens

SUPABASE = 'https://rndbaaladvmgpbsecxba.supabase.co/rest/v1/rpc/'
PUBLISHABLE_KEY = 'sb_publishable_LIxScKDbumZJE62PSvVC9A_LMl6Txut'  # public key, safe to keep in the repo

SATURATED_MATCH = 0.75   # share of a Fedshi item's name words found in the title (same product)
TYPE_MATCH = 0.5         # enough to borrow the product type and its ghost-test record
FAILED_TYPE_TESTS = 3    # a type with at least this many tests and no pass is rejected
PASS_MIN = 3             # every judge score must reach this to pass
JUDGE_REASON = [('open', 'saturated', 'already common in Iraq'),
                ('wow', 'no_wow', 'no wow or problem solved'),
                ('mass', 'niche', 'too niche for mass market'),
                ('video', 'weak_proof', 'hard to show in a video ad')]
VETO = {'bulky': 'too big or heavy for air freight', 'kids_toy': 'kids toy, not clearly trending',
        'low_value': 'looks too cheap for a 35k+ price', 'shown': 'already shown on the page',
        'consumable': 'consumable or refill', 'sized': 'sized item', 'not_product': 'not a physical product',
        'cosmetic': 'cosmetic or regulated', 'device_specific': 'fits only one device or model'}
WEIGHTS = {'wow': 25, 'mass': 20, 'open': 20, 'video': 15}


def rpc(name, payload):
    """POST to a funnel function; the payload goes through a file so it never hits the command line."""
    token = os.environ.get('SOURCING_TOKEN', '')
    if not token:
        print(f'{name}: skipped, SOURCING_TOKEN is not set (no Supabase access this run)')
        return None
    with open('data/.rpc_body.json', 'w') as f:
        json.dump(payload, f, ensure_ascii=False)
    out = subprocess.run(['curl', '-s', '-S', '-f', '-m', '120', '-X', 'POST', SUPABASE + name,
                          '-H', f'apikey: {PUBLISHABLE_KEY}', '-H', 'Content-Type: application/json',
                          '-H', f'X-Sourcing-Token: {token}',
                          '--data-binary', '@data/.rpc_body.json'], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f'{name} failed: {out.stderr.strip()} (the run token may have expired; issue a new one)')
    return json.loads(out.stdout)


def catalog():
    d = rpc('sourcing_catalog', {})
    if d is None:
        return
    json.dump(d, open('data/catalog.json', 'w'), ensure_ascii=False)
    # Arabic competitor names, one per line, for the judge to read.
    with open('data/competitors.txt', 'w') as f:
        for c in d['competitors']:
            f.write(f"{c['name']} | {c.get('price') or ''} IQD\n")
    print(f"catalog: {len(d['items'])} Fedshi items, {len(d['competitors'])} competitor items")


def best_match(tk, index, items):
    hits = {}
    for w in tk:
        for i in index.get(w, ()):
            hits[i] = hits.get(i, 0) + 1
    best, score = None, 0.0
    for i, n in hits.items():
        s = n / len(items[i]['tk'])
        if n >= 2 and s > score:
            best, score = i, s
    return best, score


def match():
    try:
        cat = json.load(open('data/catalog.json'))['items']
    except FileNotFoundError:
        print('WARNING: no data/catalog.json, so the Fedshi catalog check is skipped today')
        cat = []
    items = [{**c, 'tk': tokens(c['name'] or '')} for c in cat]
    items = [c for c in items if len(c['tk']) >= 2]
    index = {}
    for i, c in enumerate(items):
        for w in c['tk']:
            index.setdefault(w, []).append(i)
    queue, rejects = [], []
    for r in json.load(open('data/candidates.json')):
        i, s = best_match(tokens(r['title']), index, items)
        m = items[i] if i is not None else None
        info = {}
        if m and s >= TYPE_MATCH:
            info = {'product_type': m['type'], 'matched_item_fid': m['fid'], 'matched_item_name': m['name'],
                    'match_score': round(s, 2), 'type_items': m['type_items'], 'type_tests': m['type_tests'],
                    'type_passed': m['type_passed']}
        row = {**r, **info}
        if m and s >= SATURATED_MATCH:
            row['fedshi_status'] = m.get('status') or ('requested' if m.get('source') == 'requested' else 'suggested')
        if m and s >= SATURATED_MATCH and (m.get('status') == 'testing' or m.get('source') == 'requested'):
            # Already in Fedshi's pipeline (being tested, or already requested): a second request duplicates work.
            # Items that already PASSED stay in: re-sourcing a winner from China is a cost-down opportunity.
            rejects.append({**row, 'reason_code': 'in_pipeline',
                            'reason': f"Already in Fedshi's pipeline: {m['name']} ({row['fedshi_status']})"})
        elif info and m['type_tests'] >= FAILED_TYPE_TESTS and m['type_passed'] == 0:
            rejects.append({**row, 'reason_code': 'failed_before',
                            'reason': f"{m['type']}: 0 of {m['type_tests']} ghost tests passed"})
        else:
            queue.append(row)
    json.dump(queue, open('data/judge_queue.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(rejects, open('data/catalog_rejects.json', 'w'), ensure_ascii=False)
    print(f'catalog check: {len(rejects)} rejected ({sum(r["reason_code"] == "in_pipeline" for r in rejects)} already in '
          f"Fedshi's pipeline), {len(queue)} go to the judge, {sum(r.get('fedshi_status') == 'passed' for r in queue)} of them "
          f'already passed a Fedshi test (cost-down candidates) -> data/judge_queue.json')


def sheets(size=150):
    """Split the judge queue into short sheets: one line per item, with the catalog hint, so the judge
    can score every item cheaply. The judge answers with data/judge/answer_NN.json for each sheet."""
    os.makedirs('data/judge', exist_ok=True)
    q = json.load(open('data/judge_queue.json'))
    size = int(size)
    for k in range(0, len(q), size):
        with open(f'data/judge/sheet_{k // size:02d}.txt', 'w') as f:
            for r in q[k:k + size]:
                hint = {'passed': " | FEDSHI WINNER: same product passed a ghost test, China cost-down candidate",
                        'failed': " | same product FAILED a Fedshi ghost test before",
                        'suggested': " | a local supplier already offers this in Iraq"}.get(r.get('fedshi_status'), '')
                if r.get('product_type'):
                    hint += (f" | like Fedshi '{r['matched_item_name']}' ({r['match_score']:.0%}); type "
                            f"{r['product_type']}: {r['type_items']} items, {r['type_passed']}/{r['type_tests']} tests passed")
                f.write(f"{r['asin']} | {r['title'][:110]} | ${r.get('usd') or '?'} | {r.get('reviews') or 0} reviews"
                        f"{' | season ' + r['season'] if r.get('season') else ''}{hint}\n")
    print(f'{len(q)} items in {(len(q) + size - 1) // size} sheets -> data/judge/')


def collect():
    """Merge data/judge/answer_*.json into data/judged.json."""
    import glob
    out = {}
    for p in sorted(glob.glob('data/judge/answer_*.json')):
        out.update(json.load(open(p)))
    json.dump(out, open('data/judged.json', 'w'), ensure_ascii=False)
    return out


def decide(n=50, sample=5):
    collect()
    queue = json.load(open('data/judge_queue.json'))
    judged = json.load(open('data/judged.json'))
    out, missing = [], 0
    for r in queue:
        j = judged.get(r['asin'])
        if not j:
            missing += 1
            continue
        scores = {k: int(j.get(k, 0)) for k in WEIGHTS}
        low = [(k, code, text) for k, code, text in JUDGE_REASON if scores[k] < PASS_MIN]
        if j.get('x'):  # the judge's hard reject: bulky, kids_toy, low_value, shown, consumable, sized, not_product...
            low = [(None, j['x'], VETO.get(j['x'], j['x'].replace('_', ' ')))]
        score = round(sum(WEIGHTS[k] * v / 5 for k, v in scores.items())
                      + min(r.get('reviews') or 0, 1000) / 1000 * 10 + (5 if r.get('season') else 0)
                      + 5 * (len(r.get('sources') or []) > 1))
        k, code, text = min(low, key=lambda x: scores.get(x[0], 0)) if low else (None, None, None)
        out.append({**r, 'product_type': j.get('type') or r.get('product_type'), 'scores': scores, 'score': score,
                    'auto_decision': 'reject' if low else 'pass', 'reason_code': code or 'pass',
                    'reason': (f"{text}{f' ({k} {scores[k]}/5)' if k else ''}. " if low else '') + (j.get('why') or '')})
    # One item per product type: the best one passes, the rest are near-duplicates.
    best = {}
    for r in sorted([r for r in out if r['auto_decision'] == 'pass'], key=lambda r: -r['score']):
        t = (r.get('product_type') or '').lower()
        if t in best:
            r.update(auto_decision='reject', reason_code='duplicate',
                     reason=f"Same product type as a better pick ({best[t]}). " + r['reason'])
        else:
            best[t] = r['title'][:40]
    passes = sorted([r for r in out if r['auto_decision'] == 'pass'], key=lambda r: -r['score'])
    rejects = [r for r in out if r['auto_decision'] == 'reject']
    random.seed(len(out))
    json.dump(out, open('data/auto_decisions.json', 'w'), ensure_ascii=False)
    json.dump(passes[:int(n)], open('data/passes.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(random.sample(rejects, min(int(sample), len(rejects))), open('data/shadow_rejects.json', 'w'),
              indent=1, ensure_ascii=False)
    print(f'judge: {len(passes)} pass, {len(rejects)} reject, {missing} not judged (they stay undecided). '
          f'Top {min(int(n), len(passes))} -> data/passes.json; {min(int(sample), len(rejects))} rejects to check '
          f'-> data/shadow_rejects.json')
    if missing:
        print('WARNING: every queued item must be judged for the source to count as exhausted.')


def _row(r, batch, stage, decision, code, detail):
    return {'external_id': r.get('asin') or r.get('id'), 'title': r['title'], 'url': r.get('url'),
            'image_url': r.get('image_url') or r.get('image'), 'sources': r.get('sources') or [r.get('source')],
            'price_usd': r.get('usd'), 'reviews': r.get('reviews'), 'season': r.get('season'), 'batch': batch,
            'stage': stage, 'auto_decision': decision, 'reason_code': code, 'reason_detail': detail,
            **{k: r.get(k) for k in ('product_type', 'matched_item_fid', 'matched_item_name', 'match_score',
                                     'type_items', 'type_tests', 'type_passed', 'scores', 'score')}}


def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')


def log(batch):
    rows = []
    for r in json.load(open('data/rule_rejects.json')):
        rows.append(_row(r, batch, 'rules', 'reject', 'rule_' + slug(r['reason'])[:40], r['reason']))
    for r in json.load(open('data/catalog_rejects.json')):
        rows.append(_row(r, batch, 'catalog', 'reject', r['reason_code'], r['reason']))
    judged = set()
    for r in json.load(open('data/auto_decisions.json')):
        judged.add(r['asin'])
        rows.append(_row(r, batch, 'judge', r['auto_decision'], r['reason_code'], r['reason']))
    for r in json.load(open('data/judge_queue.json')):  # queued but not judged: logged as undecided
        if r['asin'] not in judged:
            rows.append(_row(r, batch, 'judge', None, None, 'not judged yet'))
    shown = set()
    try:
        shown = {s['id'] for s in json.load(open('shortlist.json'))}
    except FileNotFoundError:
        pass
    for x in rows:
        if x['external_id'] in shown:
            x['shown_on'] = batch
    rows = [x for x in rows if x['external_id'] and x['title']]
    json.dump(rows, open('data/decision_log.json', 'w'), ensure_ascii=False)  # kept even when Supabase is unreachable
    done = 0
    for i in range(0, len(rows), 500):
        r = rpc('sourcing_log', {'rows': rows[i:i + 500]})
        if r is None:
            break
        done += r['upserted']
    by = {}
    for x in rows:
        by[(x['stage'], x['auto_decision'])] = by.get((x['stage'], x['auto_decision']), 0) + 1
    print(f'logged {done} items to sourcing_candidates: ' + ', '.join(f'{s}/{d} {n}' for (s, d), n in sorted(by.items(), key=str)))


def human(items_dir, decisions_dir):
    """Send Ahmed's Request/Later/Skip taps (from the review page) to Supabase for the agreement check."""
    import glob
    import os
    batch_of, shown = {}, []
    for p in glob.glob(os.path.join(items_dir, '*.json')):
        d = json.load(open(p))
        d = d.get('data') or d
        doc = os.path.basename(p)[:-5]
        batch_of[doc] = d.get('batch')
        # Items shown before the automatic filter existed: add them so their decisions can be compared later.
        shown.append({'external_id': doc.upper(), 'title': d.get('name') or doc, 'url': d.get('source_url') or d.get('amazon_url'),
                      'image_url': d.get('image_src'), 'sources': [d.get('source') or 'review_page'],
                      'batch': d.get('batch'), 'shown_on': d.get('batch'), 'stage': 'shown',
                      'auto_decision': d.get('auto_decision'), 'reason_code': d.get('auto_reason_code'),
                      'scores': {k: d.get(k) for k in ('wow', 'mass', 'open', 'video')}, 'score': d.get('score')})
    for i in range(0, len(shown), 500):
        rpc('sourcing_log', {'rows': shown[i:i + 500]})
    rows = []
    for p in glob.glob(os.path.join(decisions_dir, '*.json')):
        d = json.load(open(p))
        d = d.get('data') or d
        doc = os.path.basename(p)[:-5]
        status = d.get('status') or d.get('decision')
        if not status:
            continue
        rows.append({'external_id': doc.upper(), 'decision': status, 'reasons': d.get('reasons') or [],
                     'decided_at': d.get('at') or d.get('decided_at'),
                     'item_request_id': (d.get('sent') or {}).get('id'), 'shown_on': batch_of.get(doc)})
    r = rpc('sourcing_decide', {'rows': rows}) if rows else None
    n = r['updated'] if r else 0
    print(f'human decisions: {len(rows)} read, {n} matched in sourcing_candidates')


def stats():
    r = rpc('sourcing_stats', {})
    if r is not None:
        print(json.dumps(r))


if __name__ == '__main__':
    cmd, *args = sys.argv[1:] or ['help']
    {'catalog': catalog, 'match': match, 'sheets': sheets, 'decide': decide, 'log': log, 'human': human,
     'stats': stats}.get(
        cmd, lambda *a: print(__doc__))(*args)

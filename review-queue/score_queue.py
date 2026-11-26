"""Review-queue scoring (shadow mode): score every new local buyer suggestion 0-100, give it a tier (A-D),
flags, plain reasons and selling angles, and save it to Supabase (review_scores). Nothing is approved or
rejected automatically; Item Flow Tracker shows the score next to each suggestion in the Review Queue.

Same method as the product funnel (product-funnel/poc/auto_filter.py): data signals from Supabase, Claude judges
every item from a text sheet plus photo contact sheets, then a transparent weighted score.

Commands (run from review-queue/):
  python3 score_queue.py pending [max]   # pending suggestions without a score -> data/pending.json,
                                         #   data/judge/sheet_NN.txt (text) + data/judge/sheet_NN.png (photos)
  python3 score_queue.py combine         # data/judge/answer_NN.json + signals -> data/scores.json (and a summary)
  python3 score_queue.py save            # data/scores.json -> Supabase review_scores
  python3 score_queue.py stats           # shadow-mode agreement per tier (JSON)

Supabase calls use the funnel key (SOURCING_TOKEN env var); see RUNBOOK.md.
"""
import io
import json
import os
import subprocess
import sys
import urllib.request

SUPABASE = 'https://rndbaaladvmgpbsecxba.supabase.co/rest/v1/rpc/'
PUBLISHABLE_KEY = 'sb_publishable_LIxScKDbumZJE62PSvVC9A_LMl6Txut'  # public key, safe to keep in the repo
MODEL_VERSION = 'v1-2026-11-26'

# v1 weights, calibrated on a blind backtest of 240 suggestions (Sep-Nov 2026): judge AUC 0.66 vs everything.
JUDGE_WEIGHTS = {'novelty': 0.50, 'wow': 0.25, 'video': 0.25}   # 1-5 scores from the judge
JUDGE_SHARE, DATA_SHARE = 0.75, 0.25
PASSED_BEFORE_BONUS = 10
TIERS = [('A', 55), ('B', 40), ('C', 28), ('D', 0)]                # score cut-offs (backtest quantiles 20/50/80%)
BASE_WIN = 0.31                                                    # average ghost-test win rate
PER_SHEET = 20


def rpc(name, payload):
    token = os.environ.get('SOURCING_TOKEN', '')
    if not token:
        sys.exit(f'{name}: SOURCING_TOKEN is not set (see RUNBOOK.md)')
    os.makedirs('data', exist_ok=True)
    with open('data/.rpc_body.json', 'w') as f:
        json.dump(payload, f, ensure_ascii=False)
    out = subprocess.run(['curl', '-s', '-S', '-f', '-m', '120', '-X', 'POST', SUPABASE + name,
                          '-H', f'apikey: {PUBLISHABLE_KEY}', '-H', 'Content-Type: application/json',
                          '-H', f'X-Sourcing-Token: {token}', '--data-binary', '@data/.rpc_body.json'],
                         capture_output=True, text=True)
    os.remove('data/.rpc_body.json')
    if out.returncode:
        sys.exit(f'{name} failed: {out.stderr.strip()} (the key may have expired)')
    return json.loads(out.stdout)


def clip(x):
    return max(0.0, min(1.0, x))


def pending(max_rows=200):
    rows = rpc('review_pending', {'max_rows': int(max_rows)})
    os.makedirs('data/judge', exist_ok=True)
    os.makedirs('data/img', exist_ok=True)
    for f in os.listdir('data/judge'):
        os.remove(os.path.join('data/judge', f))
    json.dump(rows, open('data/pending.json', 'w'), ensure_ascii=False, indent=1)
    failed = []
    for r in rows:
        path = f"data/img/{r['ticket_id']}.jpg"
        r['_img'] = path if os.path.exists(path) else None
        if r['_img'] or not r.get('image_url'):
            continue
        try:
            urllib.request.urlretrieve(r['image_url'], path)
            r['_img'] = path
        except Exception:
            failed.append(r['ticket_id'])
    for k in range(0, len(rows), PER_SHEET):
        chunk, n = rows[k:k + PER_SHEET], k // PER_SHEET + 1
        with open(f'data/judge/sheet_{n:02d}.txt', 'w') as f:
            for r in chunk:
                f.write(' | '.join([r['ticket_id'], (r.get('name') or '').strip(), f"{r.get('price_iqd') or '?'} IQD",
                                    r.get('product_type') or '?', 'video' if r.get('has_video') else 'no video',
                                    (r.get('notes') or '').replace('\n', ' ')[:120]]) + '\n')
        contact_sheet(chunk, f'data/judge/sheet_{n:02d}.png')
    print(f'{len(rows)} pending suggestions on {-(-len(rows) // PER_SHEET)} sheets'
          + (f'; photo download failed: {", ".join(failed)}' if failed else ''))


def contact_sheet(chunk, out, tile=300, cols=5):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    except OSError:
        font = ImageFont.load_default()
    rows_n = -(-len(chunk) // cols)
    sheet = Image.new('RGB', (cols * tile, rows_n * (tile + 36)), 'white')
    d = ImageDraw.Draw(sheet)
    for i, r in enumerate(chunk):
        x, y = (i % cols) * tile, (i // cols) * (tile + 36)
        d.text((x + 6, y + 4), r['ticket_id'], fill='black', font=font)
        if r.get('_img'):
            try:
                im = Image.open(r['_img']).convert('RGB')
                im.thumbnail((tile - 10, tile - 10))
                sheet.paste(im, (x + (tile - im.width) // 2, y + 36 + (tile - im.height) // 2))
            except Exception:
                d.text((x + 10, y + 120), 'no photo', fill='red', font=font)
        else:
            d.text((x + 10, y + 120), 'no photo', fill='red', font=font)
    sheet.save(out)


def score_one(r, j):
    jn = (sum(w * j[k] for k, w in JUDGE_WEIGHTS.items()) - 1) / 4
    pt = clip((r['ptype_win_rate'] - 0.2) / 0.25)
    bu = clip((r['buyer_win_rate'] - 0.2) / 0.25)
    passed_before = r['item_passed'] > 0 and r['item_failed'] == 0
    s = 100 * (JUDGE_SHARE * jn + DATA_SHARE * (0.5 * pt + 0.5 * bu)) + (PASSED_BEFORE_BONUS if passed_before else 0)
    s = int(round(min(100, max(0, s))))
    tier = next(t for t, cut in TIERS if s >= cut)

    flags = []
    if r['item_failed']:
        flags.append('failed_previous_test')
    if r['item_passed']:
        flags.append('passed_before')
    if r['item_in_testing']:
        flags.append('in_testing')
    if r['item_in_app'] or r['item_delivered']:
        flags.append('already_in_app')
    if r['item_open_suggestions']:
        flags.append('duplicate_open')

    reasons = []
    if j.get('why'):
        reasons.append(j['why'])
    if j['novelty'] >= 4:
        reasons.append('Rarely seen in Iraqi shops')
    elif j['novelty'] <= 2:
        reasons.append('Common in Iraqi shops')
    if j['wow'] >= 4 and j['video'] >= 4:
        reasons.append('Strong wow factor and easy to show in a video')
    elif j['video'] <= 2:
        reasons.append('Hard to show in a video ad')
    if r['ptype_tests'] >= 5:
        reasons.append(f"Product type wins {round(100 * r['ptype_win_rate'])}% of ghost tests ({r['ptype_tests']} tests)")
    if r['buyer_tests'] >= 10 and abs(r['buyer_win_rate'] - BASE_WIN) >= 0.05:
        reasons.append(f"Buyer's suggestions win {round(100 * r['buyer_win_rate'])}% of tests")
    if r['item_passed']:
        reasons.append(f"Same item passed {r['item_passed']} ghost test(s) before")
    if r['item_failed']:
        reasons.append(f"Same item failed {r['item_failed']} ghost test(s) before (weak signal: retests still win about 1 in 4)")
    if j.get('x'):
        reasons.append(f"Judge note: {j['x'].replace('_', ' ')}")
    return {'suggestion_id': r['suggestion_id'], 'ticket_id': r['ticket_id'], 'model_version': MODEL_VERSION,
            'score': s, 'tier': tier,
            'judge': {k: j.get(k) for k in ('wow', 'video', 'novelty', 'mass', 'look', 'season', 'why', 'x')},
            'signals': {k: r[k] for k in ('ptype_win_rate', 'ptype_tests', 'buyer_win_rate', 'buyer_tests', 'item_passed',
                                          'item_failed', 'item_in_testing', 'item_prior_suggestions',
                                          'item_open_suggestions', 'item_delivered', 'item_in_app')},
            'flags': flags, 'reasons': reasons[:6], 'angles': (j.get('angles') or [])[:3]}


def combine():
    rows = json.load(open('data/pending.json'))
    answers = {}
    for f in sorted(os.listdir('data/judge')):
        if f.startswith('answer_') and f.endswith('.json'):
            answers.update(json.load(open(os.path.join('data/judge', f))))
    out, missing = [], []
    for r in rows:
        j = answers.get(r['ticket_id'])
        if not j or any(not isinstance(j.get(k), (int, float)) for k in JUDGE_WEIGHTS):
            missing.append(r['ticket_id'])
            continue
        out.append(score_one(r, j))
    json.dump(out, open('data/scores.json', 'w'), ensure_ascii=False, indent=1)
    tiers = {t: sum(1 for o in out if o['tier'] == t) for t, _ in TIERS}
    print(json.dumps({'scored': len(out), 'missing_judge': missing, 'tiers': tiers,
                      'top': [f"{o['ticket_id']} {o['score']}" for o in sorted(out, key=lambda o: -o['score'])[:5]]},
                     ensure_ascii=False))


def save():
    rows = json.load(open('data/scores.json'))
    for k in range(0, len(rows), 100):
        print(rpc('review_save_scores', {'rows': rows[k:k + 100]}))


def stats():
    print(json.dumps(rpc('review_stats', {}), indent=1))


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    {'pending': pending, 'combine': combine, 'save': save, 'stats': stats}[cmd](*args)

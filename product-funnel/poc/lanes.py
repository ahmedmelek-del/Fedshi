"""Exploration lanes: new categories or product types tried for a fixed period with their own quota.

A lane has its own Gulf Amazon searches, can relax a hard rule for its items, keeps up to `max_per_type`
passes per product type (instead of one), and reserves `quota` of the daily batch so new items are not
crowded out by proven categories. After `end`, look at Ahmed's requests, agreement and ghost results for
the lane, then keep it (move its searches into the normal crawl) or drop it.

Usage:
  python3 lanes.py            # list lanes and whether each is running today
  python3 lanes.py crawl      # Gulf searches for running lanes -> data/raw/lane_<cc>_<id>.json
"""
import datetime as dt
import json
import os
import subprocess
import sys

LANES = [
    {'id': 'beauty_devices', 'name': 'Beauty devices (no liquids)', 'start': '2026-11-25', 'end': '2026-12-09',
     'quota': 10, 'max_per_type': 3, 'min_reviews': 200,  # lane searches are broad: only items with real demand
     # Ghost tests: hair and grooming devices passed 6 of 7 (heated comb, hair removal, nail clipper, callus
     # remover, scalp massager, curler attachment); face-lifting, derma pen and IPL devices failed.
     'queries': ['hair straightener brush', 'heated comb', 'electric nail clipper', 'electric callus remover',
                 'hair removal device women', 'electric scalp massager', 'hair dryer brush', 'facial cleansing brush',
                 'electric nose hair trimmer', 'heated eyelash curler', 'nail drill machine', 'cordless hair curler'],
     # Devices whose titles mention oil, gel, spray or cream go to the judge instead of being rejected as
     # liquids; the judge still rejects real cosmetics with the `cosmetic` code.
     'relax': ['liquid/cosmetic'],
     'device_words': r'\b(device|electric|rechargeable|cordless|usb|trimmer|shaver|epilator|dryer|straightener|curler|'
                     r'curling|comb|massager|brush|machine|led|clipper|callus|remover|drill|warmer|steamer|tool)\b',
     'note': 'Ahmed, 25 Nov: open beauty devices; no liquids or cosmetics.'},
]


def today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date()  # Baghdad


def running(on=None):
    on = on or today()
    return [l for l in LANES if dt.date.fromisoformat(l['start']) <= on <= dt.date.fromisoformat(l['end'])]


def by_id(lane_id):
    return next((l for l in LANES if l['id'] == lane_id), None)


def crawl():
    ls = running()
    if not ls:
        print('no running lane', file=sys.stderr)
        return
    os.makedirs('data/raw', exist_ok=True)
    procs = []
    for host, cc in (('www.amazon.ae', 'ae'), ('www.amazon.sa', 'sa')):
        for l in ls:
            env = {**os.environ, 'HOST': host, 'LANE': l['id']}
            log = open(f"data/raw/lane_{cc}_{l['id']}.log", 'w')
            procs.append(subprocess.Popen(['node', 'scrapers/amazon_search.js', f"data/raw/lane_{cc}_{l['id']}.json",
                                           *l['queries']], env=env, stderr=log))
    for p in procs:
        p.wait()


if __name__ == '__main__':
    if sys.argv[1:] == ['crawl']:
        crawl()
    else:
        on = today()
        for l in LANES:
            state = 'RUNNING' if l in running(on) else ('later' if on < dt.date.fromisoformat(l['start']) else 'ended')
            print(f"{state:8s} {l['name']:32s} {l['start']} → {l['end']}  quota {l['quota']}/day, "
                  f"{l['max_per_type']} per type, {len(l['queries'])} searches")

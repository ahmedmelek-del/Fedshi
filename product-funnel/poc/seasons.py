"""Season calendar for Iraq: which events to source for now, and by when the order must go out.

An event is "open" from LOOK_DAYS before it until its last order date, which leaves time for the
buyer's quotation, air freight from China (about 2 weeks) and a short test before the event.
After the last order date the event's items are dropped as too late; before the window they are
dropped as too early.

Usage:
  python3 seasons.py                 # print the open events (and what's next)
  python3 seasons.py crawl           # search Amazon UAE + Saudi for the open events -> data/raw/season_*.json
Dates are approximate for Islamic events (moon sighting); check them each year.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys

LOOK_DAYS = 70     # start sourcing this many days before the event
LEAD_DAYS = 25     # last order date = event - LEAD_DAYS (quotation + air freight + test)

# keywords: titles that belong to the event (used to tag items, and to drop them when out of window)
# queries: Amazon searches used while the event is open
EVENTS = [
    # Dated New Year's Eve: in Iraq the decorations sell through 31 December, not only Christmas.
    {'id': 'christmas', 'name': 'Christmas & New Year', 'date': '2026-12-31',
     'keywords': r'christmas|xmas|santa|snowman|reindeer|new year|nativity|gingerbread|ornaments?|tree topper|advent',
     'queries': ['christmas decorations', 'christmas lights', 'christmas tree', 'new year decorations', 'christmas gifts']},
    {'id': 'valentine', 'name': "Valentine's Day", 'date': '2027-02-14',
     'keywords': r"valentine|i love you|forever rose|preserved rose|eternal rose|couples? gift",
     'queries': ['valentines gifts for her', 'eternal rose gift box', 'valentines gifts for him']},
    {'id': 'ramadan', 'name': 'Ramadan', 'date': '2027-02-08',
     'keywords': r'ramadan|ramadhan|fanoos|fanous|crescent lantern|iftar|suhoor|quran|prayer mat|tasbih|misbaha|islamic',
     'queries': ['ramadan decorations', 'ramadan lantern', 'quran speaker', 'prayer mat', 'iftar serving']},
    {'id': 'eid_fitr', 'name': 'Eid al-Fitr', 'date': '2027-03-10',
     'keywords': r'\beid\b|eidi|eid mubarak',
     'queries': ['eid decorations', 'eid gifts', 'eidi money envelope']},
    {'id': 'mothers_day', 'name': "Mother's Day (21 March)", 'date': '2027-03-21',
     'keywords': r"mother'?s day|gifts? for (mom|mum|mother)",
     'queries': ['mothers day gifts', 'gifts for mom']},
    {'id': 'summer', 'name': 'Summer heat', 'date': '2027-05-15',
     'keywords': r'neck fan|cooling towel|misting fan|portable fan|personal fan|ice roller|car sunshade|cooling vest',
     'queries': ['portable neck fan', 'rechargeable misting fan', 'car sunshade']},
    {'id': 'eid_adha', 'name': 'Eid al-Adha & Hajj', 'date': '2027-05-17',
     'keywords': r'hajj|umrah|ihram|adha',
     'queries': ['hajj umrah accessories', 'eid al adha decorations']},
    {'id': 'school', 'name': 'Back to school', 'date': '2027-09-20',
     'keywords': r'back to school|school bag|backpack for (kids|school)|lunch ?box|pencil case|school supplies',
     'queries': ['back to school supplies', 'kids lunch box', 'pencil case']},
]
# Western events with no Iraqi market: always dropped.
NEVER = r'halloween|thanksgiving|easter|hanukkah|st\.? patrick|4th of july|independence day'


def today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date()  # Baghdad


def window(e):
    d = dt.date.fromisoformat(e['date'])
    return d - dt.timedelta(days=LOOK_DAYS), d - dt.timedelta(days=LEAD_DAYS), d


def open_events(on=None):
    on = on or today()
    return [e for e in EVENTS if window(e)[0] <= on <= window(e)[1]]


def classify(title, on=None):
    """Return (event or None, status): status is 'open', 'too late', 'too early', 'never' or ''."""
    t = title.lower()
    if re.search(rf'\b({NEVER})\b', t):
        return None, 'never'
    on = on or today()
    for e in EVENTS:
        if re.search(rf"\b({e['keywords']})", t):
            start, last, _ = window(e)
            if on < start:
                return e, 'too early'
            if on > last:
                return e, 'too late'
            return e, 'open'
    return None, ''


def label(e):
    _, last, _ = window(e)
    return f"season: {e['name']} · order by {last.day} {last.strftime('%b')}"


def crawl():
    evs = open_events()
    if not evs:
        print('no open season', file=sys.stderr)
        return
    os.makedirs('data/raw', exist_ok=True)
    procs = []
    for host, cc in (('www.amazon.ae', 'ae'), ('www.amazon.sa', 'sa')):
        for e in evs:
            out = f"data/raw/season_{cc}_{e['id']}.json"
            env = {**os.environ, 'HOST': host, 'SEASON': e['id']}
            log = open(f"data/raw/season_{cc}_{e['id']}.log", 'w')
            procs.append(subprocess.Popen(['node', 'scrapers/amazon_search.js', out, *e['queries']], env=env, stderr=log))
    for p in procs:
        p.wait()


if __name__ == '__main__':
    if sys.argv[1:] == ['crawl']:
        crawl()
    else:
        for e in EVENTS:
            s, last, d = window(e)
            state = 'OPEN' if s <= today() <= last else ('later' if today() < s else 'closed')
            print(f"{state:6s} {e['name']:28s} event {d}  sourcing {s} → order by {last}")

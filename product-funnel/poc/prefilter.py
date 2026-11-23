"""Rule-based hard filters for raw candidates (step 1 of scoring).

Drops: excluded categories (clothing/sized, liquids/cosmetics, fragile), big brands,
seasonal-Western items, out-of-range prices, and items too heavy/bulky for air (by keyword).
Usage: python3 prefilter.py data/amazon_new_releases.json data/candidates.json [data/seen_asins.txt]
The optional seen file lists ASINs already shown on the review page; they are skipped.
"""
import json
import re
import sys

EXCLUDE = {
    'clothing/sized': r"\b(rings|ring size|necklace|bracelet|earrings?|shirt|t-shirt|dress|hoodie|sweater|jacket|pants|leggings|socks?|shoes?|sneakers?|boots?|slippers?|pajamas?|bra|underwear|costume|hat|beanie|gloves?|onesie|romper|swimsuit|size \d)\b",
    'liquid/cosmetic': r"\b(lotion|serum|cream|shampoo|conditioner|oil|perfume|cologne|spray|gel|liquid|soap|wash|cleaner solution|ink|paint|polish|makeup|lipstick|mascara|sunscreen|supplement|vitamin|gummies|capsules?|tea|coffee beans|sauce|snack|food)\b",
    'fragile': r"\b(glass|ceramic|porcelain|crystal|mirror|marble|stoneware)\b",
    'seasonal-west': r"\b(christmas|xmas|advent|halloween|thanksgiving|stocking|santa|ornaments?|easter|hanukkah)\b",
    'bulky/heavy': r"\b(heater|grill|smoker|chair|table|desk|sofa|mattress|cabinet|shelf|shelving|bike|bicycle|scooter|treadmill|tent|stroller|car seat|crib|playpen|tv\b|monitor|printer|refrigerator|freezer|air fryer|oven|microwave|vacuum cleaner|generator|tire|tyre|lawn mower|kayak)\b",
    'pets (not a market in Iraq)': r"\b(dogs?|cats?|puppy|puppies|kitten|pet|pets|paw|leash|litter|aquarium|bird seed|chicken dewormer)\b",
    'not-physical/regulated': r"\b(gift card|subscription|kindle|ebook|book|dvd|blu-ray|knife|knives|blade|gun|airsoft|tactical|vape|lighter|drone)\b",
}
BRANDS = r"^(yeti|stanley|owala|cuisinart|kitchenaid|ember|apple|samsung|sony|bose|jbl|anker|lego|hasbro|mattel|barbie|nike|adidas|dyson|ninja|shark|instant pot|ring|blink|amazon|echo|fire tv|google|logitech|disney|marvel|pokemon|hot wheels|fisher-price|vtech|melissa|crayola|hydro ?flask|ninja|black\+decker|dewalt|milwaukee|ryobi|craftsman|makita|bosch|garmin|fitbit|meta|nintendo|playstation|xbox|weber|traeger|coleman|igloo|rubbermaid|oxo|lodge|le creuset|pyrex|corelle|zojirushi|keurig|nespresso|breville|hamilton beach|kong|chewy|purina|pampers|huggies|graco|chicco|ergobaby|dr\. brown|philips|braun|oral-b|gillette|energizer|duracell)\b"
KIDS_TOY = r"\b(toy|toys|kids|children|toddler|plush|squishy|doll|puzzle|blind box|play-?doh|nerf|pretend play|ages? \d)"
TRENDY_REVIEWS = 1000  # kids' toys only pass when clearly trending (Ahmed: toys rarely make good orders)
USD_MIN, USD_MAX = 8, 60

STOP = set("for with and the of in to a an on by from new 2026 2027 upgraded pack pcs set 1 2 3 4 5 6 portable mini rechargeable".split())


def tokens(t):
    t = re.split(r"[|,(]", t.lower())[0]
    return {w for w in re.findall(r"[a-z]+", t) if w not in STOP and len(w) > 2}


def similar(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def price(p):
    m = re.search(r"[\d.]+", (p or '').replace(',', ''))
    return float(m.group()) if m else None


def main(src, dst, seen_path=None):
    rows = json.load(open(src))
    seen = set()
    if seen_path:
        try:
            seen = {l.strip() for l in open(seen_path) if l.strip()}
        except FileNotFoundError:
            pass
    # Titles of everything already shown on the review page: skip the same kind of product.
    shown = []
    try:
        shown = [tokens(l) for l in open('data/seen_titles.txt') if l.strip()]
    except FileNotFoundError:
        pass
    kept, dropped = [], {}
    seen_titles = set()
    for r in rows:
        t = r['title'].lower()
        if r.get('asin') in seen:
            dropped['already reviewed'] = dropped.get('already reviewed', 0) + 1
            continue
        reason = next((k for k, rx in EXCLUDE.items() if re.search(rx, t)), None)
        if not reason and re.search(KIDS_TOY, t) and r.get('reviews', 0) < TRENDY_REVIEWS:
            reason = 'kids toy (not trending)'
        if not reason and shown:
            tk = tokens(r['title'])
            if any(similar(tk, s2) >= 0.5 for s2 in shown):
                reason = 'same type as an item already shown'
        if not reason and re.search(BRANDS, t):
            reason = 'big brand'
        usd = price(r.get('price'))
        if not reason and (usd is None or not USD_MIN <= usd <= USD_MAX):
            reason = 'price out of band'
        key = t[:40]
        if not reason and key in seen_titles:
            reason = 'duplicate'
        if reason:
            dropped[reason] = dropped.get(reason, 0) + 1
            continue
        seen_titles.add(key)
        kept.append({**r, 'usd': usd})
    json.dump(kept, open(dst, 'w'), indent=1)
    print(f"in {len(rows)} -> kept {len(kept)}")
    for k, v in sorted(dropped.items(), key=lambda x: -x[1]):
        print(f"  dropped {v:4d}  {k}")


if __name__ == '__main__':
    main(*sys.argv[1:4])

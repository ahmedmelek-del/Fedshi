"""Rule-based hard filters for raw candidates (step 1 of scoring).

Drops: excluded categories (clothing/sized, liquids/cosmetics, fragile), big brands,
out-of-window seasonal items (see seasons.py), out-of-range prices, and items too heavy/bulky for air (by keyword).
Usage: python3 prefilter.py data/amazon_new_releases.json data/candidates.json [data/seen_asins.txt]
The optional seen file lists ASINs already shown on the review page; they are skipped.
"""
import json
import re
import sys

import seasons

EXCLUDE = {
    'clothing/sized': r"\b(rings|ring size|necklace|bracelet|earrings?|shirt|t-shirt|dress|hoodie|sweater|jacket|pants|leggings|socks?|shoes?|sneakers?|boots?|slippers?|pajamas?|bra|underwear|costume|hat|beanie|gloves?|onesie|romper|swimsuit|size \d)\b",
    'liquid/cosmetic': r"(\b\d+(\.\d+)? ?(ml|l|ltr|litres?|liters?|oz)\b)|\b(softener|floor cleaner|disinfectant|refill cartridge|eye patch|cleanser|balm|wipes|dryer sheets|detergent|toner|moisturi[sz]er|lotion|serum|cream|shampoo|conditioner|oil|perfume|cologne|spray|gel|liquid|soap|wash|cleaner solution|ink|paint|polish|makeup|lipstick|mascara|sunscreen|supplement|vitamin|gummies|capsules?|tea|coffee beans|sauce|snack|food|face mask|sheet mask|facial mask|peel off|eye patches|spot patches|retinal|retinol|collagen|niacinamide|deodorant|anti-perspirant|lip liner|lip stain|hair colou?r|dishwasher tabs|dishwasher tablets|protein powder|whey|creatine|magnesium|electrolytes?|probiotic|tissues?|toilet paper|toilet roll|copy paper|moisture absorber|calcium chloride)\b",
    'fragile': r"\b(glass|ceramic|porcelain|crystal|mirror|marble|stoneware)\b",
    'bulky/heavy': r"\b(ladder|stepladder|step stool|vibration plate|yoga mat|mop|bucket|heater|grill|smoker|chair|table|desk|sofa|mattress|cabinet|shelf|shelving|bike|bicycle|scooter|treadmill|tent|stroller|car seat|crib|playpen|tv\b|monitor|printer|refrigerator|freezer|air fryer|oven|microwave|vacuum cleaner|generator|tire|tyre|lawn mower|kayak)\b",
    'pets (not a market in Iraq)': r"\b(dogs?|cats?|puppy|puppies|kitten|pet|pets|paw|leash|litter|aquarium|bird seed|chicken dewormer)\b",
    'commodity (common in Iraq)': r"\b(screen protector|phone case|case for iphone|for iphone \d+ pro|for galaxy s\d+|hdmi cable|usb.?c cable|charging cable|hdmi|charger block|wall charger|earbuds|earphones|headphones|memory card|micro ?sd|power strip|resistance bands|smart band|instax|film)\b",
    'not-physical/regulated': r"\b(gift card|subscription|kindle|ebook|book|dvd|blu-ray|knife|knives|blade|gun|airsoft|tactical|vape|lighter|drone|playstation 5|ps5|xbox|nintendo switch|trading cards?|mega box|factory sealed|golf balls?|pro v1|calendar|notebook|colou?ring books?|jigsaw|puzzle evening|gift voucher|replacement band|replacement strap|compatible with (whoop|apple watch|fitbit|garmin))\b",
}
BRANDS = r"^(yeti|stanley|owala|cuisinart|kitchenaid|ember|apple|samsung|sony|bose|jbl|anker|lego|hasbro|mattel|barbie|nike|adidas|dyson|ninja|shark|instant pot|ring|blink|amazon|echo|fire tv|google|logitech|disney|marvel|pokemon|hot wheels|fisher-price|vtech|melissa|crayola|hydro ?flask|ninja|black\+decker|dewalt|milwaukee|ryobi|craftsman|makita|bosch|garmin|fitbit|meta|nintendo|playstation|xbox|weber|traeger|coleman|igloo|rubbermaid|oxo|lodge|le creuset|pyrex|corelle|zojirushi|keurig|nespresso|breville|hamilton beach|kong|chewy|purina|pampers|huggies|graco|chicco|ergobaby|dr\. brown|philips|braun|oral-b|gillette|energizer|duracell|xiaomi|redmi|ugreen|soundcore|cerave|la roche|levoit|sandisk|fujifilm|waterwipes|bounce|torras|baseus|huawei|honor|oppo|realme|lenovo|hp|dell|asus|acer|tp-link|kingston|lexar|nivea|vaseline|johnson|dettol|tefal|moulinex|kenwood|black \+ decker|panasonic|sharp|toshiba|lg|tecno|infinix|joyroom|belkin|spigen|otterbox|esr|mi|casio|speedo|rubik'?s|jenga|command|titleist|taylormade|whoop|govee|kleenex|fairy|persil|maybelline|l[’']?or[ée]al|the ordinary|intex|fiskars|honeywell|wilson|hyperx|maped|pentel|oxford|utopia|play-doh|medicube|biodance|celimax|abib|uriage|optimum nutrition|thorne|now foods|tramontina|vileda|alfanar|hala|skillmatics|picassotiles|bright starts)\b"
KIDS_TOY = r"\b(toys for|magnetic tiles|building blocks|stem|toy|toys|kids|children|toddler|plush|squishy|doll|puzzle|blind box|play-?doh|nerf|pretend play|ages? \d)"
TRENDY_REVIEWS = 1000  # kids' toys only pass when clearly trending (Ahmed: toys rarely make good orders)

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
    kept, dropped, rejected = [], {}, []
    seen_titles = set()
    for r in rows:
        t = r['title'].lower()
        if r.get('asin') in seen:
            dropped['already reviewed'] = dropped.get('already reviewed', 0) + 1
            continue
        reason = next((k for k, rx in EXCLUDE.items() if re.search(rx, t)), None)
        ev, state = seasons.classify(t)
        if not reason and state == 'never':
            reason = 'western holiday (no market in Iraq)'
        elif not reason and state in ('too late', 'too early'):
            reason = f'season {state}'
        elif state == 'open':
            r = {**r, 'season': ev['id']}
        if not reason and re.search(KIDS_TOY, t) and r.get('reviews', 0) < TRENDY_REVIEWS:
            reason = 'kids toy (not trending)'
        if not reason and shown:
            tk = tokens(r['title'])
            if any(similar(tk, s2) >= 0.5 for s2 in shown):
                reason = 'same type as an item already shown'
        if not reason and re.search(BRANDS, t):
            reason = 'big brand'
        usd = price(r.get('price'))
        key = t[:40]
        if not reason and key in seen_titles:
            reason = 'duplicate'
        if reason:
            dropped[reason] = dropped.get(reason, 0) + 1
            rejected.append({**r, 'usd': usd, 'reason': reason})
            continue
        seen_titles.add(key)
        kept.append({**r, 'usd': usd})
    # Strongest upstream signal first: on several stores/lists, then Gulf, then most reviews.
    kept.sort(key=lambda r: (-len(r.get('sources') or [1]), -int(bool(r.get('gulf'))), -(r.get('reviews') or 0)))
    n_season = sum(1 for r in kept if r.get('season'))
    if n_season:
        print(f'{n_season} in-season items (open: ' + ', '.join(e['name'] for e in seasons.open_events()) + ')')
    json.dump(kept, open(dst, 'w'), indent=1, ensure_ascii=False)
    # Every rejection is kept with its reason, so each crawled item ends up with a recorded decision.
    json.dump(rejected, open('data/rule_rejects.json', 'w'), ensure_ascii=False)
    print(f"in {len(rows)} -> kept {len(kept)}")
    for k, v in sorted(dropped.items(), key=lambda x: -x[1]):
        print(f"  dropped {v:4d}  {k}")


if __name__ == '__main__':
    main(*sys.argv[1:4])

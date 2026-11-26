#!/usr/bin/env bash
# Crawl every Amazon source in parallel, then merge into data/amazon_new_releases.json.
#   US new releases                  (what's new and selling in the US)
#   UAE + Saudi new releases         (new in the Gulf, one step before Iraq)
#   UAE + Saudi + US best sellers    (already proven; US best sellers widen the pool)
#   UAE + Saudi seasonal searches    (only for events open now, see seasons.py)
#   UAE + Saudi lane searches        (new categories on trial, see lanes.py)
#   TikTok Shop top sellers          (FastMoss: US, UK, Malaysia, Thailand; 10 categories)
# Run from product-funnel/poc. Takes about 10 minutes.
set -u
mkdir -p data/raw
S=scrapers/amazon_new_releases.js
node $S data/raw/us_nr.json 2>data/raw/us_nr.log &
HOST=www.amazon.ae node $S data/raw/ae_nr.json 2>data/raw/ae_nr.log &
HOST=www.amazon.sa node $S data/raw/sa_nr.json 2>data/raw/sa_nr.log &
wait
HOST=www.amazon.ae LIST=bestsellers node $S data/raw/ae_bs.json 2>data/raw/ae_bs.log &
HOST=www.amazon.sa LIST=bestsellers node $S data/raw/sa_bs.json 2>data/raw/sa_bs.log &
LIST=bestsellers node $S data/raw/us_bs.json 2>data/raw/us_bs.log &
python3 seasons.py crawl &
python3 lanes.py crawl &
# TikTok Shop trends (FastMoss): only when the FastMoss login is on this machine (DAILY_RUN.md step 0 restores it).
[ -f ~/.fastmoss-mcp/state.json ] && (cd scrapers && python3 fastmoss_source.py ../data/raw/tiktok.json 2>../data/raw/tiktok.log) &
wait
tail -n1 data/raw/*.log
python3 merge_sources.py data/raw/us_nr.json data/raw/ae_nr.json data/raw/sa_nr.json data/raw/ae_bs.json data/raw/sa_bs.json data/raw/us_bs.json data/raw/season_*.json data/raw/lane_*.json data/raw/tiktok.json \
  > data/amazon_new_releases.json

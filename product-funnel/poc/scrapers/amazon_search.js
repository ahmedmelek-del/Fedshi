// Search Amazon for seasonal keywords (e.g. Christmas decorations) and keep the top organic results.
// Usage: node scrapers/amazon_search.js out.json "christmas decorations" "christmas lights" ...
// Environment: HOST (default www.amazon.com), SEASON (label saved on each row), PAGES (default 1).
// Rows have the same shape as amazon_new_releases.js, with source amazon_<us|ae|sa>_season.
const { chromium } = require('playwright');
const fs = require('fs');

const HOST = process.env.HOST || 'www.amazon.com';
const SEASON = process.env.SEASON || '';
const PAGES = Number(process.env.PAGES || 1);
const CC = HOST.split('.').pop() === 'com' ? 'us' : HOST.split('.').pop();
const TO_USD = { AED: 1 / 3.67, SAR: 1 / 3.75, '$': 1 };
const RESULT = '[data-component-type="s-search-result"]';

(async () => {
  const [out, ...queries] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ locale: 'en-US' })).newPage();
  const rows = [];
  for (const q of queries) {
    for (let p = 1; p <= PAGES; p++) {
      const url = `https://${HOST}/s?k=${encodeURIComponent(q)}&page=${p}&language=en_AE`;
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
        if (!(await page.$(RESULT))) {
          // amazon.sa sometimes shows a "continue shopping" page first.
          const btn = await page.$('button, input[type="submit"]');
          if (btn) { await btn.click().catch(() => {}); await page.waitForTimeout(3000); }
        }
        await page.waitForSelector(RESULT, { timeout: 15000 });
      } catch (e) { console.error(`no results: ${q} p${p}`); continue; }
      const found = await page.$$eval(RESULT, els => els.map(el => {
        const text = el.innerText;
        const m = text.match(/(AED|SAR|\$)\s?([\d,]+(?:\.\d+)?)/);
        const rv = el.querySelector('a[href*="customerReviews"]')?.innerText || '';
        return {
          asin: el.getAttribute('data-asin') || '',
          title: (el.querySelector('h2')?.innerText || el.querySelector('img')?.alt || '').trim(),
          image: el.querySelector('img.s-image')?.getAttribute('src') || '',
          sponsored: /Sponsored/.test(text),
          currency: m ? m[1] : '',
          amount: m ? Number(m[2].replace(/,/g, '')) : null,
          rating: Number((text.match(/([\d.]+) out of 5/) || [])[1] || 0),
          reviews: rv,
          bought: (text.match(/([\d.,]+K?\+?) bought in past month/) || [])[1] || '',
        };
      }));
      for (const r of found) {
        if (!r.asin || r.sponsored || !r.title) continue;
        const usd = r.amount != null ? (r.amount * (TO_USD[r.currency] || 1)).toFixed(2) : '';
        // Review counts show as "1,234" or "(1.2K)".
        const k = (r.reviews.match(/([\d.,]+)\s*(K?)/i) || []);
        const reviews = k[1] ? Math.round(Number(k[1].replace(/,/g, '')) * (k[2] ? 1000 : 1)) : 0;
        rows.push({
          asin: r.asin, title: r.title, url: `https://${HOST}/dp/${r.asin}`, image_url: r.image,
          price: usd ? `$${usd}` : '', price_local: r.amount != null ? `${r.currency} ${r.amount}` : '',
          rating: r.rating, reviews, bought: r.bought, query: q, season: SEASON,
          category: `search: ${q}`, source: `amazon_${CC}_season`,
        });
      }
      console.error(`${q} p${p}: ${found.length}`);
    }
  }
  await browser.close();
  const seen = new Set();
  const uniq = rows.filter(r => !seen.has(r.asin) && seen.add(r.asin));
  fs.writeFileSync(out, JSON.stringify(uniq, null, 1));
  console.error(`${uniq.length} items from ${HOST}`);
})();

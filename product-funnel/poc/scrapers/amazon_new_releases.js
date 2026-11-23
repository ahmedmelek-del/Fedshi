// Scrape Amazon lists (Hot New Releases, Movers & Shakers, Best Sellers) for Fedshi-relevant categories.
// Works for amazon.com and the Gulf stores (amazon.ae, amazon.sa), which are one step closer to Iraq.
//
// Usage: node scrapers/amazon_new_releases.js data/amazon_new_releases.json
// Environment (all optional):
//   HOST=www.amazon.ae          store (default www.amazon.com)
//   LIST=new-releases           new-releases | movers-and-shakers | bestsellers
//   CATS=kitchen,automotive     category slugs (defaults depend on the store)
// Prices are converted to USD in "price" (AED ÷ 3.67, SAR ÷ 3.75); "price_local" keeps the original.
const { chromium } = require('playwright');
const fs = require('fs');

const HOST = process.env.HOST || 'www.amazon.com';
const LIST = process.env.LIST || 'new-releases';
const GULF = /amazon\.(ae|sa)$/.test(HOST);
// Category slugs differ per store (read from each store's own New Releases menu).
// Dropped everywhere: fashion (clothing) and pets (not a market in Iraq).
const STORE_CATS = {
  'www.amazon.com': ['home-garden', 'kitchen', 'automotive', 'hi', 'baby-products', 'electronics', 'sporting-goods',
    'office-products', 'lawn-garden', 'toys-and-games', 'wireless', 'beauty', 'arts-crafts', 'pc', 'photo'],
  'www.amazon.ae': ['home', 'kitchen', 'automotive', 'electronics', 'baby', 'beauty', 'health', 'office-products', 'toys',
    'computers', 'mobile-phones', 'sports-goods', 'home-improvement'],
  'www.amazon.sa': ['home', 'automotive', 'electronics', 'baby-products', 'beauty', 'health', 'office-products', 'toys',
    'sports-goods', 'home-improvement', 'garden'],
};
const DEFAULT_CATS = STORE_CATS[HOST] || STORE_CATS['www.amazon.com'];
const CATS = (process.env.CATS ? process.env.CATS.split(',') : DEFAULT_CATS).map(s => s.trim()).filter(Boolean);
const SOURCE = `amazon_${HOST.split('.').pop() === 'com' ? 'us' : HOST.split('.').pop()}_${LIST.replace(/-/g, '_')}`;
const TO_USD = { AED: 1 / 3.67, SAR: 1 / 3.75, '$': 1 };

async function passInterstitial(page) {
  // amazon.sa sometimes shows a "continue shopping" page before the list.
  if ((await page.$$('[id="gridItemRoot"]')).length) return;
  const btn = await page.$('button, input[type="submit"]');
  if (btn) { await btn.click().catch(() => {}); await page.waitForTimeout(3000); }
}

async function scrapePage(page) {
  for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 3000); await page.waitForTimeout(700); }
  return page.$$eval('[id="gridItemRoot"]', (els, host) => els.map(root => {
    const asin = root.querySelector('[data-asin]')?.getAttribute('data-asin') || '';
    const img = root.querySelector('img');
    const text = root.innerText;
    const m = text.match(/(AED|SAR|\$)\s?([\d,]+(?:\.\d+)?)/);
    return {
      asin,
      url: asin ? `https://${host}/dp/${asin}` : '',
      rank: Number((text.match(/#(\d+)/) || [])[1] || 0),
      title: (img?.getAttribute('alt') || '').trim(),
      image: img?.getAttribute('src') || '',
      currency: m ? m[1] : '',
      amount: m ? Number(m[2].replace(/,/g, '')) : null,
      gain: (text.match(/([\d,]+)%/) || [])[1] || '',
      rating: Number((text.match(/([\d.]+) out of 5/) || [])[1] || 0),
      reviews: Number(((text.match(/out of 5 stars\s*([\d,]+)/) || [])[1] || '0').replace(/,/g, '')),
    };
  }), HOST);
}

(async () => {
  const out = [];
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    locale: 'en-US',
  });
  const lang = GULF ? 'language=en_AE&' : '';
  for (const cat of CATS) {
    const seen = new Set();
    for (const pg of [1, 2]) {
      const page = await ctx.newPage();
      try {
        const url = `https://${HOST}/gp/${LIST}/${cat}?${lang}pg=${pg}`;
        await page.goto(url, { timeout: 45000, waitUntil: 'domcontentloaded' });
        await passInterstitial(page);
        if (!(await page.$$('[id="gridItemRoot"]')).length) {
          await page.goto(url, { timeout: 45000, waitUntil: 'domcontentloaded' });
        }
        for (const it of await scrapePage(page)) {
          if (!it.asin || seen.has(it.asin)) continue;
          seen.add(it.asin);
          const usd = it.amount != null && TO_USD[it.currency] ? +(it.amount * TO_USD[it.currency]).toFixed(2) : null;
          out.push({ source: SOURCE, host: HOST, list: LIST, category: cat, ...it,
            price: usd != null ? `$${usd}` : '', price_local: it.amount != null ? `${it.currency} ${it.amount}` : '' });
        }
      } catch (e) { console.error(cat, pg, 'ERR', e.message.split('\n')[0]); }
      await page.close();
    }
    console.error(HOST, LIST, cat, seen.size);
  }
  await browser.close();
  fs.writeFileSync(process.argv[2] || 'data/amazon_new_releases.json', JSON.stringify(out, null, 1));
  console.error('total', out.length);
})();

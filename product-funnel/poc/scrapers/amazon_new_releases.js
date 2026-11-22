// Scrape Amazon "Hot New Releases" (new products already selling) for Fedshi-relevant categories.
// Movers & Shakers returns an empty list to headless browsers, so New Releases is the Amazon signal.
// Usage: node scrapers/amazon_new_releases.js data/amazon_new_releases.json
const { chromium } = require('playwright');
const fs = require('fs');

// Override with CATS=a,b,c in the environment.
const CATS = (process.env.CATS || [
  'home-garden', 'kitchen', 'automotive', 'hi', 'pet-supplies', 'baby-products',
  'electronics', 'sporting-goods', 'office-products', 'lawn-garden', 'toys-and-games', 'wireless',
  // beauty: tools only survive the filters; fashion: accessories only (bags, watches, jewellery boxes).
  'beauty', 'arts-crafts', 'pc', 'photo', 'fashion',
].join(',')).split(',').map(s => s.trim()).filter(Boolean);

async function scrapePage(page) {
  for (let i = 0; i < 8; i++) { await page.mouse.wheel(0, 3000); await page.waitForTimeout(700); }
  return page.$$eval('[id="gridItemRoot"]', els => els.map(root => {
    const asin = root.querySelector('[data-asin]')?.getAttribute('data-asin') || '';
    const img = root.querySelector('img');
    const text = root.innerText;
    return {
      asin,
      url: asin ? `https://www.amazon.com/dp/${asin}` : '',
      rank: Number((text.match(/#(\d+)/) || [])[1] || 0),
      title: (img?.getAttribute('alt') || '').trim(),
      image: img?.getAttribute('src') || '',
      price: (text.match(/\$[\d,.]+/) || [''])[0],
      rating: Number((text.match(/([\d.]+) out of 5/) || [])[1] || 0),
      reviews: Number(((text.match(/out of 5 stars\s*([\d,]+)/) || [])[1] || '0').replace(/,/g, '')),
    };
  }));
}

(async () => {
  const out = [];
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    locale: 'en-US',
  });
  for (const cat of CATS) {
    const seen = new Set();
    for (const pg of [1, 2]) {
      const page = await ctx.newPage();
      try {
        await page.goto(`https://www.amazon.com/gp/new-releases/${cat}?pg=${pg}`, { timeout: 45000, waitUntil: 'domcontentloaded' });
        for (const it of await scrapePage(page)) {
          if (it.asin && !seen.has(it.asin)) { seen.add(it.asin); out.push({ source: 'amazon_new_releases', category: cat, ...it }); }
        }
      } catch (e) { console.error(cat, pg, 'ERR', e.message.split('\n')[0]); }
      await page.close();
    }
    console.error(cat, seen.size);
  }
  await browser.close();
  fs.writeFileSync(process.argv[2] || 'data/amazon_new_releases.json', JSON.stringify(out, null, 1));
  console.error('total', out.length);
})();

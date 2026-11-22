// Look up China retail price + units sold on AliExpress for each shortlisted item.
// AliExpress price is a conservative stand-in for 1688 factory cost (1688 is usually 30–50% lower).
// Usage: node scrapers/aliexpress_search.js shortlist.json data/aliexpress.json
const { chromium } = require('playwright');
const fs = require('fs');

function parseSold(s) {
  const m = (s || '').replace(/,/g, '').match(/([\d.]+)\s*(k)?\+?\s*sold/i);
  if (!m) return 0;
  return Math.round(parseFloat(m[1]) * (m[2] ? 1000 : 1));
}

(async () => {
  const items = JSON.parse(fs.readFileSync(process.argv[2]));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    locale: 'en-US',
  });
  const out = {};
  for (const it of items) {
    const page = await ctx.newPage();
    const q = it.query;
    try {
      await page.goto(`https://www.aliexpress.com/w/wholesale-${encodeURIComponent(q.replace(/\s+/g, '-'))}.html?SortType=total_tranpro_desc`,
        { timeout: 45000, waitUntil: 'domcontentloaded' });
      for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, 2500); await page.waitForTimeout(800); }
      const cards = await page.$$eval('a[href*="/item/"]', as => as.map(a => ({
        href: a.href.split('?')[0], text: a.innerText.replace(/\s+/g, ' ').trim(),
        img: a.querySelector('img')?.src || '',
      })).filter(c => c.text.includes('$')));
      const seen = new Set();
      const results = [];
      for (const c of cards) {
        if (seen.has(c.href)) continue; seen.add(c.href);
        const prices = [...c.text.matchAll(/\$\s?([\d,]+\.\d{2})/g)].map(m => parseFloat(m[1].replace(/,/g, '')));
        // First price is the shown price. A much higher second price means a new-shopper "welcome deal"
        // (e.g. $1.09 vs $12.25), which isn't a real repeat-buy cost, so mark it.
        const welcomeDeal = prices.length > 1 && prices.some(p => p > prices[0] * 4);
        results.push({ url: c.href, title: c.text.split(/\d[\d.,]*k?\+? sold/i)[0].slice(0, 140).trim(),
          price: prices[0] || null, prices, welcomeDeal, sold: parseSold(c.text), image: c.img });
        if (results.length >= 10) break;
      }
      out[it.id] = { query: q, results };
      console.error(it.id, q, results.length);
    } catch (e) { console.error(it.id, 'ERR', e.message.split('\n')[0]); out[it.id] = { query: q, results: [] }; }
    await page.close();
  }
  await browser.close();
  fs.writeFileSync(process.argv[3], JSON.stringify(out, null, 1));
})();

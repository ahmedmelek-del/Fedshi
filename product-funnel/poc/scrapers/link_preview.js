// Read the public preview (title, description, image) of links added to the review page's inbox.
// Usage: node scrapers/link_preview.js '<json array of {id,url}>' out.json
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const links = JSON.parse(process.argv[2]);
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ locale: 'en-US' });
  const out = [];
  for (const { id, url } of links) {
    const page = await ctx.newPage();
    try {
      const r = await page.goto(url, { timeout: 45000, waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(4000);
      const meta = await page.evaluate(() => {
        const m = n => document.querySelector(`meta[property="${n}"], meta[name="${n}"]`)?.content || '';
        return { title: m('og:title') || document.title, description: m('og:description') || m('description'), image: m('og:image') };
      });
      out.push({ id, url, status: r && r.status(), finalUrl: page.url(), ...meta });
    } catch (e) {
      out.push({ id, url, error: e.message.split('\n')[0] });
    }
    await page.close();
  }
  await browser.close();
  fs.writeFileSync(process.argv[3], JSON.stringify(out, null, 1));
  for (const o of out) console.log(o.id, o.status || o.error, (o.title || '').slice(0, 90), '|', (o.description || '').slice(0, 200), '| img:', o.image ? 'yes' : 'no', '|', o.finalUrl || '');
})();

// UX sweep harness for Creative Command Center (read-only)
const { chromium } = require('playwright');
const fs = require('fs');

const OUT = '/home/tomas/fable-window/artifacts/ccc-ux';
const BASE = 'http://localhost:3000';

const PAGES = [
  ['performance-today', '/performance?tab=today'],
  ['performance', '/performance'],
  ['research', '/research'],
  ['winners', '/winners'],
  ['brain', '/brain'],
  ['reports', '/reports'],
  ['comments', '/comments'],
  ['swipe', '/swipe'],
  ['feedback', '/feedback'],
];

(async () => {
  const browser = await chromium.launch();
  const notes = [];

  for (const [vpName, vp] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 390, height: 844 }]]) {
    const ctx = await browser.newContext({ viewport: vp });
    const page = await ctx.newPage();
    const consoleErrs = [];
    page.on('console', m => { if (m.type() === 'error') consoleErrs.push(m.text().slice(0, 300)); });
    page.on('pageerror', e => consoleErrs.push('PAGEERROR: ' + String(e).slice(0, 300)));

    for (const [name, path] of PAGES) {
      consoleErrs.length = 0;
      const t0 = Date.now();
      try {
        await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 45000 }).catch(async () => {
          await page.waitForTimeout(3000);
        });
        await page.waitForTimeout(1500);
        const loadMs = Date.now() - t0;
        await page.screenshot({ path: `${OUT}/${vpName}-${name}-fold.png` });
        await page.screenshot({ path: `${OUT}/${vpName}-${name}-full.png`, fullPage: true });
        // capture visible text skeleton
        const info = await page.evaluate(() => {
          const heads = [...document.querySelectorAll('h1,h2,h3')].slice(0, 30).map(h => h.tagName + ': ' + h.innerText.trim().slice(0, 120));
          const body = document.body.innerText.slice(0, 4000);
          const hscroll = document.documentElement.scrollWidth > document.documentElement.clientWidth;
          return { title: document.title, heads, body, hscroll, scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth };
        });
        notes.push({ vp: vpName, name, path, loadMs, hscroll: info.hscroll, scrollWidth: info.scrollWidth, clientWidth: info.clientWidth, title: info.title, heads: info.heads, consoleErrs: [...consoleErrs], bodyPreview: info.body });
      } catch (e) {
        notes.push({ vp: vpName, name, path, error: String(e).slice(0, 500), consoleErrs: [...consoleErrs] });
      }
    }
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(`${OUT}/sweep-notes.json`, JSON.stringify(notes, null, 2));
  console.log('done', notes.length, 'entries');
})().catch(e => { console.error(e); process.exit(1); });

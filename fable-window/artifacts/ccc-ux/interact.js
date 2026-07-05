// Interactive UX pass (read-only; never clicks Confirm on write actions)
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = '/home/tomas/fable-window/artifacts/ccc-ux';
const BASE = 'http://localhost:3000';
const notes = [];
const note = (k, v) => { notes.push({ [k]: v }); console.log(k, JSON.stringify(v).slice(0, 300)); };

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // A. Warm-load timing of Today (3 hits)
  for (let i = 1; i <= 3; i++) {
    const t0 = Date.now();
    await page.goto(BASE + '/performance?tab=today', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
    note('today-warm-load-ms-' + i, Date.now() - t0);
  }

  // B. Is the "28 kill" digest text clickable? Does a kill list exist?
  const digestClickable = await page.evaluate(() => {
    const el = [...document.querySelectorAll('a,button')].find(e => /kill/i.test(e.innerText || ''));
    return el ? el.innerText.slice(0, 60) : null;
  });
  note('digest-kill-clickable-element', digestClickable);

  // C. Click Iterate Next row chevron
  const iterRow = page.locator('text=INTRO').first();
  if (await iterRow.count()) {
    await iterRow.click().catch(e => note('iterate-click-err', String(e).slice(0, 200)));
    await page.waitForTimeout(2500);
    await page.screenshot({ path: OUT + '/flow-iterate-next-click.png' });
    note('iterate-next-after-click-url', page.url());
  }

  // D. Click first KILL row in Just Launched
  await page.goto(BASE + '/performance?tab=today', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  const killBtn = page.locator('text=KILL').first();
  if (await killBtn.count()) {
    await killBtn.click().catch(e => note('kill-click-err', String(e).slice(0, 200)));
    await page.waitForTimeout(2500);
    await page.screenshot({ path: OUT + '/flow-kill-row-click.png', fullPage: false });
    note('kill-after-click-url', page.url());
    const overlayText = await page.evaluate(() => document.body.innerText.slice(0, 1200));
    fs.writeFileSync(OUT + '/flow-kill-row-text.txt', overlayText);
  }

  // E. Research > Queue tab
  await page.goto(BASE + '/research', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.locator('button:has-text("Queue"), a:has-text("Queue")').first().click().catch(e => note('queue-tab-err', String(e).slice(0, 150)));
  await page.waitForTimeout(2500);
  await page.screenshot({ path: OUT + '/flow-research-queue.png', fullPage: true });
  const queueText = await page.evaluate(() => document.body.innerText.slice(0, 3000));
  fs.writeFileSync(OUT + '/flow-research-queue-text.txt', queueText);

  // Open Generate brief modal if present (do NOT submit)
  const genBtn = page.locator('button:has-text("Generate brief"), button:has-text("generate brief")').first();
  if (await genBtn.count()) {
    await genBtn.click().catch(() => {});
    await page.waitForTimeout(1500);
    await page.screenshot({ path: OUT + '/flow-generate-brief-modal.png' });
    note('generate-brief-modal', 'opened');
    await page.keyboard.press('Escape');
  } else {
    note('generate-brief-modal', 'no trigger button found on queue tab');
  }

  // F. Lanes: count Brief-this-lane buttons, then View evidence link
  await page.goto(BASE + '/research', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.locator('button:has-text("Lanes")').first().click().catch(() => {});
  await page.waitForTimeout(1500);
  const briefBtns = await page.locator('button:has-text("Brief this lane")').count();
  note('brief-this-lane-button-count', briefBtns);
  const evidence = page.locator('a:has-text("View evidence")').first();
  if (await evidence.count()) {
    const href = await evidence.getAttribute('href');
    note('view-evidence-href', href);
    await evidence.click();
    await page.waitForTimeout(3500);
    await page.screenshot({ path: OUT + '/flow-view-evidence.png', fullPage: false });
    note('view-evidence-url', page.url());
    const evText = await page.evaluate(() => document.body.innerText.slice(0, 2000));
    fs.writeFileSync(OUT + '/flow-view-evidence-text.txt', evText);
  }

  // G. Persona 3: editor deep link to one creative
  await ctx.clearCookies();
  const editorCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } }); // fresh, no localStorage
  const ep = await editorCtx.newPage();
  const t0 = Date.now();
  await ep.goto(BASE + '/performance?tab=ads&sh=SH-16358', { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {});
  note('editor-deeplink-load-ms', Date.now() - t0);
  await ep.waitForTimeout(2000);
  await ep.screenshot({ path: OUT + '/flow-editor-deeplink.png', fullPage: false });
  const eText = await ep.evaluate(() => document.body.innerText.slice(0, 2500));
  fs.writeFileSync(OUT + '/flow-editor-deeplink-text.txt', eText);
  await editorCtx.close();

  // H. Reports: click the data-health badge
  await page.goto(BASE + '/reports', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  const health = page.locator('text=data:').first();
  if (await health.count()) {
    await health.click().catch(() => {});
    await page.waitForTimeout(1200);
    await page.screenshot({ path: OUT + '/flow-health-popover.png' });
  }

  // I. Swipe: Adapt this -> confirm state (do NOT confirm)
  await page.goto(BASE + '/research', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page.locator('button:has-text("Swipe")').first().click().catch(() => {});
  await page.waitForTimeout(3000);
  const adapt = page.locator('button:has-text("Adapt this")').first();
  if (await adapt.count()) {
    await adapt.click().catch(() => {});
    await page.waitForTimeout(800);
    await page.screenshot({ path: OUT + '/flow-adapt-confirm.png' });
    const confirmVisible = await page.locator('button:has-text("Confirm")').count();
    note('adapt-confirm-visible', confirmVisible);
    // back out
    await page.locator('button:has-text("x")').first().click().catch(() => {});
  }

  // J. Command palette
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(800);
  await page.screenshot({ path: OUT + '/flow-cmdk.png' });

  await browser.close();
  fs.writeFileSync(OUT + '/interact-notes.json', JSON.stringify(notes, null, 2));
  console.log('interactive pass done');
})().catch(e => { console.error(e); process.exit(1); });

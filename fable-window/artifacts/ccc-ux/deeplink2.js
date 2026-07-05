const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  await p.goto('http://localhost:3000/performance?tab=ads&sh=SH-13107', { waitUntil: 'networkidle', timeout: 90000 }).catch(()=>{});
  await p.waitForTimeout(2500);
  await p.screenshot({ path: 'flow-editor-deeplink-old.png' });
  const txt = await p.evaluate(() => document.body.innerText);
  console.log('showing line:', (txt.match(/Showing[^\n]*/)||[''])[0]);
  console.log('has SH-13107 card:', /SH-13107/.test(txt.replace('SH-13107','',1)));
  // count cards
  console.log('body excerpt:', txt.slice(txt.indexOf('Showing'), txt.indexOf('Showing')+400).replace(/\n/g,' | ').slice(0,400));
  await b.close();
})();

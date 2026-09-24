// Print the rendered text of a JavaScript-drawn page (cat8 run 5 prompt §2; audits 22-25).
// Usage: NODE_PATH=/opt/node22/lib/node_modules NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt node scripts/cat8_render.js <URL> [wait_ms]
// Outbound HTTPS goes through the session proxy, which re-terminates TLS with its own CA.
// Chromium does not trust that CA, and flags that make it accept the CA also skip other checks
// (audit 23: hostname mismatch passed). So HTTP(S) requests of the page are intercepted and
// fetched by Playwright's Node side, which verifies TLS normally against NODE_EXTRA_CA_CERTS
// (the proxy's bundle), then handed back to the page. Service workers are blocked and
// WebSockets are closed (audit 24).
// Completeness is not assumed. What is counted as an `INCOMPLETE` line (audits 25-26):
//   - each request seen by route() (tracked per request, not per URL) that failed or had not
//     finished when the text was taken; websockets; failed requests; page-load errors;
//   - the page text changing between the first read (after wait_ms) and a second read
//     (after another max(2*wait_ms, 8 s)), which catches late content whatever its path.
// The last line is always `INCOMPLETE 合計 <N> 件`. What is NOT covered: requests the page
// never started (e.g. service workers are blocked, so their fetches never happen), content
// that arrives after the second read, and text drawn without the DOM (canvas, images).
// So N = 0 does not prove the text is the whole page.
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2];
  const wait = parseInt(process.argv[3] || '3000', 10);
  if (!url) { console.error('usage: cat8_render.js <URL> [wait_ms]'); process.exit(2); }
  const incomplete = [];
  const pending = new Map();
  let nextId = 0;
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  try {
    const context = await browser.newContext({
      proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined,
      serviceWorkers: 'block',
    });
    await context.routeWebSocket(/.*/, (ws) => {
      incomplete.push('websocket ' + ws.url());
      ws.close();
    });
    await context.route('**/*', async (route) => {
      const u = route.request().url();
      const id = nextId++;
      pending.set(id, u);
      try {
        await route.fulfill({ response: await route.fetch() });
      } catch (e) {
        incomplete.push('fetch-failed ' + u + ' ' + String(e).split('\n')[0]);
        await route.abort().catch(() => {});
      } finally {
        pending.delete(id);
      }
    });
    const page = await context.newPage();
    try {
      page.on('requestfailed', (r) => incomplete.push('request-failed ' + r.url() + ' ' + (r.failure() ? r.failure().errorText : '')));
      const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(wait);
      const first = await page.evaluate(() => document.body.innerText);
      await page.waitForTimeout(Math.max(wait * 2, 8000));
      const second = await page.evaluate(() => document.body.innerText);
      console.log('HTTP ' + (res ? res.status() : 'NA') + ' ' + page.url());
      console.log(second);
      if (first !== second) incomplete.push('text-changed-after-wait (' + first.length + ' -> ' + second.length + ' chars)');
    } catch (e) {
      incomplete.push('error ' + String(e).split('\n')[0]);
      process.exitCode = 1;
    }
    for (const u of pending.values()) incomplete.push('pending ' + u);
  } finally {
    for (const line of incomplete) console.log('INCOMPLETE ' + line);
    console.log('INCOMPLETE 合計 ' + incomplete.length + ' 件');
    await browser.close();
  }
})().catch(e => { console.log('INCOMPLETE error ' + String(e).split('\n')[0]); process.exit(1); });

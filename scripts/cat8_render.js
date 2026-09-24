// Print the rendered text of a JavaScript-drawn page (cat8 run 5 prompt §2; audit 22 finding 2).
// Usage: NODE_PATH=/opt/node22/lib/node_modules NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt node scripts/cat8_render.js <URL> [wait_ms]
// Outbound HTTPS goes through the session proxy, which re-terminates TLS with its own CA.
// Chromium does not trust that CA, and flags that make it accept the CA also skip other checks
// (audit 23: hostname mismatch passed). So HTTP(S) requests of the page are intercepted and
// fetched by Playwright's Node side, which verifies TLS normally against NODE_EXTRA_CA_CERTS
// (the proxy's bundle), then handed back to the page.
// Paths that route() does not cover (audit 24): service workers are blocked, WebSockets are
// closed by routeWebSocket, and any request that still fails is printed as a BLOCKED/FAILED
// line, so a page whose text depends on those paths shows it in the output instead of silently.
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2];
  const wait = parseInt(process.argv[3] || '3000', 10);
  if (!url) { console.error('usage: cat8_render.js <URL> [wait_ms]'); process.exit(2); }
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  try {
    const context = await browser.newContext({
      proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined,
      serviceWorkers: 'block',
    });
    await context.routeWebSocket(/.*/, (ws) => {
      console.error('BLOCKED websocket: ' + ws.url());
      ws.close();
    });
    await context.route('**/*', async (route) => {
      try {
        await route.fulfill({ response: await route.fetch() });
      } catch (e) {
        console.error('fetch failed: ' + route.request().url() + ' ' + String(e).split('\n')[0]);
        await route.abort();
      }
    });
    const page = await context.newPage();
    page.on('requestfailed', (r) => console.error('FAILED request: ' + r.url() + ' ' + (r.failure() ? r.failure().errorText : '')));
    const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(wait);
    console.log('HTTP ' + (res ? res.status() : 'NA') + ' ' + page.url());
    console.log(await page.evaluate(() => document.body.innerText));
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(String(e)); process.exit(1); });

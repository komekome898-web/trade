// Print the rendered text of a JavaScript-drawn page (cat8 run 5 prompt §2; audit 22 finding 2).
// Usage: NODE_PATH=/opt/node22/lib/node_modules node scripts/cat8_render.js <URL> [wait_ms]
// Outbound HTTPS goes through the session proxy, which re-terminates TLS with its own CA
// (/root/.ccr/agent-proxy-ca.crt). Chromium does not read that CA from the environment, so
// only that CA's public key is trusted via --ignore-certificate-errors-spki-list; every other
// certificate is still verified normally.
const { chromium } = require('playwright');
const crypto = require('crypto');
const fs = require('fs');
const CA = '/root/.ccr/agent-proxy-ca.crt';
(async () => {
  const url = process.argv[2];
  const wait = parseInt(process.argv[3] || '3000', 10);
  if (!url) { console.error('usage: cat8_render.js <URL> [wait_ms]'); process.exit(2); }
  const args = [];
  if (fs.existsSync(CA)) {
    const spki = new crypto.X509Certificate(fs.readFileSync(CA)).publicKey.export({ type: 'spki', format: 'der' });
    args.push('--ignore-certificate-errors-spki-list=' + crypto.createHash('sha256').update(spki).digest('base64'));
  }
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium',
    proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined,
    args,
  });
  try {
    const page = await browser.newPage();
    const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(wait);
    console.log('HTTP ' + (res ? res.status() : 'NA') + ' ' + page.url());
    console.log(await page.evaluate(() => document.body.innerText));
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(String(e)); process.exit(1); });

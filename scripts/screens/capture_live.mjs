// Read-only screenshots of the saved live case (Keppel REIT). Start it first: scripts/demo/serve.sh --keppel
//   node scripts/screens/capture_live.mjs http://127.0.0.1:15300
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { fileURLToPath } from 'node:url'

const base = process.argv[2] || 'http://127.0.0.1:15300'
const out = fileURLToPath(new URL('../../docs/screens/', import.meta.url))
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const errors = []
async function shot(name, hash, viewport, { scale = 1, fullPage = false, before } = {}) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: scale })
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`))
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('favicon.ico')) errors.push(`${name}: ${r.status()} ${r.url()}`) })
  await page.goto(`${base}/${hash}`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(800)
  if (before) await before(page)
  await page.screenshot({ path: `${out}live_${name}.png`, fullPage })
  await page.close()
}
const desktop = { width: 1440, height: 900 }, phone = { width: 390, height: 844 }
// Full-page shots need the panes to grow with their content instead of scrolling inside the window.
const unroll = page => page.addStyleTag({ content: '.wb{height:auto;overflow:visible}.shell,.centre{overflow:visible}.rail,.panel{position:sticky;top:0;height:100vh}' })
await shot('01_inputs', '#/inputs', desktop, { fullPage: true, before: unroll })
await shot('02_full_es', '#/workbench/full', desktop)
await shot('03_section_2', '#/workbench/2', desktop)
await shot('04_section_4', '#/workbench/4', desktop, { fullPage: true, before: unroll })
await shot('05_section_8', '#/workbench/8', desktop, { fullPage: true, before: unroll })
await shot('06_section_10', '#/workbench/10', desktop, { fullPage: true, before: unroll })
await shot('07_section_12', '#/workbench/12', desktop)
await shot('08_section_14', '#/workbench/14', desktop, { fullPage: true, before: unroll })
await shot('09_phone_section_4', '#/workbench/4', phone, { scale: 2 })
await browser.close()
console.log(errors.length ? `Problems:\n${errors.join('\n')}` : 'Captured 9 screens, no page errors')
if (errors.length) process.exit(1)

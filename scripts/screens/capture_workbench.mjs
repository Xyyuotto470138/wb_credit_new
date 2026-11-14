// Screenshot pack for the 2.14 screens, taken from a running demo (scripts/demo/serve.sh --prepared).
//   node scripts/screens/capture_workbench.mjs http://127.0.0.1:15300
// Also exercises Edit text, Sources and the Credit Assistant on section 1, so the case is changed.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { fileURLToPath } from 'node:url'
import assert from 'node:assert/strict'

const base = process.argv[2] || 'http://127.0.0.1:15300'
const out = fileURLToPath(new URL('../../docs/screens/', import.meta.url))
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const errors = []
async function open(hash, viewport, scale = 1) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: scale })
  page.on('pageerror', e => errors.push(`${hash}: ${e.message}`))
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('favicon.ico')) errors.push(`${hash}: ${r.status()} ${r.url()}`) })
  await page.goto(`${base}/${hash}`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(500)
  return page
}
const idle = page => page.locator('.wb-busy').waitFor({ state: 'hidden', timeout: 120000 })
const shot = (page, name, fullPage = false) => page.screenshot({ path: `${out}wb_${name}.png`, fullPage })
const desktop = { width: 1440, height: 900 }, phone = { width: 390, height: 844 }

let page = await open('#/inputs', desktop)
await shot(page, '01_inputs'); await page.close()
page = await open('#/workbench/full', desktop)
await shot(page, '02_full_es'); await page.close()

page = await open('#/workbench/1', desktop)
await shot(page, '03_section')
await page.locator('sup.cite').first().click(); await page.locator('.source.on').waitFor()
await shot(page, '04_sources')
await page.locator('.tabs button', { hasText: 'Credit Assistant' }).click()
await page.getByRole('button', { name: 'Edit text' }).click()
const wording = page.getByLabel('Section wording').first()
await wording.fill((await wording.inputValue()) + ' Wording reviewed by the CA.')
await shot(page, '05_edit_text')
await page.getByRole('button', { name: 'Save wording' }).click(); await idle(page)
await page.getByText(/Version 2 ·/).waitFor()
assert.ok(await page.getByText('Wording reviewed by the CA.').count(), 'manual edit saved as a new version')
await page.getByLabel('Message to the Credit Assistant').fill('The RM has confirmed the request with the client.')
await page.getByRole('button', { name: 'Send' }).click(); await page.locator('.change').waitFor(); await idle(page)
await shot(page, '06_tracked_change')
await page.getByRole('button', { name: 'Reject' }).click(); await idle(page); await page.locator('.change').waitFor({ state: 'hidden' })
assert.equal(await page.getByText('The RM has confirmed the request').count(), 1, 'rejected change is only in the chat, not the section')
await page.getByRole('button', { name: 'History' }).click()
await shot(page, '07_version_history')
await page.getByRole('button', { name: 'History' }).click()
await page.getByRole('button', { name: 'Confirm section' }).click(); await idle(page)
await page.locator('.rail a.on .dot.ok').waitFor()
await shot(page, '08_confirmed'); await page.close()

page = await open('#/workbench/10', desktop)
await shot(page, '09_section_10', true); await page.close()
page = await open('#/workbench/12', desktop)
await shot(page, '10_pending_inputs'); await page.close()
page = await open('#/inputs', phone, 2)
await shot(page, '11_phone_inputs'); await page.close()
page = await open('#/workbench/8', phone, 2)
await shot(page, '12_phone_section')
await page.getByRole('button', { name: /Credit Assistant/ }).click()
await shot(page, '13_phone_assistant'); await page.close()
await browser.close()
console.log(errors.length ? `Problems:\n${errors.join('\n')}` : 'Captured 13 screens, no page errors')
if (errors.length) process.exit(1)

// Development-only visual walkthrough. All case mutations use the actual UI.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { spawn } from 'node:child_process'
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises'
import { createWriteStream } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import assert from 'node:assert/strict'

const root = fileURLToPath(new URL('../../', import.meta.url))
const output = path.join(root, 'docs/screens')
const base = path.join(root, 'runtime/0024')
await mkdir(base, { recursive: true })
await mkdir(output, { recursive: true })
const runDir = await mkdtemp(path.join(base, 'capture-'))
await mkdir(path.join(runDir, 'tmp'))
const env = { ...process.env, LLM_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1', TMPDIR: path.join(runDir, 'tmp') }
const children = []
let browser
let page
const shots = []
const errors = []
const blocked = []
const appUrl = 'http://127.0.0.1:15124'
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
async function stop() {
  await browser?.close().catch(() => {})
  for (const child of children.reverse()) {
    if (child.exitCode !== null || child.signalCode !== null) continue
    child.kill('SIGTERM')
    await Promise.race([new Promise(resolve => child.once('exit', resolve)), delay(5000)])
    if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL')
  }
}
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => { await stop(); process.exit(1) })
function start(command, args, name, cwd = root) {
  const child = spawn(command, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] })
  const log = createWriteStream(path.join(runDir, `${name}.log`))
  child.stdout.pipe(log); child.stderr.pipe(log)
  child.on('error', error => errors.push(`${name}: ${error.message}`))
  children.push(child)
  return child
}
async function available(url) {
  try { await fetch(url, { signal: AbortSignal.timeout(1000) }); return true } catch { return false }
}
async function waitServer(url, child) {
  for (let i = 0; i < 120; i++) {
    if (child.exitCode !== null) throw new Error(`Server exited: ${url}; see ${runDir}`)
    if (await available(url)) return
    await delay(500)
  }
  throw new Error(`Server did not start: ${url}`)
}
async function idle() {
  await page.locator('main[aria-busy="false"]').waitFor({ timeout: 120000 })
  await page.waitForLoadState('networkidle')
  assert.equal(await page.locator('.error[role="alert"]').count(), 0, 'UI action error')
}
async function click(name, scope = page) {
  await scope.getByRole('button', { name, exact: true }).click({ timeout: 120000 })
  await idle()
}
async function frame(locator) {
  await locator.evaluate(el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 24))
}
async function shot(slug, caption, locator) {
  await idle()
  await page.getByText('Loading section…', { exact: true }).waitFor({ state: 'hidden' })
  await page.getByText('Loading chat history…', { exact: true }).waitFor({ state: 'hidden' })
  if (locator) await frame(locator)
  else await page.evaluate(() => window.scrollTo(0, 0))
  await page.evaluate(() => document.fonts.ready)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false, `Page overflow: ${slug}`)
  const filename = `${String(shots.length + 1).padStart(2, '0')}_${slug}.png`
  await page.screenshot({ path: path.join(output, filename), animations: 'disabled' })
  shots.push({ filename, caption })
  await writeFile(path.join(runDir, 'shots.json'), JSON.stringify(shots, null, 2))
  console.log(`${filename}: ${caption}`)
}
async function scan(n) {
  await page.locator('.folder-intake select').selectOption(`tranche_${n}`)
  await click('Scan folder')
}
async function select(n) {
  await page.locator('#section-editor > .toolbar select').selectOption(String(n))
  await page.getByText('Loading section…', { exact: true }).waitFor({ state: 'hidden' })
  await idle()
  const reload = page.getByRole('button', { name: 'Reload section', exact: true })
  if (await page.getByText('The section or its inputs changed,', { exact: false }).count()) await reload.click()
  await idle()
}
async function snapshot() {
  const res = await page.request.get(`${appUrl}/api/cases`)
  const cases = await res.json()
  const data = await page.request.get(`${appUrl}/api/cases/${cases[0].id}/dashboard`)
  assert.equal(data.ok(), true)
  return data.json()
}
async function draft(n, onlyStale = false) {
  await select(n)
  const data = await snapshot()
  const section = data.sections.find(s => s.section_id === n)
  if (onlyStale && section.current_draft_id && section.readiness !== 'Stale') return
  // History mounts after the editor fetch. Finish that read before starting a
  // write, particularly on the large section-11 dependency chain.
  if (section.current_draft_id) {
    await page.locator('.section-chat').waitFor()
    await page.getByText('Loading chat history…', { exact: true }).waitFor({ state: 'hidden' })
    await idle()
  }
  if ([7, 8].includes(n)) await page.getByLabel('I confirm the supplied term sheet’s unsecured description for the new draft.').check()
  if (n === 14) await page.getByLabel('CA-stated position for the new draft').fill('Defer pending evidence and legal review.')
  await click(section.current_draft_id ? 'Redraft as new version' : 'Create mock first draft')
  console.log(`Saved section ${n}`)
}
try {
  assert.equal(await available(appUrl), false, 'Port 15124 already in use; stop the existing server yourself before capture')
  assert.equal(await available('http://127.0.0.1:18024/health'), false, 'Port 18024 already in use')
  const api = start(path.join(root, '.venv/bin/python'), ['-c', 'import sys, uvicorn; from backend.app.local import create_demo_app; uvicorn.run(create_demo_app(sys.argv[1]), host="127.0.0.1", port=18024)', path.join(runDir, 'case')], 'backend')
  await waitServer('http://127.0.0.1:18024/health', api)
  const ui = start(process.execPath, ['node_modules/vite/bin/vite.js', '--config', '../scripts/screens/vite.config.mjs'], 'frontend', path.join(root, 'frontend'))
  await waitServer(appUrl, ui)
  browser = await chromium.launch({ ...(process.env.SCREEN_BROWSER === 'chromium' ? {} : { channel: 'chrome' }), headless: true, env })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce', serviceWorkers: 'block', acceptDownloads: true })
  await context.route('**/*', route => {
    const url = new URL(route.request().url())
    if (url.origin === appUrl || ['data:', 'blob:'].includes(url.protocol)) return route.continue()
    blocked.push(url.origin)
    return route.abort()
  })
  page = await context.newPage()
  page.setDefaultTimeout(30000)
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(appUrl)
  await page.getByRole('heading', { name: 'ESR-REIT', exact: true }).waitFor()
  await idle()
  await page.getByLabel('CA name', { exact: true }).fill('Demo Credit Analyst')
  await shot('empty_dashboard', 'Empty synthetic case: no inputs or saved sections; workflow remains Draft.')
  await shot('empty_progress', 'Empty draft progress, tranche coverage and document intake.', page.getByRole('region', { name: 'Saved draft progress' }))
  await page.getByText('Classification hints for uploads', { exact: true }).click()
  await shot('intake_options', 'Upload classification hints and configured tranche-folder scan.', page.locator('#intake'))
  await page.getByText('Classification hints for uploads', { exact: true }).click()
  await scan(1)
  await click('Check public sources')
  let data = await snapshot()
  for (const doc of data.documents.filter(d => d.origin === 'public')) {
    await page.locator('#documents').getByRole('button', { name: doc.original_filename, exact: true }).click()
    await page.locator('dialog canvas').waitFor()
    await page.waitForFunction(() => !!document.querySelector('dialog canvas')?.getAttribute('width'))
    if (!shots.some(s => s.filename.includes('public_source'))) await shot('public_source', 'Saved public PDF in the source dialog, with URL, retrieval date and explicit review action.', page.locator('dialog'))
    await click('Confirm public evidence reviewed', page.getByRole('dialog'))
    await click('Close', page.getByRole('dialog'))
  }
  await shot('tranche1_overview', 'Tranche 1 plus reviewed saved public evidence: provided, public and missing inputs.', page.locator('.case-heading'))
  await shot('tranche1_expected', 'Expected-input table distinguishes full inputs from partial public context.', page.locator('#expected'))
  await shot('tranche1_requests', 'Tranche 1 open requests grouped by RM, client and internal team.', page.locator('#requests'))
  await page.locator('#requests details').first().locator('summary').click()
  await shot('request_export', 'Request-list export action with the first request expanded; the download sends nothing.', page.locator('#requests'))
  const requestDownload = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Export request list', exact: true }).click()
  await (await requestDownload).saveAs(path.join(runDir, 'request-list.txt'))
  await click('Generate saved mock spread')
  await shot('generation_offers', 'Validated saved mock spread generated; industry-mapping offer remains unavailable.', page.locator('.generation-offers'))
  for (const n of [4, 5, 6, 7, 10, 8, 9]) await draft(n)
  await shot('tranche1_drafts', 'Seven saved partial/full sections after tranche 1; saved drafts are separate from readiness.', page.getByRole('region', { name: 'Saved draft progress' }))
  await select(4)
  await shot('section_editor', 'Section editor shows named gaps, sourced wording and original-page citation links.', page.locator('#section-editor'))
  await page.locator('.claim-sources button').first().click()
  await page.locator('dialog canvas').waitFor()
  await shot('cited_pdf', 'A section citation opens its original PDF page with public provenance.', page.locator('dialog'))
  await click('Close', page.getByRole('dialog'))
  await scan(2)
  await shot('tranche2_overview', 'Tranche 2 adds property and renewal support; earlier affected drafts become Stale.', page.locator('.case-heading'))
  for (const n of [1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11]) await draft(n)
  await shot('tranche2_drafts', 'Eleven saved sections after tranche 2; rating, conduct and conclusion remain outstanding.', page.getByRole('region', { name: 'Saved draft progress' }))
  await select(8)
  await page.getByLabel('CA fact or note (no numeric changes)').fill('Legal review remains pending.')
  await click('Propose revision')
  await shot('chat_proposal', 'Section chat proposes a cited revision for review before it changes the saved draft.', page.locator('.chat-proposal').first())
  await click('Reject revision')
  await shot('chat_rejected', 'Rejected proposal stays in chat history; saved wording is unchanged.', page.locator('.chat-proposal').first())
  await page.getByLabel('CA fact or note (no numeric changes)').fill('Legal review remains pending.')
  await click('Propose revision')
  await click('Accept revision')
  await shot('chat_accepted', 'Accepted revision records the analyst and creates a new version with CA-input provenance.', page.locator('.chat-proposal').first())
  const note = page.locator('.claim').filter({ hasText: 'Legal review remains pending.' }).last()
  await shot('accepted_note', 'The saved section includes the accepted synthetic CA note and its source link.', note)
  await note.locator('.claim-sources button').click()
  await page.locator('dialog .source-excerpt').waitFor()
  await shot('ca_input_source', 'CA-input source panel records the note, actor and time without implying a document page.', page.locator('dialog'))
  await click('Close', page.getByRole('dialog'))
  await page.locator('.version-history > summary').click()
  await page.locator('.version-history select').selectOption({ index: 1 })
  await shot('version_history', 'Read-only historical section version preserves its wording, model, template and sources.', page.locator('.version-history'))
  await scan(3)
  await shot('tranche3_overview', 'Tranche 3 supplies conduct and internal rating; missing-file count differs from mandatory gaps.', page.locator('.case-heading'))
  for (const n of [1, 2, 3, 4, 5, 6, 7, 8, 10, 9, 11, 12, 13]) await draft(n, true)
  await draft(14)
  data = await snapshot()
  assert.equal(data.sections.filter(s => s.current_draft_id).length, 14)
  assert.equal(data.sections.filter(s => s.readiness === 'Stale').length, 0)
  await shot('tranche3_complete', 'All fourteen sections saved; the industry-mapping gap remains visible and no approval is implied.', page.getByRole('region', { name: 'Saved draft progress' }))
  await shot('all_sections', 'All fourteen built ES sections remain navigable with their readiness and gap counts.', page.locator('#sections'))
  // Capture each distinct section with its first claims, plus computed/normalized source modes.
  for (let n = 1; n <= 14; n++) {
    await select(n)
    await shot(`section_${String(n).padStart(2, '0')}`, `Section ${n}: ${data.sections.find(s => s.section_id === n).name}; saved sourced draft for CA review.`, page.locator('#section-editor'))
    if (n === 2) {
      await shot('exposure_values', 'Exposure figures are read-only Python computations with synthetic source citations.', page.locator('.claim').first())
      await page.locator('.claim-sources button').first().click()
      await page.locator('dialog .source-excerpt').waitFor()
      await shot('workbook_source', 'Normalized workbook source panel with original-file download and synthetic provenance.', page.locator('dialog'))
      await click('Close', page.getByRole('dialog'))
    }
    if (n === 10) {
      await page.getByLabel(/^Revision type/).selectOption('numeric')
      await page.getByLabel(/^Metric/).selectOption({ index: 1 })
      await shot('numeric_chat', 'Section 10 numeric chat requires explicit sourced operands for Python recomputation.', page.locator('.section-chat'))
      await page.getByLabel(/^Revision type/).selectOption('fact')
    }
  }
  await select(8)
  await click('Confirm section reviewed')
  await shot('confirmed_section', 'CA confirmation records review while keeping named gaps open.', page.locator('#section-editor'))
  await click('Preview draft export')
  await shot('draft_export', 'Draft Word export preview pins the template, saved section versions and visible gaps.', page.locator('#draft-export'))
  await click('Create draft bundle')
  await shot('export_history', 'Saved draft bundle offers Word, source manifest and request-list downloads.', page.locator('#draft-export > h3'))
  const bundleDownload = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Download draft bundle', exact: true }).click()
  await (await bundleDownload).saveAs(path.join(runDir, 'draft-bundle.zip'))
  await shot('model_picker', 'Case-level model picker exposes offline mock choices and keeps all live routes disabled.', page.getByRole('heading', { name: 'Drafting model', exact: true }))
  await page.getByText('Configured model routes', { exact: true }).click()
  await shot('model_routes', 'Configured model route list labels disabled providers and unconfirmed deployment details.', page.getByRole('heading', { name: 'Drafting model', exact: true }))
  await page.getByText('Configured model routes', { exact: true }).click()
  await select(2)
  await click('Compare section drafts')
  await shot('model_compare', 'Side-by-side offline model comparison uses the same evidence and identical Python tables.', page.locator('.comparison-results'))
  await shot('compare_wording', 'Comparison wording retains each mock model’s citations and gaps; previews do not save a draft.', page.locator('.model-comparison pre').first())
  await page.locator('input[type="file"]').setInputFiles(path.join(root, 'demo/synthetic/late_update/valuation_v2.pdf'))
  await idle()
  data = await snapshot()
  assert.deepEqual(data.sections.filter(s => s.readiness === 'Stale').map(s => s.section_id), [8, 9, 11, 14])
  await shot('late_valuation_stale', 'Revised valuation makes sections 8, 9, 11 and 14 Stale while retaining saved versions.', page.getByRole('region', { name: 'Saved draft progress' }))
  await select(8)
  await shot('stale_editor', 'Stale editor explains the choice to keep wording for review or explicitly redraft.', page.locator('#section-editor'))
  await shot('redraft_choice', 'Explicit redraft action preserves historical wording and confirmation; reconfirmation is disabled while Stale.', page.locator('.editor-actions'))
  await page.getByLabel('I confirm the supplied term sheet’s unsecured description for the new draft.').check()
  await click('Redraft as new version')
  const revised = page.locator('.claim').filter({ hasText: '104' }).first()
  await shot('revised_security', 'Explicit redraft uses the revised synthetic SGD 104m valuation and retains source provenance.', revised)
  for (const n of [9, 11, 14]) await draft(n)
  await shot('refreshed_chain', 'After ordered redrafts, the affected chain is current; previous versions and exports remain.', page.getByRole('region', { name: 'Saved draft progress' }))
  await shot('document_register', 'Document register retains public/synthetic provenance and all twenty-three stored versions.', page.locator('#documents'))
  assert.deepEqual(errors, [])
  assert.deepEqual(blocked, [])
  await writeFile(path.join(output, 'capture.json'), JSON.stringify({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, browser: await browser.version(), capturedAt: new Date().toISOString(), errors, blockedExternalOrigins: blocked, shots }, null, 2) + '\n')
  console.log(`Completed ${shots.length} screenshots. Runtime: ${path.relative(root, runDir)}`)
} catch (error) {
  if (page) {
    await page.screenshot({ path: path.join(runDir, 'failure.png') }).catch(() => {})
    await writeFile(path.join(runDir, 'failure.txt'), await page.locator('body').innerText().catch(() => '')).catch(() => {})
  }
  throw error
} finally {
  await stop()
}

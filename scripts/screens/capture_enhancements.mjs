// Screens of the enhancement builds on the saved live case (Keppel REIT). This script CHANGES the case it runs on,
// so run it through scripts/screens/enhancements.sh, which backs the saved case up first and puts it back afterwards.
//   node scripts/screens/capture_enhancements.mjs http://127.0.0.1:15300 [blocks,sense,papers,review,update]
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { fileURLToPath } from 'node:url'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const base = process.argv[2] || 'http://127.0.0.1:15300'
const only = (process.argv[3] || 'blocks,sense,papers,review').split(',')
const out = fileURLToPath(new URL('../../docs/screens/', import.meta.url))
const work = fileURLToPath(new URL('../../runtime/shots/enhancements/', import.meta.url))
await mkdir(work, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const errors = []
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('pageerror', e => errors.push(e.message))
page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('favicon.ico')) errors.push(`${r.status()} ${r.url()}`) })
page.on('dialog', dialog => dialog.accept())
const open = async hash => { await page.goto('about:blank'); await page.goto(`${base}/${hash}`); await page.waitForLoadState('networkidle'); await page.waitForTimeout(700) }
const settle = async () => { await page.waitForSelector('.wb-busy', { state: 'detached', timeout: 120000 }).catch(() => {}); await page.waitForTimeout(600) }
const unroll = () => page.addStyleTag({ content: '.wb{height:auto;overflow:visible}.shell,.centre{overflow:visible}.rail,.panel{position:sticky;top:0;height:100vh}' })
const shot = async (name, options = {}) => { await page.screenshot({ path: `${out}enh_${name}.png`, ...options }) }
const paste = (selector, text) => page.evaluate(([selector, text]) => {
  const data = new DataTransfer(); data.setData('text/plain', text)
  document.querySelector(selector).dispatchEvent(new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true }))
}, [selector, text])

if (only.includes('blocks')) {
  // A screenshot to add: the stress cases table of section 10, as an analyst would capture it from another tool.
  await open('#/workbench/10')
  const picture = path.join(work, 'pasted_screenshot.png')
  await page.locator('.paper .part:has(table)', { hasText: 'Stress cases' }).first().screenshot({ path: picture })

  await open('#/workbench/5')
  // 1. Paste a table copied from Excel after the first part.
  await page.locator('.paper .part .add-block').first().click()
  await paste('.composer-block textarea', ['Peer (SGX listed office REIT)', 'Aggregate leverage (%)', 'Occupancy (%)', 'Source'].join('\t') + '\n'
    + ['Demo Peer A', '38.5', '96.2', 'Analyst worksheet'].join('\t') + '\n' + ['Demo Peer B', '41.0', '94.8', 'Analyst worksheet'].join('\t') + '\n' + ['Demo Peer C', '36.9', '97.5', 'Analyst worksheet'].join('\t') + '\n'
    + ['Average', '48.8', '96.2', 'Typed by the analyst'].join('\t'))  // 48.8 is a deliberate typing slip (the average is 38.8), for the sense check to find
  await page.waitForSelector('.composer-block table')
  await page.fill('.composer-block .title', 'Peer comparison (illustrative, SYNTHETIC DEMO DATA)')
  await page.waitForTimeout(300)
  await shot('01_paste_table')
  await page.click('.composer-block .btn.primary'); await settle()
  // 2. Add a screenshot under it.
  await page.locator('.paper .part .add-block').first().click()
  await page.setInputFiles('.composer-block input[type=file]', picture)
  await page.fill('.composer-block .title', 'Stress cases, as captured from the analyst model')
  await page.waitForTimeout(300)
  await page.click('.composer-block .btn.primary'); await settle()
  // 3. Add a paragraph at the top of the section.
  await page.locator('.paper .box > .add-block').first().click()
  await page.fill('.composer-block textarea', 'Site visit on 5 November with the relationship manager. The manager walked through the leasing pipeline for the floors falling vacant next year. No adverse observations.')
  await page.click('.composer-block .btn.primary'); await settle()
  await unroll()
  await shot('02_section_with_added_content', { fullPage: true })
  // The Word ES with the added content in place, saved for a rendered check.
  const api = base.replace(':15300', ':18200')
  const caseId = (await (await fetch(`${api}/cases`)).json())[0].id
  const preview = await (await fetch(`${api}/cases/${caseId}/exports/preview`)).json()
  const artifact = await (await fetch(`${api}/cases/${caseId}/exports`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor: 'demo-ca', role: 'CA', expected_preview_token: preview.preview_token }) })).json()
  const docx = Buffer.from(await (await fetch(`${api}/cases/${caseId}/exports/${artifact.id}/document.docx`)).arrayBuffer())
  await (await import('node:fs/promises')).writeFile(path.join(work, 'es_with_added_content.docx'), docx)
}
if (only.includes('sense')) {
  // Section 4 of the saved case carries a suggestion from the live run (scripts/demo/live_run.py --sense).
  await open('#/workbench/4'); await unroll()
  await shot('05_sense_check_section_4', { fullPage: true })
  // The model reads the tables that code does not check. Needs the live flag (scripts/screens/enhancements.sh ... --live); costs a few cents.
  await open('#/workbench/5')
  await page.click('.secbar .btn:has-text("Sense check")'); await settle()
  await page.waitForSelector('.banner:has-text("Sense check by the model")', { timeout: 180000 })
  await unroll()
  await shot('03_sense_check', { fullPage: true })
  const mark = page.locator('.suggested button.link').first()
  if (await mark.count()) { await mark.click(); await settle(); await shot('04_sense_check_looked_at', { fullPage: true }) }
}
if (only.includes('papers')) {
  // Read-only: the papers list, then switching to the second paper and back.
  await open('#/papers')
  await shot('06_papers_list')
  await page.locator('.papers .row:has-text("ESR-REIT") .btn').click()
  await page.waitForSelector('.paper'); await page.waitForTimeout(900)
  await shot('07_second_paper_open')
  await page.selectOption('.topbar select[aria-label="Switch paper"]', { label: 'Keppel REIT · New to bank' })
  await page.waitForSelector('.paper'); await page.waitForTimeout(900)
  await shot('08_switched_back')
}
if (only.includes('review')) {
  // Maker and checker on the live paper. The maker confirms every section, submits; the checker reviews, queries one section and
  // returns it; the maker sees the query, reconfirms and resubmits; the checker completes the review and supports.
  const api = base.replace(':15300', ':18200')
  const call = async (path, body) => { const r = await fetch(api + path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}); if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`); return r.json() }
  const caseId = (await call('/cases'))[0].id
  const confirmAll = async () => {
    for (const section of (await call(`/cases/${caseId}/dashboard`)).sections) {
      if (!section.current_draft_id || section.readiness === 'CA confirmed') continue
      await call(`/cases/${caseId}/sections/${section.section_id}/confirm`, { actor: 'demo-ca', role: 'CA', expected_draft_id: section.current_draft_id, expected_revision: section.editor_revision, expected_input_fingerprint: section.input_fingerprint })
    }
  }
  const asRole = async role => { await page.evaluate(([role, id]) => { localStorage.setItem('wb.role', role); localStorage.setItem('wb.paper', id) }, [role, caseId]) }
  await open('#/workbench/review'); await asRole('CA')
  await confirmAll()
  await open('#/workbench/review')
  await page.fill('.centre.review .check input', 'The spread figures are copied from the financial statements and checked in section 10.')
  await page.fill('.centre.review .reply textarea', 'First submission. One model suggestion in section 4 is still open.')
  await shot('09_maker_submit')
  await page.click('.centre.review .btn.primary'); await settle()
  await shot('10_maker_submitted')
  // Checker
  await asRole('Credit Head'); await open('#/workbench/8')
  await shot('11_checker_section')
  await page.click('.review-bar .btn:has-text("Query this section")')
  await page.fill('.review-bar textarea', 'State who the valuer is instructed by, and whether the valuation is addressed to the Bank.')
  await page.click('.review-bar .btn:has-text("Save query")'); await settle()
  for (const section of (await call(`/cases/${caseId}/review`)).sections.filter(s => s.submitted_draft_id && s.section_id !== 8)) {
    await call(`/cases/${caseId}/review/marks`, { actor: 'demo-credit-head', role: 'Credit Head', section_id: section.section_id, status: 'reviewed', expected_es_version_id: (await call(`/cases/${caseId}/review`)).active_es_version_id })
  }
  await open('#/workbench/review')
  await page.fill('.centre.review .reply textarea', 'One query on section 8. The rest reads well.')
  await shot('12_checker_review_with_query')
  await page.click('.centre.review .buttons .btn:not(.primary)'); await settle()
  await open('#/papers'); await shot('13_papers_returned_checker_view')
  // Maker sees the return
  await asRole('CA'); await open('#/workbench/8')
  await shot('14_maker_returned_section')
  await confirmAll()
  await open('#/workbench/review')
  await page.fill('.centre.review .reply textarea', 'Noted. The valuer and addressee are stated in the valuation report cited in section 8.')
  await shot('15_maker_resubmit')
  await page.click('.centre.review .btn.primary'); await settle()
  // Checker completes the review
  await asRole('Credit Head'); await open('#/workbench/8')
  await shot('16_checker_second_look')
  await page.click('.review-bar .btn.primary'); await settle()
  await open('#/workbench/review')
  await shot('17_checker_ready_to_support')
  await page.click('.centre.review .buttons .btn.primary'); await settle()
  await shot('18_supported_with_trail')
  await asRole('CA')
}
const short = only.includes('update_short')  // only sections 8, 1 and 10: refreshes the three proposal pictures at about a third of the cost
if (only.includes('update') || only.includes('update_look') || short) {
  // update_look stops after the What changed page: no model call, no cost.
  // New information: revised papers arrive after the ES is drafted. Each proposal is a drafting call, so this needs
  // the live flag (scripts/screens/enhancements.sh update --live) and costs about as much as redrafting the affected sections.
  const api = base.replace(':15300', ':18200')
  const caseId = (await (await fetch(`${api}/cases`)).json()).find(c => c.borrower_name === 'Keppel REIT').id
  await open('#/inputs')
  await page.evaluate(id => { localStorage.setItem('wb.role', 'CA'); localStorage.setItem('wb.paper', id) }, caseId)
  await open('#/inputs')
  await page.selectOption('select[aria-label="Folder to scan"]', 'late_update')
  await page.click('.scan .btn'); await settle()
  await shot('19_revised_papers_received')
  await open('#/workbench/updates'); await unroll()
  await shot('20_what_changed', { fullPage: true })
  if (only.includes('update') || short) {
  const card = n => page.locator(`.card.upd:has(h3 a[href="#/workbench/${n}"])`)
  const done = async () => { await page.waitForTimeout(400); await page.waitForSelector('.wb-busy', { state: 'detached', timeout: 900000 }); await page.waitForTimeout(700) }
  const propose = async n => {
    for (let attempt = 1; ; attempt++) {
      await card(n).locator('.buttons .btn.primary').click(); await done()
      if (await card(n).locator('.proposal').count()) return
      const problem = await page.locator('.wb-error').innerText().catch(() => 'no proposal shown')
      if (attempt === 2) throw new Error(`Section ${n}: ${problem}`)
      console.log(`section ${n}: retrying after: ${problem}`)
      await page.locator('.wb-error .btn').click().catch(() => {})
    }
  }
  const apply = async n => { await card(n).locator('.buttons .btn.primary').click(); await done() }
  const picture = async (n, name) => { await card(n).scrollIntoViewIfNeeded(); await card(n).screenshot({ path: `${out}enh_${name}.png` }) }
  // Section 8 first: the loan to value line, with the calculated cells marked.
  await propose(8); await picture(8, '21_proposal_figures'); await apply(8)
  // Section 1: wording as tracked changes. One part is set to "keep" for the picture, then set back so the applied ES is consistent.
  await propose(1)
  const keep = card(1).locator('.part-change .choice label:has-text("Keep the current wording") input').first()
  if (await keep.count()) { await keep.check(); await picture(1, '22_proposal_wording_one_part_kept'); await card(1).locator('.part-change .choice label:has-text("Accept") input').first().check() }
  else await picture(1, '22_proposal_wording_one_part_kept')
  await apply(1)
  if (!short) { for (const n of [2, 3, 4, 5, 6, 7]) { await propose(n); if (n === 7) await picture(7, '23_proposal_facility_terms'); await apply(n) }
  await shot('24_part_way_waiting_sections', { fullPage: true }) }
  await propose(10); await picture(10, '25_proposal_calculated_tables'); await apply(10)
  if (!short) {
  await propose(9); await apply(9)
  await propose(11); await picture(11, '26_proposal_risks'); await apply(11)
  await propose(14); await picture(14, '27_proposal_recommendation'); await apply(14)
  await open('#/workbench/updates'); await unroll()
  await shot('28_all_sections_updated', { fullPage: true })
  await open('#/workbench/8'); await unroll()
  await shot('29_section_8_after_update', { fullPage: true })
  // The Word ES after the update, saved for a rendered check.
  const preview = await (await fetch(`${api}/cases/${caseId}/exports/preview`)).json()
  if (preview.blockers?.length) console.log('export blocked:', preview.blockers.join(' '))
  else {
    const artifact = await (await fetch(`${api}/cases/${caseId}/exports`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor: 'demo-ca', role: 'CA', expected_preview_token: preview.preview_token }) })).json()
    const docx = Buffer.from(await (await fetch(`${api}/cases/${caseId}/exports/${artifact.id}/document.docx`)).arrayBuffer())
    await (await import('node:fs/promises')).writeFile(path.join(work, 'es_after_update.docx'), docx)
  }
  }
  }
}
await browser.close()
console.log(errors.length ? `Problems:\n${errors.join('\n')}` : 'Captured, no page errors')
if (errors.length) process.exit(1)

// Records the mock demo flow on a fresh case and saves the video and the exported ES.
//   node scripts/demo/record_demo.mjs
// Output: docs/demo/earlier_mock_case/WB_Credit_demo.mp4, WB_Credit_ES_export.docx and .pdf (the first mock demo)
// Mock provider only; servers started here are stopped at the end.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { spawn, execFileSync } from 'node:child_process'
import { mkdir, rm, readdir, writeFile, copyFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../../', import.meta.url))
const out = path.join(root, 'docs/demo/earlier_mock_case')
const work = path.join(root, 'runtime/demo_video')
const app = 'http://127.0.0.1:15224', api = 'http://127.0.0.1:18124'
const env = { ...process.env, LLM_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1', DEMO_PORT: '15224', DEMO_API_PORT: '18124' }
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
const children = []
function start(command, args, cwd) {
  const child = spawn(command, args, { cwd, env, stdio: 'ignore' })
  children.push(child)
  return child
}
async function up(url) {
  for (let i = 0; i < 80; i++) { try { if ((await fetch(url)).ok) return } catch { /* not ready */ } await delay(250) }
  throw new Error(`Server did not start: ${url}`)
}
await rm(work, { recursive: true, force: true })
await mkdir(path.join(work, 'video'), { recursive: true }); await mkdir(out, { recursive: true })
let browser
try {
  execFileSync('npm', ['run', 'build'], { cwd: path.join(root, 'frontend'), stdio: 'ignore' })
  start(path.join(root, '.venv/bin/python'), ['-c', 'import sys, uvicorn; from backend.app.local import create_demo_app; uvicorn.run(create_demo_app(sys.argv[1]), host="127.0.0.1", port=18124, log_level="warning")', path.join(work, 'case')], root)
  await up(`${api}/health`)
  start(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--config', '../scripts/demo/vite.demo.config.mjs'], path.join(root, 'frontend'))
  await up(app)

  browser = await chromium.launch({ channel: 'chrome', headless: true })
  const size = { width: 1280, height: 720 }
  const context = await browser.newContext({ viewport: size, recordVideo: { dir: path.join(work, 'video'), size } })
  const page = await context.newPage()
  const idle = () => page.locator('.wb-busy').waitFor({ state: 'hidden', timeout: 180000 })
  const caption = text => page.evaluate(t => {
    let bar = document.getElementById('demo-caption')
    if (!bar) {
      bar = document.body.appendChild(Object.assign(document.createElement('div'), { id: 'demo-caption' }))
      bar.style.cssText = 'pointer-events:none;position:fixed;left:50%;bottom:44px;transform:translateX(-50%);z-index:99;background:#0B2A6B;color:#fff;font:600 17px -apple-system,sans-serif;padding:9px 20px;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.3)'
    }
    bar.textContent = t
  }, text)
  const step = async (text, ms = 1500) => { await caption(text); await delay(ms) }

  await page.goto(`${app}/#/inputs`); await page.waitForLoadState('networkidle')
  await step('Inputs screen: the analyst adds files as they arrive', 2500)
  const tranche = n => path.join(root, 'demo/synthetic', `tranche_${n}`)
  const first = (await readdir(tranche(1))).map(name => path.join(tranche(1), name))
  await caption('Upload the first files')
  await page.locator('.dropzone input[type=file]').setInputFiles(first); await delay(400); await idle(); await delay(1800)
  await caption('Scan the deal folder for the rest')
  await page.getByLabel('Folder to scan').selectOption('tranche_2'); await delay(700)
  await page.getByRole('button', { name: 'Scan folder' }).click(); await delay(400); await idle(); await delay(2000)
  await caption('Search saved public sources for what is missing')
  await page.getByRole('button', { name: 'Search public sources' }).click(); await delay(400); await idle(); await delay(1500)
  await page.getByRole('button', { name: /public files? as reviewed/ }).click(); await delay(400); await idle()
  await page.getByRole('button', { name: 'Generate now' }).click(); await delay(400); await idle()
  await step('Checklist: uploaded, still missing, and sections that can start', 1200)
  await page.mouse.move(640, 400); await page.mouse.wheel(0, 420); await delay(2600)
  await page.locator('.go').scrollIntoViewIfNeeded()
  await caption('Start drafting the sections that are ready')
  await page.getByLabel(/description of the RCF as unsecured/).check(); await delay(900)
  await page.getByRole('button', { name: /Start drafting/ }).click()
  await page.waitForURL(/#\/workbench/, { timeout: 240000 }); await idle()
  await step('ES workbench: the whole ES in the template layout', 2200)
  await page.mouse.move(700, 400); await page.mouse.wheel(0, 500); await delay(1800)
  await caption('Open a section')
  await page.locator('.rail a', { hasText: 'Security support' }).click()
  await page.locator('.paper .box p').first().waitFor(); await delay(2500)
  await caption('Ask the Credit Assistant for a change')
  const box = page.getByLabel('Message to the Credit Assistant')
  await box.click(); await box.pressSequentially('The client is arranging the insurance renewal. The certificate is expected before drawdown.', { delay: 18 })
  await delay(600); await page.getByRole('button', { name: 'Send' }).click()
  await page.locator('.change').waitFor(); await idle()
  await step('The change is shown as a tracked change. Nothing is saved yet.', 3200)
  await caption('Accept the change')
  await page.getByRole('button', { name: 'Accept change' }).click(); await delay(400); await idle()
  await page.locator('.change').waitFor({ state: 'hidden' }); await delay(1800)
  await caption('Confirm the section')
  await page.getByRole('button', { name: 'Confirm section' }).click(); await delay(400); await idle()
  await page.locator('.rail a.on .dot.ok').waitFor(); await delay(2200)
  await caption('Export the ES into the Word template')
  await page.locator('.rail a', { hasText: 'Full ES' }).click(); await delay(1500)
  await page.getByRole('button', { name: 'Export ES to Word' }).click(); await delay(400); await idle()
  const link = page.getByRole('link', { name: 'Download Word ES' })
  await link.waitFor(); await delay(2500)
  const docx = await (await page.request.get(new URL(await link.getAttribute('href'), app).href)).body()
  await writeFile(path.join(out, 'WB_Credit_ES_export.docx'), docx)
  await step('Mock mode with synthetic demo data. Drafts are for analyst review.', 2500)
  const video = page.video()
  await context.close()
  const webm = await video.path()
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', webm, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '24', '-movflags', '+faststart', path.join(out, 'WB_Credit_demo.mp4')])
  execFileSync(path.join(root, 'scripts/render_docx.sh'), [path.join(out, 'WB_Credit_ES_export.docx'), path.join(work, 'pdf')], { stdio: 'ignore' })
  await copyFile(path.join(work, 'pdf', 'WB_Credit_ES_export.pdf'), path.join(out, 'WB_Credit_ES_export.pdf'))
  console.log('Saved docs/demo/earlier_mock_case/WB_Credit_demo.mp4 and WB_Credit_ES_export.docx/.pdf')
} finally {
  await browser?.close().catch(() => {})
  for (const child of children) child.kill('SIGTERM')
}

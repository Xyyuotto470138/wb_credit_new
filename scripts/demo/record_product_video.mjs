// Records the product video of the new-to-bank Keppel REIT case: title cards, divider screens and
// large call-outs over the real screens. No narration captions. The product is shown as "GWB Credit":
// the cards say so and the top bar label is restyled for the recording only (the app itself is unchanged).
//   node scripts/demo/record_product_video.mjs            all scenes; one section is drafted with the live model (paid, under USD 1)
//   node scripts/demo/record_product_video.mjs --dry      no live call: the live drafting scene stops before the click
//   add --only inputs,tour                                re-record only these scenes and reuse the other saved clips
// Needs the saved live case from scripts/demo/live_run.py (runtime/demo_live/case). It is backed up first and restored at the end.
// Output: docs/demo/WB_Credit_product_video.mp4. Servers started here are stopped at the end.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { spawn, execFileSync } from 'node:child_process'
import { mkdir, rm, readdir, writeFile, cp, access, rename } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../../', import.meta.url))
const work = path.join(root, 'runtime/demo_video')
const clips = path.join(work, 'clips'), cards = path.join(work, 'cards')
const target = path.join(root, 'docs/demo/WB_Credit_product_video.mp4')
const dry = process.argv.includes('--dry')
const only = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1].split(',') : null
const W = 1920, H = 1080, LW = 1536, LH = 864, BASE = W / LW   // the app is laid out at 1536 x 864 and shown at 1.25x
const FRESH = { app: 'http://127.0.0.1:15224', api: 'http://127.0.0.1:18124' }   // empty case: Documents Input and the live draft
const SAVED = { app: 'http://127.0.0.1:15225', api: 'http://127.0.0.1:18125' }   // copy of the saved live case: everything else
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
const children = []
function start(command, args, cwd, extra = {}) {
  children.push(spawn(command, args, { cwd, env: { ...process.env, LLM_PROVIDER: 'mock', PYTHONDONTWRITEBYTECODE: '1', ...extra }, stdio: 'ignore' }))
}
async function up(url) {
  for (let i = 0; i < 120; i++) { try { if ((await fetch(url)).ok) return } catch { /* not ready */ } await delay(250) }
  throw new Error(`Server did not start: ${url}`)
}
const serve = (dir, pack, apiPort, webPort, extra) => {
  start(path.join(root, '.venv/bin/python'), ['-c', `import sys, uvicorn; from backend.app.local import create_demo_app; uvicorn.run(create_demo_app(sys.argv[1], sys.argv[2]), host="127.0.0.1", port=${apiPort}, log_level="warning")`, dir, pack], root, extra)
  start(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--config', '../scripts/demo/vite.demo.config.mjs'], path.join(root, 'frontend'), { DEMO_PORT: String(webPort), DEMO_API_PORT: String(apiPort) })
}

// ---------- look: light background, dark type, one blue accent
const FONT = '"Avenir Next","SF Pro Display",-apple-system,"Helvetica Neue",Arial,sans-serif'
const INK = '#0B0C10', BLUE = '#1273EA', PAPER = '#F7F8FA', PRODUCT = 'GWB Credit'
const K = 0.72   // pace: every hold in the app scenes is multiplied by this
const cardCss = `*{margin:0;box-sizing:border-box}html,body{width:${W}px;height:${H}px;overflow:hidden;color:${INK};font-family:${FONT};-webkit-font-smoothing:antialiased;
background:linear-gradient(180deg,#FCFCFD 0%,${PAPER} 52%,#E3EEFC 86%,#CFE3FB 100%)}
.glow{position:absolute;inset:-20%;background:radial-gradient(1100px 620px at 82% 104%,rgba(18,115,234,.20),transparent 62%),radial-gradient(900px 520px at 10% 108%,rgba(120,180,255,.20),transparent 60%);animation:drift 7s ease-in-out infinite alternate}
@keyframes drift{to{transform:translate(-3%,-2%) scale(1.06)}}
.w{display:inline-block;opacity:0;transform:translateY(46px);filter:blur(12px);animation:rise .6s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes rise{to{opacity:1;transform:none;filter:none}}
@keyframes out{to{opacity:0;transform:translateY(-36px);filter:blur(10px)}}
@keyframes pop{0%{opacity:0;transform:scale(.6)}70%{transform:scale(1.05)}100%{opacity:1;transform:scale(1)}}
b{font-weight:inherit;color:${BLUE}}
.mid{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.foot{position:absolute;left:0;right:0;bottom:62px;text-align:center;font-size:28px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:rgba(11,12,16,.5)}`
// Words rise in one after another; a word wrapped in *stars* is shown in the accent blue.
const words = (text, from = 0, step = 0.09) => text.split(' ').map((w, i) => {
  const accent = /^\*.*\*$/.test(w)
  return `<span class="w" style="animation-delay:${(from + i * step).toFixed(2)}s${accent ? `;color:${BLUE}` : ''}">${accent ? w.slice(1, -1) : w}</span>`
}).join(' ')
const page = body => `<!doctype html><meta charset="utf-8"><style>${cardCss}</style><div class="glow"></div>${body}`
const tile = `<div style="width:270px;height:270px;border-radius:62px;background:linear-gradient(180deg,#fff,#F1F3F6);box-shadow:0 30px 60px rgba(20,40,80,.18),0 2px 0 rgba(255,255,255,.9) inset,0 0 0 1px rgba(10,20,40,.05);display:flex;align-items:center;justify-content:center;font-size:92px;font-weight:700;letter-spacing:-.04em;background-clip:padding-box">
  <span style="background:linear-gradient(135deg,#0A55D6,#2E9BFF);-webkit-background-clip:text;color:transparent">GWB</span></div>`

function divider(number, title, sub) {
  return page(`<div class="mid">
    <div class="w" style="font-size:40px;font-weight:600;letter-spacing:.16em;color:${BLUE};background:rgba(18,115,234,.10);padding:12px 34px 10px;border-radius:999px">${number}</div>
    <div style="font-size:190px;font-weight:500;letter-spacing:-.035em;line-height:1.05;margin-top:38px">${words(title, 0.12, 0.1)}</div>
    <div style="font-size:54px;font-weight:400;margin-top:36px;color:rgba(11,12,16,.62)">${words(sub, 0.5, 0.04)}</div></div>`)
}
function intro() {
  const lines = ['Deal papers *in.*', 'Draft ES *out.*', 'Every figure *checked.*']
  const start = 3.3, each = 1.05
  const phrase = (text, i) => `<div class="mid" style="font-size:176px;font-weight:500;letter-spacing:-.035em;${i < lines.length - 1 ? `animation:out .3s ${(start + (i + 1) * each - 0.3).toFixed(2)}s ease-in forwards` : ''}">
    <span>${words(text, start + i * each, 0.08)}</span></div>`
  return page(`<div class="mid" style="animation:out .35s 1.15s ease-in forwards"><div style="opacity:0;animation:pop .6s .1s cubic-bezier(.2,.9,.3,1.2) forwards">${tile}</div></div>
    <div class="mid" style="font-size:200px;font-weight:500;letter-spacing:-.035em;line-height:1.1;animation:out .35s ${start - 0.4}s ease-in forwards">
      <div>${words('Introducing', 1.5, 0.1)}</div><div>${words(`*${PRODUCT.split(' ')[0]}* *${PRODUCT.split(' ')[1]}*`, 1.75, 0.12)}</div></div>
    ${lines.map(phrase).join('')}
    <div class="foot"><span class="w" style="animation-delay:1.9s">Prototype · Synthetic demo data</span></div>`)
}
function outro() {
  const lines = ['AI drafts.', 'Python checks.', '*Analysts* *decide.*']
  return page(`<div class="mid" style="font-size:186px;font-weight:500;letter-spacing:-.035em;line-height:1.1;padding-bottom:60px">
    ${lines.map((text, i) => `<div>${words(text, 0.15 + i * 0.6, 0.1)}</div>`).join('')}</div>
    <div class="foot"><span class="w" style="animation-delay:2.2s">${PRODUCT} · Prototype · Synthetic demo data · Drafts are for credit analyst review</span></div>`)
}

// Runs inside the app page: the 1.25x stage, zoom, spotlight, large call-outs and a visible pointer.
function stage({ W, H, LW, LH, BASE, FONT, BLUE, INK, PAPER, PRODUCT }) {
  const css = document.createElement('style')
  css.textContent = `html,body{overflow:hidden!important;background:${PAPER}!important;width:${W}px;height:${H}px}
#root{width:${LW}px;height:${LH}px;transform-origin:0 0;transform:translate(0px,0px) scale(${BASE});transition:transform .75s cubic-bezier(.3,.7,.1,1);background:#fff}
.wb{height:${LH}px!important}
.topbar .product{font-size:0!important}.topbar .product::after{content:'${PRODUCT}';font-size:15px}
#pv{position:fixed;inset:0;z-index:9999;pointer-events:none;font-family:${FONT};-webkit-font-smoothing:antialiased}
#pv .spot{position:absolute;border:4px solid ${BLUE};border-radius:18px;box-shadow:0 0 0 4000px rgba(245,247,251,.74),0 0 0 10px rgba(18,115,234,.14),0 18px 60px rgba(18,115,234,.30);opacity:0;transition:opacity .3s,left .45s,top .45s,width .45s,height .45s}
#pv .say{position:absolute;max-width:1740px;background:rgba(255,255,255,.86);-webkit-backdrop-filter:blur(26px) saturate(1.4);backdrop-filter:blur(26px) saturate(1.4);color:${INK};font-size:80px;font-weight:600;letter-spacing:-.03em;line-height:1.1;padding:30px 58px 32px;border-radius:40px;border:1px solid rgba(255,255,255,.9);box-shadow:0 0 0 1px rgba(10,20,40,.06),0 34px 90px rgba(20,70,160,.26),0 6px 18px rgba(20,40,80,.10);opacity:0;transform:translateY(30px) scale(.92);transition:opacity .25s,transform .4s cubic-bezier(.2,1.4,.4,1)}
#pv .say.on{opacity:1;transform:none}
#pv .say em{font-style:normal;background:linear-gradient(120deg,#0A55D6,#2E9BFF);-webkit-background-clip:text;color:transparent}
#pv .say small{display:block;font-size:36px;font-weight:500;letter-spacing:0;color:rgba(11,12,16,.55);margin-top:8px}
#pv .ptr{position:absolute;left:-60px;top:-60px;width:34px;height:34px}
#pv .ring{position:absolute;width:20px;height:20px;margin:-10px;border-radius:50%;border:4px solid ${BLUE};animation:ring .5s ease-out forwards}
@keyframes ring{to{transform:scale(5.5);opacity:0}}`
  document.head.appendChild(css)
  const layer = document.body.appendChild(Object.assign(document.createElement('div'), { id: 'pv' }))
  layer.innerHTML = `<div class="spot"></div><div class="say"></div><svg class="ptr" viewBox="0 0 24 24"><path d="M4 2l15 11h-8.2l-3.3 8.4z" fill="#0B0C10" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`
  const spot = layer.querySelector('.spot'), say = layer.querySelector('.say'), ptr = layer.querySelector('.ptr'), app = document.getElementById('root')
  let cur = { s: BASE, tx: 0, ty: 0 }
  addEventListener('mousemove', e => { ptr.style.left = `${e.clientX - 5}px`; ptr.style.top = `${e.clientY - 3}px` }, true)
  addEventListener('mousedown', e => {
    const ring = layer.appendChild(Object.assign(document.createElement('div'), { className: 'ring' }))
    ring.style.left = `${e.clientX}px`; ring.style.top = `${e.clientY}px`; setTimeout(() => ring.remove(), 600)
  }, true)
  window.__pv = {
    zoom(el, scale = 1.5, biasY = 0) {
      if (!el) { cur = { s: BASE, tx: 0, ty: 0 } } else {
        const r = el.getBoundingClientRect(), s = BASE * scale
        const cx = (r.left + r.width / 2 - cur.tx) / cur.s, cy = (r.top + Math.min(r.height, H / scale) / 2 - cur.ty) / cur.s
        cur = { s, tx: Math.min(0, Math.max(W - s * LW, W / 2 - s * cx)), ty: Math.min(0, Math.max(H - s * LH, H / 2 - s * cy + biasY)) }
      }
      app.style.transform = `translate(${cur.tx}px,${cur.ty}px) scale(${cur.s})`
    },
    spot(el, pad = 12) {
      if (!el) { spot.style.opacity = 0; return }
      const r = el.getBoundingClientRect()
      const top = Math.max(8, r.top - pad), left = Math.max(8, r.left - pad)
      Object.assign(spot.style, { left: `${left}px`, top: `${top}px`, width: `${Math.min(W - 8, r.right + pad) - left}px`, height: `${Math.min(H - 8, r.bottom + pad) - top}px`, opacity: 1 })
    },
    say(html, where = 'bottom') {
      if (!html) { say.classList.remove('on'); return }
      say.classList.remove('on'); say.innerHTML = html
      say.style.cssText = { bottom: 'left:50%;bottom:80px;width:max-content;', top: 'left:50%;top:120px;width:max-content;', left: 'left:90px;bottom:90px;', right: 'right:90px;bottom:90px;', 'top-right': 'right:90px;top:130px;', 'top-left': 'left:90px;top:130px;' }[where]
      if (where === 'bottom' || where === 'top') { say.style.marginLeft = `${-say.offsetWidth / 2}px` }
      requestAnimationFrame(() => requestAnimationFrame(() => say.classList.add('on')))
    },
  }
}

// ---------- recording
async function exists(file) { try { await access(file); return true } catch { return false } }
async function record(browser, name, run) {
  const out = path.join(clips, `${name}.mp4`)
  if (only && !only.includes(name) && await exists(out)) return out
  const dir = path.join(work, 'raw', name)
  await rm(dir, { recursive: true, force: true })
  const context = await browser.newContext({ viewport: { width: W, height: H }, recordVideo: { dir, size: { width: W, height: H } } })
  const t0 = Date.now(), page = await context.newPage()
  const now = () => (Date.now() - t0) / 1000
  const segments = []
  let open = null
  const cut = {
    begin(speed = 1) { open = { a: now(), speed } },
    end() { if (open) { segments.push({ ...open, b: now() }); open = null } },
    async fast(speed, action) { cut.end(); cut.begin(speed); await action(); cut.end(); cut.begin() },
  }
  await run(page, cut)
  cut.end()
  const video = page.video()
  await context.close()
  const filter = segments.map((s, i) => `[0:v]trim=start=${s.a.toFixed(3)}:end=${s.b.toFixed(3)},setpts=(PTS-STARTPTS)/${s.speed}[v${i}]`).join(';')
    + `;${segments.map((_, i) => `[v${i}]`).join('')}concat=n=${segments.length}:v=1:a=0,fps=30,format=yuv420p[out]`
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', await video.path(), '-filter_complex', filter, '-map', '[out]', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', out])
  console.log(`recorded ${name}: ${segments.reduce((sum, s) => sum + (s.b - s.a) / s.speed, 0).toFixed(1)}s`)
  return out
}
const card = (browser, name, html, seconds) => record(browser, name, async (page, cut) => {
  const file = path.join(cards, `${name}.html`)
  await writeFile(file, html)
  await page.goto(pathToFileURL(file).href); await delay(120)
  cut.begin(); await delay(seconds * 1000)
})

function tools(page) {
  const pv = (method, locator, ...args) => locator ? locator.first().evaluate((el, [m, a]) => window.__pv[m](el, ...a), [method, args]) : page.evaluate(([m, a]) => window.__pv[m](null, ...a), [method, args])
  const t = {
    idle: () => page.locator('.wb-busy').waitFor({ state: 'hidden', timeout: 300000 }),
    async open(base, hash) {
      await page.goto(`${base}/${hash}`); await page.waitForLoadState('networkidle')
      await page.evaluate(stage, { W, H, LW, LH, BASE, FONT, BLUE, INK, PAPER, PRODUCT }); await page.mouse.move(W * 0.55, H * 0.6); await delay(400)
    },
    async go(hash, wait) { await page.evaluate(h => { location.hash = h }, hash); if (wait) await page.locator(wait).first().waitFor(); await delay(700) },
    say: (html, where) => page.evaluate(([h, w]) => window.__pv.say(h, w), [html, where]),
    async hush() { await page.evaluate(() => { window.__pv.say(''); window.__pv.spot(null) }); await delay(260) },
    zoom: async (locator, scale, biasY) => { await pv('zoom', locator, scale, biasY); await delay(800) },
    spot: (locator, pad) => pv('spot', locator, pad),
    async show(locator) { await locator.first().evaluate(el => el.scrollIntoView({ behavior: 'smooth', block: 'center' })); await delay(750) },
    async point(locator) {
      const box = await locator.first().boundingBox()
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 18 }); await delay(180)
    },
    async click(locator) { await t.point(locator); await locator.first().click(); await delay(280) },
    // One beat: optional spotlight, a large call-out, hold, then clear.
    async beat(html, { on, where = 'bottom', hold = 2600, pad } = {}) {
      if (on) await t.spot(on, pad)
      await t.say(html, where); await delay(hold * K); await t.hush()
    },
  }
  return t
}

async function intake(api) {
  const post = (url, body) => fetch(`${api}${url}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
  const id = (await (await fetch(`${api}/cases`)).json())[0].id, base = `/cases/${id}`, ca = { actor: 'Demo Credit Analyst', role: 'CA' }
  const state = await (await fetch(`${api}${base}/dashboard`)).json()
  if (state.documents.length) return
  for (const folder of state.intake.folders) await post(`${base}/documents/scan`, { folder_id: folder.id, metadata_by_path: folder.metadata_by_path || {} })
  await post(`${base}/public-search`, ca)
  for (const doc of (await (await fetch(`${api}${base}/dashboard`)).json()).documents) if (doc.origin === 'public' && !doc.confirmed_by) await post(`${base}/documents/${doc.id}/confirm`, ca)
}

const scenes = {
  async inputs(page, cut) {
    const t = tools(page)
    await t.open(FRESH.app, '#/inputs'); cut.begin()
    const drop = page.locator('.dropzone')
    await t.zoom(drop, 1.25); await t.point(drop)
    await t.beat('Drop in the <em>deal papers</em>', { on: drop, hold: 2000 })
    const folder = path.join(root, 'demo/synthetic_keppel/deal_folder')
    const files = (await readdir(folder)).map(name => path.join(folder, name))
    await cut.fast(4, async () => { await page.locator('.dropzone input[type=file]').setInputFiles(files); await delay(400); await t.idle() })
    await t.zoom(null); await delay(300)
    const uploaded = page.getByLabel('Uploaded', { exact: true })
    await t.zoom(uploaded, 1.3)
    await t.beat(`<em>${files.length} files.</em> Sorted on arrival.`, { on: uploaded, where: 'right', hold: 2600 })
    await t.zoom(null)
    const search = page.getByRole('button', { name: 'Search public sources' })
    await t.show(search); await t.click(search)
    await cut.fast(4, async () => { await delay(300); await t.idle() })
    const mark = page.getByRole('button', { name: /public files? as reviewed/ })
    await t.show(mark); await t.zoom(mark, 1.3)
    await t.beat('Public filings <em>found for you</em>', { on: page.locator('.group', { hasText: 'Found for you' }), where: 'right', hold: 2400 })
    await t.click(mark); await cut.fast(4, async () => { await delay(300); await t.idle() })
    await t.zoom(null)
    const go = page.getByRole('button', { name: /Start drafting/ })
    const ready = page.locator('.grid > *').last()
    await ready.evaluate(el => el.scrollIntoView({ behavior: 'smooth', block: 'start' })); await delay(900)
    await t.zoom(ready, 1.3)
    const count = (await go.innerText()).match(/\d+/)[0]
    await t.beat(`<em>${count} sections</em> ready to draft`, { on: ready, where: 'left', hold: 2600 })
    await t.zoom(null); await delay(200)
  },
  async draft(page, cut) {
    const t = tools(page)
    await intake(FRESH.api)
    await t.open(FRESH.app, '#/workbench/12'); cut.begin()
    const button = page.getByRole('button', { name: 'Draft this section' })
    await t.zoom(button, 1.5); await t.point(button)
    await t.beat('One click to <em>draft</em>', { on: button, hold: 1900 })
    if (dry) return
    await button.click(); await delay(500)
    await t.say('Drafting with the <em>live model</em><small>Shown at 8x speed</small>', 'bottom'); await delay(900)
    await cut.fast(8, async () => { await page.locator('.paper table').first().waitFor({ timeout: 300000 }); await t.idle() })
    await t.hush(); await t.zoom(null)
    const tables = page.locator('.paper table')
    await t.zoom(tables.first(), 1.45)
    await t.beat('Internal rating, read from the <em>rating worksheet</em>', { on: tables.first(), hold: 2800 })
    await t.show(tables.nth(1)); await t.zoom(tables.nth(1), 1.45)
    await t.beat('Every claim <em>checked</em> against its cited page', { on: tables.nth(1), hold: 2800 })
    await t.zoom(null); await delay(200)
  },
  async tour(page, cut) {
    const t = tools(page)
    await t.open(SAVED.app, '#/workbench/full'); await page.locator('.full-section').first().waitFor(); await delay(600); cut.begin()
    await t.say('<em>14 sections.</em> One template.', 'bottom')
    await page.locator('.centre').evaluate(el => el.scrollTo({ top: 2600, behavior: 'smooth' })); await delay(1100)
    await page.locator('.centre').evaluate(el => el.scrollTo({ top: 6200, behavior: 'smooth' })); await delay(1100); await t.hush()
    await t.go('#/workbench/2', '.paper table')
    const exposure = page.locator('.paper .part', { hasText: 'Existing and proposed limits' })
    await t.show(exposure); await t.zoom(exposure.locator('table'), 1.45)
    await t.beat('Figures copied from source. <em>Totals computed in code.</em>', { on: exposure.locator('table'), hold: 3000 })
    const cite = exposure.locator('sup.cite').first()
    await t.click(cite); await t.zoom(null); await delay(400)
    await t.beat('Every claim carries its <em>source</em>', { on: page.locator('.panel'), where: 'left', hold: 2800 })
    await t.go('#/workbench/4', '.paper .images img')
    const images = page.locator('.paper .images').first()
    await t.show(images); await t.zoom(images, 1.3)
    await t.beat('The <em>real building.</em> The real location.', { on: images, hold: 3000 })
    const plan = page.locator('.paper .images').last()
    if (await page.locator('.paper .images').count() > 1) { await t.zoom(null, 1); await t.show(plan); await t.zoom(plan, 1.3); await delay(1000) }
    await t.zoom(null)
    await t.go('#/workbench/10', '.paper table')
    const pl = page.locator('.paper .part table').first()
    await t.show(pl); await t.zoom(pl, 1.4)
    await t.beat('Reported financials, <em>checked line by line</em>', { on: pl, hold: 2800 })
    const stress = page.locator('.paper .part:has(table)', { hasText: 'Stress cases' }).first()
    await t.zoom(null, 1); await t.show(stress); await t.zoom(stress.locator('table').first(), 1.4)
    await t.beat('Ratios and stress cases: <em>computed, never model-written</em>', { on: stress.locator('table').first(), hold: 3000 })
    await t.zoom(null); await delay(200)
  },
  async assistant(page, cut) {
    const t = tools(page)
    await t.open(SAVED.app, '#/workbench/8'); await page.locator('.paper .part').first().waitFor(); await delay(500); cut.begin()
    const box = page.getByLabel('Message to the Credit Assistant')
    await t.zoom(box, 1.35); await t.click(box)
    await t.say('Ask in <em>plain words</em>', 'left')
    await box.pressSequentially('The client is arranging the insurance endorsement. It is expected before first drawdown.', { delay: 13 })
    await delay(500); await t.hush()
    await t.click(page.getByRole('button', { name: 'Send' }))
    await page.locator('.change').waitFor(); await t.idle(); await t.zoom(null)
    const change = page.locator('.change')
    await t.show(change); await t.zoom(change, 1.35)
    await t.beat('A <em>tracked change.</em> Nothing saved yet.', { on: change, where: 'top', hold: 3000 })
    await t.click(page.getByRole('button', { name: 'Accept change' })); await t.idle()
    await change.waitFor({ state: 'hidden' }); await t.zoom(null, 1)
    const note = page.locator('.paper .part', { hasText: "Credit analyst's notes" }).last()
    await t.show(note); await t.zoom(note, 1.35)
    await t.beat('<em>Accepted.</em> Marked as analyst input.', { on: note, where: 'top', hold: 2800 })
    await t.zoom(null); await delay(200)
  },
  async confirm(page, cut) {
    const t = tools(page)
    await t.open(SAVED.app, '#/workbench/8'); await page.locator('.paper .part').first().waitFor(); await delay(500); cut.begin()
    const button = page.getByRole('button', { name: 'Confirm section' })
    await t.zoom(button, 1.4)
    await t.beat('The analyst <em>signs off</em> each section', { on: button, hold: 2200 })
    await t.click(button); await t.idle()
    await page.locator('.rail a.on .dot.ok').waitFor(); await t.zoom(null)
    const row = page.locator('.rail a.on')
    await t.zoom(row, 1.5)
    await t.beat('<em>Confirmed.</em> No AI approval, ever.', { on: row, where: 'right', hold: 2800 })
    await t.zoom(null); await delay(200)
  },
}

await mkdir(clips, { recursive: true }); await mkdir(cards, { recursive: true })
const live = path.join(root, 'runtime/demo_live/case'), backup = path.join(work, 'saved_case_backup')
async function restore() { if (await exists(backup)) { await rm(live, { recursive: true, force: true }); await rename(backup, live) } }
await restore()   // a run that was killed part-way leaves the backup behind
if (!await exists(live)) throw new Error('No saved live case. Run: .venv/bin/python scripts/demo/live_run.py')
const wanted = name => !only || only.includes(name)
let browser
try {
  execFileSync('npm', ['run', 'build'], { cwd: path.join(root, 'frontend'), stdio: 'ignore' })
  if (wanted('inputs') || wanted('draft')) {
    if (wanted('inputs')) await rm(path.join(work, 'fresh'), { recursive: true, force: true })
    serve(path.join(work, 'fresh'), 'demo/synthetic_keppel', 18124, 15224, dry ? {} : { WB_CREDIT_LIVE: '1' })
  }
  // The saved case only runs from its own folder, so it is used in place and put back from this backup at the end.
  await cp(live, backup, { recursive: true })
  serve(live, 'demo/synthetic_keppel', 18125, 15225)
  await up(`${SAVED.api}/health`); await up(SAVED.app)
  if (wanted('inputs') || wanted('draft')) { await up(`${FRESH.api}/health`); await up(FRESH.app) }

  browser = await chromium.launch({ channel: 'chrome', headless: true })
  const order = [
    ['intro', () => card(browser, 'intro', intro(), 7.2)],
    ['d1', () => card(browser, 'd1', divider('01', 'Documents *Input*', 'Drop the deal folder. See what is missing.'), 2.5)],
    ['inputs', () => record(browser, 'inputs', scenes.inputs)],
    ['d2', () => card(browser, 'd2', divider('02', 'ES Drafting *Pilot*', 'Section by section, in the ES template.'), 2.5)],
    ['draft', () => record(browser, 'draft', scenes.draft)],
    ['tour', () => record(browser, 'tour', scenes.tour)],
    ['d3', () => card(browser, 'd3', divider('03', 'Credit Chat *Assistant*', 'Ask for a change. See it tracked.'), 2.5)],
    ['assistant', () => record(browser, 'assistant', scenes.assistant)],
    ['d4', () => card(browser, 'd4', divider('04', 'Analyst *Review*', 'Every section confirmed by the analyst.'), 2.5)],
    ['confirm', () => record(browser, 'confirm', scenes.confirm)],
    ['outro', () => card(browser, 'outro', outro(), 5.2)],
  ]
  const done = []
  for (const [, make] of order) done.push(await make())
  const list = path.join(work, 'concat.txt')
  await writeFile(list, done.map(file => `file '${file}'`).join('\n'))
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c:v', 'libx264', '-crf', '30', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', target])
  console.log(`Saved ${path.relative(root, target)}${dry ? ' (dry run: no live call)' : ''}`)
} finally {
  await browser?.close().catch(() => {})
  for (const child of children) child.kill('SIGTERM')
  await delay(800); await restore()
}

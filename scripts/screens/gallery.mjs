// Print one viewport screenshot and caption per page; never a full-page shrink-to-fit.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../../', import.meta.url))
const output = path.join(root, 'docs/screens')
const manifest = JSON.parse(await readFile(path.join(output, 'capture.json'), 'utf8'))
const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;')
await writeFile(path.join(output, 'gallery.html'), `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>WB Credit screen review</title><style>
@page { size: 15in 10in; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; background: #e7ecef; color: #22343b; font-family: Arial, sans-serif; }
.sheet { width: 15in; height: 10in; padding: .3in .5in; background: white; break-after: page; }
.sheet:last-child { break-after: auto; }
h1 { margin: 0 0 .10in; font-size: 14pt; font-weight: 600; }
p { margin: 0 0 .12in; font-size: 10pt; line-height: 1.25; }
img { display: block; width: 14in; height: 8.75in; object-fit: contain; border: 1px solid #d7e0e4; }
@media screen { .sheet { margin: 16px auto; box-shadow: 0 2px 8px #0002; } }
</style></head><body>${manifest.shots.map((shot, i) => `<section class="sheet"><h1>WB Credit | Screen ${String(i + 1).padStart(2, '0')} of ${manifest.shots.length} | Mock demo</h1><p>${escape(shot.caption)}</p><img src="${escape(shot.filename)}" alt="${escape(shot.caption)}"></section>`).join('\n')}</body></html>\n`)
const tmp = path.join(root, 'runtime/0024/gallery-tmp')
await mkdir(tmp, { recursive: true })
const browser = await chromium.launch({ ...(process.env.SCREEN_BROWSER === 'chromium' ? {} : { channel: 'chrome' }), headless: true, env: { ...process.env, TMPDIR: tmp } })
try {
  const page = await browser.newPage()
  await page.route('**/*', route => route.request().url().startsWith('file:') ? route.continue() : route.abort())
  await page.goto(pathToFileURL(path.join(output, 'gallery.html')).href)
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode())) })
  await page.pdf({ path: path.join(output, 'WB_Credit_screens.pdf'), preferCSSPageSize: true, printBackground: true })
  console.log(`Printed ${manifest.shots.length} screenshot pages.`)
} finally { await browser.close() }

// Render actual API snapshots using existing compiler tooling, without a browser dependency.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
const root = fileURLToPath(new URL('../', import.meta.url))
await build({ absWorkingDir: root, entryPoints: ['src/CaseDashboard.jsx', 'src/VersionHistory.jsx', 'src/DraftExport.jsx'],
  bundle: true, platform: 'node', format: 'esm', packages: 'external', jsx: 'automatic', splitting: true,
  loader: { '.css': 'empty' }, outdir: 'dist/gate2-check', outExtension: { '.js': '.mjs' }, logLevel: 'silent' })
const { default: Dashboard } = await import('../dist/gate2-check/CaseDashboard.mjs')
const { default: History } = await import('../dist/gate2-check/VersionHistory.mjs')
const { ExportPreview } = await import('../dist/gate2-check/DraftExport.mjs')
const dir = process.argv[2]
const read = async name => JSON.parse(await readFile(`${dir}/${name}.json`, 'utf8'))
const render = (Component, props) => renderToStaticMarkup(React.createElement(Component, props))
const css = await readFile(new URL('../src/styles.css', import.meta.url), 'utf8')
const escape = s => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;')
for (const name of ['empty', 'tranche-1', 'tranche-2', 'tranche-3', 'stale', 'redrafted']) {
  const data = await read(name)
  const html = render(Dashboard, { data, busy: false, actor: 'gate2-ca', run: async () => {} })
  for (const s of data.sections) assert.ok(html.includes(escape(`${s.section_id}. ${s.name}`)))
  for (const label of ['Saved draft progress', 'Saved sections', 'Stale · review required', 'Demo input progression', 'Draft template export', 'Preview draft export']) assert.ok(html.includes(label))
  assert.match(html, /<button class="primary" disabled="">Create draft bundle/)
  assert.match(html, /<button disabled="">Previous section/)
  assert.ok(html.includes(`<span aria-current="step"><b>${name === 'empty' ? 1 : 2}</b>`))
  if (name === 'stale') assert.match(html, /8 → 9 → 11 → 14/)
  await writeFile(`${dir}/${name}.html`, `<!doctype html><html><head><meta charset="utf-8"><title>Gate 2 ${name}</title><style>${css}</style></head><body><main>${html}</main></body></html>`)
}
const history = await read('history-stale')
const html = render(History, { history, live: history.section, caseId: history.section.case_id, showSource: () => {} })
assert.match(html, /Historical confirmation/)
assert.ok(!html.includes('Current CA confirmation'))
assert.match(html, /Stale/)
assert.ok(html.includes(escape(history.versions.at(-1).text)))
assert.match(html, /Legal review remains pending/)
const preview = await read('export-preview')
const exported = render(ExportPreview, { preview })
assert.match(exported, /DRAFT/)
assert.match(exported, /Template field and mapping gaps/)
assert.match(exported, /Industry code/)
for (const s of Object.values(preview.sections)) assert.ok(exported.includes(s.draft.id))
const hostile = { ...preview, status: '<script>untrusted</script>', blockers: ['<script>blocked</script>'] }
const escaped = render(ExportPreview, { preview: hostile })
assert.ok(!escaped.includes('<script>'))
assert.match(escaped, /Word export blocked/)
console.log('Gate 2 render checks passed: six tranche/stale snapshots, history, exact saved text, export gaps and escaping.')

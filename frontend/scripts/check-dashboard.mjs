// Offline render check using Vite's existing compiler dependency; no browser package.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const root = fileURLToPath(new URL('../', import.meta.url))
await build({ absWorkingDir: root, entryPoints: ['src/CaseDashboard.jsx'], bundle: true,
  platform: 'node', format: 'esm', packages: 'external', jsx: 'automatic', splitting: true,
  loader: { '.css': 'empty' }, outdir: 'dist/ssr-check', entryNames: 'dashboard-check', outExtension: { '.js': '.mjs' }, logLevel: 'silent' })
const { default: Dashboard } = await import('../dist/ssr-check/dashboard-check.mjs')
for (const file of process.argv.slice(2)) {
  const data = JSON.parse(await readFile(file, 'utf8'))
  const html = renderToStaticMarkup(React.createElement(Dashboard, { data, busy: false, actor: 'gate1-ca', run: () => {} }))
  const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;')
  assert.match(html, /SYNTHETIC DEMO DATA/)
  assert.match(html, /Found publicly/)
  assert.match(html, /Export request list/)
  assert.match(html, /No live search or model calls/)
  assert.match(html, /Generation not yet available/)
  for (const section of data.sections) {
    assert.ok(html.includes(escape(`${section.section_id}. ${section.name}`)), section.name)
    assert.ok(html.includes(escape(section.readiness)), section.readiness)
  }
  for (const doc of data.documents) assert.ok(html.includes(escape(doc.original_filename)), doc.original_filename)
  assert.ok(!html.includes('Drafted</span>'))
  const output = file.replace(/\.json$/, '.html')
  await writeFile(output, `<!doctype html><html lang="en"><head><meta charset="UTF-8"><title>Gate 1 render check</title><style>${await readFile(new URL('../src/styles.css', import.meta.url), 'utf8')}</style></head><body><main>${html}</main></body></html>`)
  console.log(`Rendered ${data.documents.length} documents and all 14 sections: ${file}`)
}

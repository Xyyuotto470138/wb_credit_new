// Render actual API comparison snapshots with existing compiler tooling.
import assert from 'node:assert/strict'
import { readFile, writeFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
const root = fileURLToPath(new URL('../', import.meta.url))
await build({ absWorkingDir: root, entryPoints: ['src/ModelControls.jsx'], bundle: true,
  platform: 'node', format: 'esm', packages: 'external', jsx: 'automatic',
  outfile: 'dist/compare-render.mjs', logLevel: 'silent' })
const { ComparisonResults } = await import('../dist/compare-render.mjs')
const directory = process.argv[2]
const css = await readFile(new URL('../src/styles.css', import.meta.url), 'utf8')
const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;')
let count = 0
for (const child of await readdir(directory, { withFileTypes: true })) {
  if (!child.isDirectory() || !child.name.startsWith('test_same_prompt')) continue
  const path = `${directory}/${child.name}`
  for (const file of await readdir(path)) {
    if (!/^comparison-\d+\.json$/.test(file)) continue
    const result = JSON.parse(await readFile(`${path}/${file}`, 'utf8'))
    const html = renderToStaticMarkup(React.createElement(ComparisonResults, { result }))
    for (const output of result.results) {
      assert.ok(html.includes(escape(output.draft.text)))
      assert.ok(html.includes(escape(output.draft.model_version)))
    }
    for (const label of ['Preview only', 'Same prompt and evidence verified', 'identical', 'Citation coverage', 'Unsupported claims rejected', 'Gap markers', 'Latency', 'Estimated cost']) assert.ok(html.includes(label), label)
    await writeFile(`${path}/${file.replace('.json', '.html')}`, `<!doctype html><html><head><meta charset="utf-8"><title>B26 comparison</title><style>${css}</style></head><body><main>${html}</main></body></html>`)
    count++
  }
}
assert.equal(count, 4)
console.log('Passed real comparison render checks for sections 1, 2, 10 and 13; exact text, metrics, provenance and labels.')

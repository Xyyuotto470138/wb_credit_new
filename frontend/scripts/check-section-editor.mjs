// Offline render verification with Vite's existing compiler. No browser dependency.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { editableClaim, sourcePageLabel } from '../src/sectionModel.js'

const root = fileURLToPath(new URL('../', import.meta.url))
await build({ absWorkingDir: root, entryPoints: ['src/SectionEditor.jsx'], bundle: true,
  platform: 'node', format: 'esm', packages: 'external', jsx: 'automatic', splitting: true,
  loader: { '.css': 'empty' }, outdir: 'dist/section-check', entryNames: 'editor',
  outExtension: { '.js': '.mjs' }, logLevel: 'silent' })
const { SectionContent } = await import('../dist/section-check/editor.mjs')
const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#x27;')
for (const file of process.argv.slice(2)) {
  const input = JSON.parse(await readFile(file, 'utf8'))
  for (const draft of Array.isArray(input) ? input : [input]) {
    const props = { draft, edits: {}, setEdits: () => {}, disabled: false, showSource: () => {} }
    const html = renderToStaticMarkup(React.createElement(SectionContent, props))
    const editable = draft.claim_spans.filter(editableClaim).length
    assert.equal((html.match(/<textarea/g) || []).length, editable)
    assert.ok(html.includes(escape(draft.text)), 'Exact saved text remains available')
    assert.match(html, /MOCK DRAFT/)
    const sources = draft.claim_spans[0].source_register
    for (const source of Object.values(sources)) {
      assert.ok(html.includes(escape(source.filename)))
      assert.ok(html.includes(escape(sourcePageLabel(source))))
      if (source.synthetic) assert.match(html, /SYNTHETIC DEMO DATA/)
      if (source.url) { assert.ok(html.includes(escape(source.url))); assert.ok(html.includes(source.retrieved_at)) }
    }
    if (draft.ca_edits) assert.match(html, /not independently verified/)
    const locked = renderToStaticMarkup(React.createElement(SectionContent, { ...props, disabled: true }))
    assert.equal((locked.match(/<textarea[^>]*readOnly=""/g) || []).length, editable)
    const editableId = draft.claim_spans.find(editableClaim)?.id
    if (editableId) {
      const hostile = renderToStaticMarkup(React.createElement(SectionContent, { ...props, edits: { [editableId]: '<script>alert("untrusted")</script>' } }))
      assert.ok(!hostile.includes('<script>'))
      assert.match(hostile, /&lt;script&gt;/)
    }
    const output = file.replace(/\.json$/, `-section-${draft.section_id}.html`)
    await writeFile(output, `<!doctype html><html lang="en"><head><meta charset="UTF-8"><title>Section editor render check</title><style>${await readFile(new URL('../src/styles.css', import.meta.url), 'utf8')}</style></head><body><main><section class="panel">${html}</section></main></body></html>`)
    console.log(`Section ${draft.section_id}: ${editable} editable claims; ${Object.keys(sources).length} cited source pages; text, locks and escaping verified.`)
  }
}

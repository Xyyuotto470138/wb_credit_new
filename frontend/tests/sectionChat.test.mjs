import assert from 'node:assert/strict'
import test from 'node:test'
import { build } from 'esbuild'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const root = fileURLToPath(new URL('../', import.meta.url))
await build({ absWorkingDir: root, entryPoints: ['src/SectionChat.jsx'], bundle: true,
  platform: 'node', format: 'esm', packages: 'external', jsx: 'automatic',
  outfile: 'dist/chat-check.mjs', logLevel: 'silent' })
const { ProposalReview } = await import('../dist/chat-check.mjs')
const proposal = { id: 'p', status: 'pending', model_version: 'mock:b24', base_draft_id: 'draft-1',
  proposed_text: 'CA input: <script>untrusted</script>\n[GAP] Missing evidence',
  payload: { request: { numeric: { metric_id: 'occupancy', period: '2025', scope: 'Group',
    basis: 'comparable lettable area', synthetic: true, operands: { occupied_area: [{ value: '40', unit: 'sqm' }] } } },
    results: [{ metric: 'occupancy', name: 'Occupancy', display: null, unit: 'percent', gaps: ['Missing operands: lettable_area'] }] } }

test('proposal renders sources, gaps and explicit numeric acceptance without unsafe HTML', () => {
  const html = renderToStaticMarkup(React.createElement(ProposalReview, { proposal, disabled: false,
    resolve: () => {}, acceptNumeric: false, setAcceptNumeric: () => {} }))
  assert.match(html, /SYNTHETIC DEMO DATA/)
  assert.match(html, /not independently verified/)
  assert.match(html, /Missing operands: lettable_area/)
  assert.match(html, /Occupancy: N\/A/)
  assert.match(html, /<button disabled="">Accept revision/)
  assert.match(html, /<button>Reject revision/)
  assert.ok(!html.includes('<script>'))
  assert.match(html, /&lt;script&gt;/)
})
test('resolved or stale proposals cannot be accepted; locks disable both decisions', () => {
  for (const status of ['accepted', 'rejected', 'stale']) {
    const html = renderToStaticMarkup(React.createElement(ProposalReview, { proposal: { ...proposal, status } }))
    assert.ok(!html.includes('<button'))
  }
  const html = renderToStaticMarkup(React.createElement(ProposalReview, { proposal, disabled: true,
    acceptNumeric: true, resolve: () => {}, setAcceptNumeric: () => {} }))
  assert.match(html, /<button disabled="">Accept revision/)
  assert.match(html, /<button disabled="">Reject revision/)
})

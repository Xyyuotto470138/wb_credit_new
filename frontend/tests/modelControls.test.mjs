import assert from 'node:assert/strict'
import test from 'node:test'
import { build } from 'esbuild'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
const root = fileURLToPath(new URL('../', import.meta.url))
await build({ absWorkingDir: root, entryPoints: ['src/ModelControls.jsx'], bundle: true,
  platform: 'node', format: 'esm', packages: 'external', jsx: 'automatic',
  outfile: 'dist/models-check.mjs', logLevel: 'silent' })
const { ComparisonResults, ModelCompare, CaseModelPicker } = await import('../dist/models-check.mjs')
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props))
const models = [
  { id: 'mock-v1', display_name: 'Mock A', runnable: true, weights: 'mock', model_id: 'mock-v1' },
  { id: 'mock-v2', display_name: 'Mock B', runnable: true, weights: 'mock', model_id: 'mock-v2' },
  { id: 'qwen-direct', display_name: 'Qwen', runnable: false, weights: 'hosted', bank_available: true },
]
test('picker disables hosted routes and locked case writes, shows pre-run mock estimate', () => {
  const html = render(CaseModelPicker, { data: { case: { default_model_id: 'mock-v1' }, model_registry: { models } }, actor: 'CA', disabled: true })
  assert.match(html, /disabled="">Save case default/)
  assert.match(html, /value="qwen-direct" disabled=""/)
  assert.match(html, /US\$0/)
  assert.match(html, /bank family available/)
  const comparison = render(ModelCompare, { models, disabled: true })
  assert.match(comparison, /disabled="">Compare section drafts/)
  assert.match(comparison, /Estimated combined cost: US\$0/)
})
test('comparison displays measured checks, escaped sourced text and empty coverage honestly', () => {
  const result = { computed_tables_identical: true, computed_table_count: 0, results: models.slice(0, 2).map(model => ({ model,
    draft: { model_version: model.id, text: '<script>bad</script> [GAP] Missing evidence' },
    metrics: { citation_coverage: { percent: null, total: 0, cited: 0, basis: 'Not semantic verification' },
      unsupported_claims_rejected: 1, malformed_response: true, omitted_claims: 2, gap_markers: ['Missing evidence'], latency_ms: 0.25, estimated_cost_usd: '0' } })) }
  const html = render(ComparisonResults, { result })
  for (const label of ['identical (0; none in this section)', 'N/A — no displayed claims', 'Unsupported claims rejected', 'Gap markers', 'Latency', 'Estimated cost', 'Preview only']) assert.ok(html.includes(label), label)
  assert.ok(!html.includes('<script>'))
  assert.match(html, /&lt;script&gt;/)
})

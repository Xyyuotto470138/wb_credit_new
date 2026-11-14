import assert from 'node:assert/strict'
import test from 'node:test'
import { changedClaims, editableClaim, sameRevision, sourcePageLabel, versionToken } from '../src/sectionModel.js'
import { post } from '../src/api/client.js'

test('protects computed cells, summary, rating, position and dedicated inputs', () => {
  const base = { id: 'c', kind: 'narrative', text: 'Supplied wording' }
  assert.ok(editableClaim(base))
  assert.ok(editableClaim({ ...base, kind: 'facility' }))
  for (const protectedFields of [{ computed_value_id: 'x' }, { computed_value_ids: ['x'] },
    { kind: 'computed_summary' }, { kind: 'ca_input' }, { kind: 'case_input' }, { kind: 'ca_position' },
    { internal_rating: true }, { requires_unsecured_confirmation: true }, { kind: 'draft_metadata' }]) {
    assert.equal(editableClaim({ ...base, ...protectedFields }), false)
  }
})
test('saves only changed existing editable claims, retaining local empty edits for validation', () => {
  const draft = { claim_spans: [{ id: 'c', kind: 'narrative', text: 'original' }, { id: 'p', kind: 'computed_summary', text: 'read only' }] }
  assert.deepEqual(changedClaims(draft, { c: 'original', unknown: 'no', p: 'no' }), {})
  assert.deepEqual(changedClaims(draft, { c: 'revised' }), { c: 'revised' })
  assert.deepEqual(changedClaims(draft, { c: '' }), { c: '' })
})
test('all three optimistic tokens bind actions to the loaded section, including upstream changes', async t => {
  const state = { current_draft_id: 'draft-1', editor_revision: 2, input_fingerprint: 'inputs-1' }
  assert.ok(sameRevision(state, { ...state }))
  assert.equal(sameRevision(null, state), false)
  for (const change of [{ current_draft_id: 'draft-2' }, { editor_revision: 3 }, { input_fingerprint: 'inputs-2' }]) {
    assert.equal(sameRevision(state, { ...state, ...change }), false)
  }
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/cases/demo/sections/8/save')
    assert.deepEqual(JSON.parse(options.body), { actor: 'CA', role: 'CA', expected_draft_id: 'draft-1',
      expected_revision: 2, expected_input_fingerprint: 'inputs-1', replacements: { c: 'revised' } })
    return { ok: false, status: 409, json: async () => ({ detail: 'Section revision or inputs changed' }) }
  })
  await assert.rejects(post('/cases/demo/sections/8/save', { ...versionToken(state, 'CA'), replacements: { c: 'revised' } }),
    error => error.status === 409 && /inputs changed/.test(error.message))
})
test('distinguishes original PDF, printed spread, region and normalized worksheet pages', () => {
  assert.equal(sourcePageLabel({ page: 59, printed_page: '114–115', region: 'bbox:[0,0,400,600]', locator: { format: 'pdf' } }),
    'PDF page 59 · printed 114–115 · region bbox:[0,0,400,600]')
  assert.equal(sourcePageLabel({ page: 2, region: 'whole', locator: { format: 'xlsx' } }), 'Normalized page 2')
})

test('typed CA sources never display a fabricated document page', () => {
  assert.equal(sourcePageLabel({ origin: 'CA input', message_id: 'message-1' }), 'CA input · message message-1')
})

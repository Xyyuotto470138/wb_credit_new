import assert from 'node:assert/strict'
import test from 'node:test'
import { draftProgress, trancheProgress, exportRevision, mergeExportHistory } from '../src/dashboardModel.js'

test('saved draft coverage and current confirmation stay separate on Stale content', () => {
  const sections = [
    { current_draft_id: 'v1', confirmed_draft_id: 'v1', readiness: 'Stale' },
    { current_draft_id: 'v2', readiness: 'CA confirmed' },
    { current_draft_id: 'v3', readiness: 'Drafted' },
    { readiness: 'Not applicable', na_reason: 'New client' },
    { readiness: 'Waiting for input' },
  ]
  assert.deepEqual(draftProgress(sections), { saved: 3, confirmed: 1, stale: 1, na: 1 })
})
test('demo tranche coverage counts only current matching hashes, not duplicate names or historical files', () => {
  const data = { intake: { presets: [{ tranche: 1, sha256: 'a' }, { tranche: 1, sha256: 'b' }, { tranche: 2, sha256: 'c' }] },
    documents: [{ content_hash: 'a', current: true }, { content_hash: 'a', current: true }, { content_hash: 'b', current: false }] }
  assert.deepEqual(trancheProgress(data), [{ number: 1, held: 1, total: 2 }, { number: 2, held: 0, total: 1 }, { number: 3, held: 0, total: 0 }])
})
test('export preview UI token invalidates on section, source, request and workflow changes', () => {
  const data = { case: { id: 'demo', workflow_state: 'Draft' }, sections: [{ current_draft_id: 'v1' }], documents: [], expected_documents: [] }
  for (const next of [
    { ...data, sections: [{ current_draft_id: 'v2' }] },
    { ...data, documents: [{ id: 'doc', confirmed_by: 'ca' }] },
    { ...data, expected_documents: [{ dismiss_reason: 'Pending' }] },
    { ...data, case: { ...data.case, workflow_state: 'Approved' } },
  ]) assert.notEqual(exportRevision(data), exportRevision(next))
})
test('late history responses retain newly created exports, deduplicate and sort chronologically', () => {
  const recent = { id: 'new', created_at: '2026-11-11T12:00:00Z', manifest: { status: 'DRAFT' } }
  const old = { id: 'old', created_at: '2026-11-10T12:00:00Z' }
  assert.deepEqual(mergeExportHistory([recent], [old]), [old, recent])
  assert.deepEqual(mergeExportHistory([recent], [recent, old]), [old, recent])
  assert.deepEqual(mergeExportHistory([recent], []), [recent])
})

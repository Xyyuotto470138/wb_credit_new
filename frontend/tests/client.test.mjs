import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { contentUrl, requestListUrl, request, post, upload, demoMetadata } from '../src/api/client.js'

test('encodes case and document references without allowing path injection', () => {
  assert.equal(contentUrl('a/b', 'x?y', true), '/api/cases/a%2Fb/documents/x%3Fy/content?preview=true')
  assert.equal(requestListUrl('a/b'), '/api/cases/a%2Fb/request-list')
})
test('preserves raw file bytes and structured metadata in upload request', async t => {
  const file = new File(['SYNTHETIC DEMO DATA'], 'term & sheet.pdf')
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    const parsed = new URL(url, 'http://localhost')
    assert.equal(parsed.searchParams.get('filename'), file.name)
    assert.deepEqual(JSON.parse(parsed.searchParams.get('metadata')), { entity: 'ESR-REIT', catalogue_id: 2 })
    assert.equal(options.body, file)
    assert.equal(options.headers['Content-Type'], 'application/octet-stream')
    return { ok: true, json: async () => ({ outcome: 'created' }) }
  })
  assert.deepEqual(await upload('demo', file, { entity: 'ESR-REIT', catalogue_id: 2 }), { outcome: 'created' })
})
test('uses supplied demo classifications only for verified content', async () => {
  const bytes = await readFile(new URL('../../demo/synthetic/tranche_1/term_sheet.pdf', import.meta.url))
  const file = new File([bytes], 'renamed.pdf')
  const preset = { sha256: '094d04bc31359b6677f71467b0d5e8d943957c262558133d23a1031707f3f5dd', metadata: { catalogue_id: 2, synthetic: true } }
  assert.deepEqual(await demoMetadata(file, [preset]), preset.metadata)
  assert.equal(await demoMetadata(new File(['Changed content'], 'term_sheet.pdf'), [preset]), undefined)
})
test('surfaces backend validation details, unreadable failures and network errors', async t => {
  t.mock.method(globalThis, 'fetch', async () => ({ ok: false, status: 422, json: async () => ({ detail: 'Actor is required' }) }))
  await assert.rejects(request('/cases'), /Actor is required/)
  globalThis.fetch = async () => ({ ok: false, status: 502, json: async () => { throw new Error('Bad JSON') } })
  await assert.rejects(request('/cases'), /Request failed \(502\)/)
  globalThis.fetch = async () => { throw new Error('Network unavailable') }
  await assert.rejects(request('/cases'), /Network unavailable/)
})
test('posts the explicit CA identity and action body', async t => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/cases/demo/public-search')
    assert.equal(options.method, 'POST')
    assert.deepEqual(JSON.parse(options.body), { actor: 'gate1-ca', role: 'CA' })
    return { ok: true, json: async () => ({ search: { outcome: 'found' } }) }
  })
  assert.equal((await post('/cases/demo/public-search', { actor: 'gate1-ca', role: 'CA' })).search.outcome, 'found')
})

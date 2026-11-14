import assert from 'node:assert/strict'
import test from 'node:test'
import { wordChanges, wordingView } from '../src/workbench/diff.js'

test('an edited sentence is shown word by word; a rewritten one is shown whole', () => {
  const edit = wordingView('The term loan is SGD 600,000,000 for five years.', 'The term loan is SGD 650,000,000 for five years.')
  assert.equal(edit.rewritten, false)
  assert.deepEqual(edit.pieces.filter(p => p.type !== 'same').map(p => [p.type, p.text]), [['del', '600,000,000'], ['add', '650,000,000']])
  assert.equal(wordingView('The valuation report gives a market value at the year end.', 'Conditions precedent include consent of the other partners.').rewritten, true)
  // Nothing to compare against is not a rewrite: new wording is shown as added.
  assert.equal(wordingView('', 'New paragraph.').rewritten, false)
  assert.deepEqual(wordChanges('a b', 'a b').map(p => p.type), ['same', 'same', 'same'])
})

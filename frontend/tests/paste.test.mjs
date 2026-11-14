import assert from 'node:assert/strict'
import test from 'node:test'
import { rowsFromHtml, rowsFromText, fromClipboard } from '../src/workbench/paste.js'

test('reads a table copied from Excel as tab-separated rows, kept as pasted', () => {
  assert.deepEqual(rowsFromText('Peer\tLeverage (%)\r\nDemo Peer A\t38.5\r\n\r\nDemo Peer B\t'), [['Peer', 'Leverage (%)'], ['Demo Peer A', '38.5'], ['Demo Peer B', '']])
  assert.equal(rowsFromText('A sentence without columns.'), null)
})
test('reads a table copied from Word or a web page, repeating merged cells as empty cells', () => {
  const cell = (text, span) => ({ textContent: text, getAttribute: () => span })
  const row = cells => ({ querySelectorAll: () => cells })
  const parse = () => ({ querySelector: () => ({ querySelectorAll: () => [row([cell(' Tenant name ', '2'), cell('Area')]), row([cell('A'), cell('B'), cell('1,200')]), row([cell(''), cell('')])] }) })
  assert.deepEqual(rowsFromHtml('<table><tr><td>x</td></tr></table>', parse), [['Tenant name', '', 'Area'], ['A', 'B', '1,200']])
  assert.equal(rowsFromHtml('<p>no table</p>', parse), null)
})
test('a paste is a table when it has columns, otherwise it is left as typed text', async () => {
  const data = (html, text) => ({ getData: type => type === 'text/html' ? html : text, files: [] })
  assert.deepEqual(await fromClipboard(data('', 'a\tb\n1\t2')), { kind: 'table', rows: [['a', 'b'], ['1', '2']] })
  assert.equal(await fromClipboard(data('', 'plain words')), null)
})

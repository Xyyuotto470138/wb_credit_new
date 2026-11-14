// Display-only text comparison for tracked changes. It never alters saved text.
function lcs(a, b) {
  const table = Array.from({ length: a.length + 1 }, () => new Uint32Array(b.length + 1))
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--) {
    table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1])
  }
  return table
}
export function diff(a, b) {
  const table = lcs(a, b), out = []
  let i = 0, j = 0
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { out.push({ type: 'same', text: a[i] }); i++; j++ }
    else if (table[i + 1][j] >= table[i][j + 1]) out.push({ type: 'del', text: a[i++] })
    else out.push({ type: 'add', text: b[j++] })
  }
  while (i < a.length) out.push({ type: 'del', text: a[i++] })
  while (j < b.length) out.push({ type: 'add', text: b[j++] })
  return out
}
const words = text => text.split(/(\s+)/).filter(Boolean)
// Two wordings compared word by word, as one list of {type, text} pieces with unchanged words kept.
export const wordChanges = (before, after) => diff(words(before), words(after))
// Changed blocks only, each as a list of {type, text} pieces. A line that was reworded is compared word by word.
export function trackedChanges(before, after) {
  const lines = diff(before.split('\n'), after.split('\n'))
  const blocks = []
  for (let i = 0; i < lines.length;) {
    if (lines[i].type === 'same') { i++; continue }
    const removed = [], added = []
    while (i < lines.length && lines[i].type !== 'same') { (lines[i].type === 'del' ? removed : added).push(lines[i].text); i++ }
    const paired = Math.min(removed.length, added.length)
    for (let k = 0; k < paired; k++) blocks.push(diff(words(removed[k]), words(added[k])))
    for (const text of removed.slice(paired)) if (text.trim()) blocks.push([{ type: 'del', text }])
    for (const text of added.slice(paired)) if (text.trim()) blocks.push([{ type: 'add', text }])
  }
  return blocks
}
// Word by word marks read well for an edit and badly for a rewrite. When under half of the words survive, show the two wordings whole.
export function wordingView(before, after) {
  const pieces = wordChanges(before, after)
  const words = pieces.filter(p => p.text.trim())
  const same = words.filter(p => p.type === 'same').length
  return { pieces, rewritten: !!before.trim() && !!after.trim() && words.length > 0 && same / words.length < 0.5 }
}

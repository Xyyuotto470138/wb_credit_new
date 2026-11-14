// Turns what the analyst pastes into a block: a table (from Excel or Word), a screenshot, or plain text.
// Content is taken as pasted. Nothing is recalculated or reworded.
const tidy = text => String(text ?? '').replaceAll(String.fromCharCode(160), ' ').replace(/\s+/g, ' ').trim()
const square = rows => {
  const kept = rows.filter(row => row.some(cell => cell))
  const width = Math.max(0, ...kept.map(row => row.length))
  return kept.map(row => [...row, ...Array(width - row.length).fill('')])
}

// Excel and most tools put tab-separated rows on the clipboard as plain text.
export function rowsFromText(text) {
  const lines = String(text ?? '').replace(/\r\n?/g, '\n').split('\n').filter(line => line.trim())
  if (!lines.some(line => line.includes('\t'))) return null
  return square(lines.map(line => line.split('\t').map(tidy)))
}

// Word and web pages put an HTML table on the clipboard. Merged cells are repeated as empty cells.
export function rowsFromHtml(html, parse = source => new DOMParser().parseFromString(source, 'text/html')) {
  if (!/<table/i.test(html || '')) return null
  const table = parse(html).querySelector('table')
  if (!table) return null
  const rows = [...table.querySelectorAll('tr')].map(row => [...row.querySelectorAll('th,td')].flatMap(cell =>
    [tidy(cell.textContent), ...Array(Math.max(0, (Number(cell.getAttribute('colspan')) || 1) - 1)).fill('')]))
  const result = square(rows)
  return result.length ? result : null
}

export const readImage = file => new Promise((resolve, reject) => {
  if (!/^image\/(png|jpeg)$/.test(file.type)) return reject(new Error('Only PNG and JPEG images can be added.'))
  if (file.size > 8 * 1024 * 1024) return reject(new Error('An image can be up to 8 MB.'))
  const reader = new FileReader()
  reader.onload = () => resolve(reader.result)
  reader.onerror = () => reject(new Error('The image could not be read.'))
  reader.readAsDataURL(file)
})

// What a paste event holds, in order of preference: an image, a table, otherwise nothing special (plain text is typed in).
export async function fromClipboard(data) {
  const html = data.getData('text/html'), text = data.getData('text/plain')
  const table = rowsFromHtml(html) || rowsFromText(text)
  if (table && (table.length > 1 || table[0].length > 1)) return { kind: 'table', rows: table.slice(0, 80).map(row => row.slice(0, 14)) }
  const image = [...(data.files || [])].find(file => file.type.startsWith('image/'))
  if (image) return { kind: 'image', image_data: await readImage(image) }
  return null
}

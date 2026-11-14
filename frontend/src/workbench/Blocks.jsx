import { useRef, useState } from 'react'
import { fromClipboard, readImage } from './paste'

const LABEL = 'Analyst added. Not checked by the system.'

function Content({ block, caseId, image }) {
  if (block.kind === 'text') return block.text.split('\n').filter(line => line.trim()).map((line, i) => <p key={i}>{line}</p>)
  if (block.kind === 'table') return <div className="scroll"><table><tbody>{block.rows.map((row, i) => <tr key={i}>{row.map((cell, k) =>
    i === 0 && block.header !== false ? <th key={k}>{cell}</th> : <td key={k} className={/^-?[\d,.()]+%?x?$/.test(cell) ? 'r' : ''}>{cell}</td>)}</tr>)}</tbody></table></div>
  return <img className="shot" src={image || `/api/cases/${encodeURIComponent(caseId)}/blocks/${encodeURIComponent(block.image)}`} alt={block.title || 'Image added by the analyst'} />
}

// The composer: paste a table or a screenshot, or type text. Used for a new block and for changing a text block.
function Composer({ initial, onSave, onCancel, busy }) {
  const [draft, setDraft] = useState(initial || { kind: 'text', text: '', title: '' })
  const [error, setError] = useState('')
  const file = useRef(null)
  const take = found => { setError(''); setDraft(previous => ({ ...found, title: previous.title || '', header: true })) }
  const paste = event => {
    const data = event.clipboardData
    const special = /<table/i.test(data.getData('text/html')) || data.getData('text/plain').includes('\t') || [...(data.files || [])].some(f => f.type.startsWith('image/'))
    if (!special || initial) return  // plain text goes into the box as typed
    event.preventDefault()
    fromClipboard(data).then(found => found && take(found)).catch(e => setError(e.message))
  }
  const choose = event => {
    const chosen = event.target.files[0]
    if (chosen) readImage(chosen).then(image_data => take({ kind: 'image', image_data })).catch(e => setError(e.message))
    event.target.value = ''
  }
  const ready = draft.kind === 'text' ? draft.text.trim() : draft.kind === 'table' ? draft.rows?.length : draft.image_data
  return <div className="composer-block" onPaste={paste}>
    <input className="title" aria-label="Title (optional)" placeholder="Title (optional)" maxLength={200} value={draft.title || ''} onChange={e => { const title = e.target.value; setDraft(previous => ({ ...previous, title })) }} />
    {draft.kind === 'text' && <textarea aria-label="Text to add" rows={4} maxLength={20000} autoFocus value={draft.text}
      placeholder={initial ? '' : 'Type here, or paste a table from Excel or Word, or a screenshot'} onChange={e => { const text = e.target.value; setDraft(previous => ({ ...previous, text })) }} />}
    {draft.kind === 'table' && <><Content block={draft} />
      <label className="check"><input type="checkbox" checked={draft.header !== false} onChange={e => { const header = e.target.checked; setDraft(previous => ({ ...previous, header })) }} />The first row is a heading row</label></>}
    {draft.kind === 'image' && <Content block={draft} image={draft.image_data} />}
    {error && <p className="part-gap">{error}</p>}
    <div className="row">
      {!initial && <><button className="btn small" disabled={busy} onClick={() => file.current.click()}>Choose an image</button>
        <input ref={file} type="file" accept="image/png,image/jpeg" hidden onChange={choose} />
        {draft.kind !== 'text' && <button className="btn small" disabled={busy} onClick={() => setDraft({ kind: 'text', text: '', title: draft.title })}>Start again</button>}</>}
      <span className="spacer" />
      <button className="btn small" disabled={busy} onClick={onCancel}>Cancel</button>
      <button className="btn small primary" disabled={busy || !ready} onClick={() => onSave(draft)}>{initial ? 'Save' : 'Add to section'}</button>
    </div>
    <small>{LABEL} It is kept exactly as you add it and goes into the Word ES at this place.</small>
  </div>
}

export function AddBlock({ after, ops, busy }) {
  const [open, setOpen] = useState(false)
  if (!ops) return null
  if (!open) return <button className="add-block" disabled={busy} onClick={() => setOpen(true)}>+ Add text, a table or a screenshot here</button>
  return <Composer busy={busy} onCancel={() => setOpen(false)} onSave={draft => {
    setOpen(false)
    ops({ op: 'add', kind: draft.kind, after, title: draft.title || '', ...(draft.kind === 'text' ? { text: draft.text } : draft.kind === 'table' ? { rows: draft.rows, header: draft.header !== false } : { image_data: draft.image_data }) })
  }} />
}

// Model suggestions for one table. Each is a prompt for a human check; marking it records that a person looked.
export function Suggested({ findings, resolutions = {}, onResolve, busy }) {
  if (!findings?.length) return null
  return <div className="suggested">{findings.map(f => {
    const done = resolutions[f.id]
    return <div key={f.id} className={done ? 'done' : ''}><b>Suggested check</b>
      <span>{[f.row_label, f.column].filter(Boolean).join(', ')}{(f.row_label || f.column) && ': '}{f.reason}</span>
      {done ? <small>Looked at by {done.actor}{done.note ? `: ${done.note}` : ''}</small>
        : onResolve && <button className="link" disabled={busy} onClick={() => onResolve(f.id)}>Mark as looked at</button>}</div>
  })}</div>
}

export function BlockList({ blocks, caseId, ops, busy, sense, onResolve }) {
  const [editing, setEditing] = useState(null)
  return blocks.map(block => <div key={block.id} className="analyst-block">
    {editing === block.id
      ? <Composer busy={busy} initial={block.kind === 'text' ? { kind: 'text', text: block.text, title: block.title } : { ...block }} onCancel={() => setEditing(null)}
          onSave={draft => { setEditing(null); ops({ op: 'update', block_id: block.id, title: draft.title || '', ...(block.kind === 'text' ? { text: draft.text } : block.kind === 'table' ? { rows: block.rows, header: draft.header !== false } : {}) }) }} />
      : <>{block.title && <h5>{block.title}</h5>}
        <Content block={block} caseId={caseId} />
        <Suggested findings={sense?.findings.filter(f => f.table === `block:${block.id}`)} resolutions={sense?.resolutions} onResolve={onResolve} busy={busy} />
        <div className="row"><span className="tag">Analyst added</span><small>Not checked by the system · {block.updated_by || block.author}</small><span className="spacer" />
          {ops && <><button className="link" disabled={busy} onClick={() => ops({ op: 'move', block_id: block.id, direction: 'up' })}>Move up</button>
            <button className="link" disabled={busy} onClick={() => ops({ op: 'move', block_id: block.id, direction: 'down' })}>Move down</button>
            <button className="link" disabled={busy} onClick={() => setEditing(block.id)}>Edit</button>
            <button className="link" disabled={busy} onClick={() => { if (window.confirm('Remove this block from the section? Earlier versions keep it.')) ops({ op: 'delete', block_id: block.id }) }}>Remove</button></>}</div></>}
  </div>)
}

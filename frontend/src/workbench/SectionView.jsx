import { editableClaim } from '../sectionModel'
import { buildBlocks, columnLabel, formatValue } from './sectionContent'
import { AddBlock, BlockList, Suggested } from './Blocks'

const HIDDEN_COLUMNS = ['currency', 'entity', 'period', 'basis']
const Cites = ({ cites, onCite }) => cites.map(c => <sup key={c.id} className="cite" role="button" tabIndex={0} title="Show source"
  onClick={() => onCite(c.id)} onKeyDown={e => e.key === 'Enter' && onCite(c.id)}>{c.n}</sup>)

function Text({ claim, cites, onCite, editing, edits, setEdits }) {
  if (editing && editableClaim(claim)) return <textarea aria-label="Section wording" rows={4} value={edits[claim.id] ?? claim.text}
    onChange={e => setEdits(previous => ({ ...previous, [claim.id]: e.target.value }))} />
  return <>{claim.text}<Cites cites={cites} onCite={onCite} />
    {claim.ca_edit && <span className="note"> Edited by the CA.</span>}
    {(claim.ca_input || claim.kind === 'ca_input' || claim.ca_position) && <span className="note"> CA input, not independently verified.</span>}</>
}

function Measures({ rows, onCite }) {
  return <div className="scroll"><span className="calc"><b>Computed</b> by the system from cited inputs. Not editable.</span><table><thead><tr><th>Measure</th><th className="r">Value</th><th>Period</th><th>Scope</th></tr></thead><tbody>
    {rows.map((row, k) => <tr key={k}><td>{row.name}{row.claim.value.proxy && ' (proxy)'}<Cites cites={row.cites} onCite={onCite} /></td>
      <td className="r">{formatValue(row.claim.value.value, row.claim.value.unit === 'currency' ? 'currency' : row.claim.value.unit)}{row.claim.value.unit === 'currency' && ` ${row.claim.value.currency || ''}`}</td><td>{row.claim.value.period}</td><td>{row.claim.value.scope}</td></tr>)}</tbody></table></div>
}

function ComputedTable({ table }) {
  if (!table.rows?.length) return null
  const columns = Object.keys(table.rows[0]).filter(key => !HIDDEN_COLUMNS.includes(key))
  const unit = key => table.cells?.find(c => c.metric?.endsWith(`/${key}`))?.unit || ''
  const period = table.rows[0].period
  return <div className="computed">
    <span className="calc"><b>Computed</b> by the system from cited inputs. Not editable.{period ? ` As at ${period}.` : ''}</span>
    <div className="scroll"><table><thead><tr>{columns.map(key => <th key={key}>{columnLabel(key)}</th>)}</tr></thead><tbody>
      {table.rows.map((row, i) => <tr key={i}>{columns.map(key => <td key={key}>{formatValue(row[key], /^\d{4}-/.test(String(row[key])) ? '' : unit(key).replace('currency_million', ''))}</td>)}</tr>)}
      {table.totals && <tr className="total">{columns.map((key, i) => <td key={key}>{i === 0 ? 'Total' : formatValue(table.totals[key] ?? '', '')}</td>)}</tr>}
    </tbody></table></div>
  </div>
}

export function SectionBody({ draft, onCite, editing = false, edits = {}, setEdits }) {
  const { blocks, metadata, tables } = buildBlocks(draft)
  const text = (item, key) => <Text key={key} claim={item.claim} cites={item.cites} onCite={onCite} editing={editing} edits={edits} setEdits={setEdits} />
  return <>
    <p className="label">{metadata.label || 'Draft for CA review'}</p>
    {tables.map((table, i) => <ComputedTable key={i} table={table} />)}
    {blocks.map((block, i) => block.type === 'heading' ? <h4 key={i}>{block.text}</h4>
      : block.type === 'para' ? <p key={i}>{text(block, i)}</p>
      : block.type === 'facilities' ? <div className="scroll" key={i}><table><thead><tr><th>Key terms</th>{block.names.map(name => <th key={name}>{name}</th>)}</tr></thead><tbody>
        {block.fields.map(field => <tr key={field}><th>{field}</th>{block.names.map(name => <td key={name}>
          {(block.cells[`${field}|${name}`] || []).map((item, k) => <div key={k}>{text(item, k)}</div>)}</td>)}</tr>)}</tbody></table></div>
      : block.type === 'financials' ? <div className="scroll" key={i}><table><thead><tr><th>SGD'000 unless marked (m = SGD million)</th>{block.periods.map(p => <th key={p} className="r">{p}</th>)}</tr></thead><tbody>
        {block.labels.map(label => <tr key={label}><td>{label}</td>{block.periods.map(p => {
          const item = block.cells[`${label}|${p}`]
          return <td key={p} className="r">{item ? <>{formatValue(item.claim.reviewed_value.value, item.claim.reviewed_value.unit)}<Cites cites={item.cites} onCite={onCite} /></> : <span className="gap-cell">Gap</span>}</td>
        })}</tr>)}</tbody></table></div>
      : <div key={i}>{block.rows.length > 0 && <Measures rows={block.rows} onCite={onCite} />}
        {block.spread.length > 0 && <details className="more"><summary>Financial spread figures ({block.spread.length})</summary><Measures rows={block.spread} onCite={onCite} /></details>}</div>)}
  </>
}

const cellCites = (cell, numbering) => (cell.cites || []).filter(id => numbering.has(id)).map(id => ({ id, n: numbering.get(id) }))

function Cell({ cell, numbering, onCite, head }) {
  const Tag = head || cell.status === 'label' ? 'th' : 'td'
  return <Tag className={/^-?[\d,.]+%?x?$/.test(cell.text || '') ? 'r' : ''}>
    {cell.status === 'gap' ? <span className="gap-cell">Not provided</span> : cell.text}
    {(cell.sections || []).map(n => <span key={n} className="note"> (see section {n})</span>)}
    <Cites cites={cellCites(cell, numbering)} onCite={onCite} /></Tag>
}

// A section drafted from the team's ES specification: every part in template order.
function SpecBody({ draft, layout, caseId, onCite, editing, edits, setEdits, blockOps, busy, sense, onResolve }) {
  const { numbering, metadata } = buildBlocks(draft)
  const claims = draft.claim_spans.slice(1)
  const notes = claims.filter(c => c.kind === 'ca_input')
  // Content the analyst added sits after the part it follows; a block whose part has gone is shown at the end.
  const keys = layout.parts.map(part => part.key)
  const added = after => {
    const blocks = (metadata.blocks || []).filter(b => after === null ? b.after !== '' && !keys.includes(b.after) : b.after === after)
    return <>{blocks.length > 0 && <BlockList blocks={blocks} caseId={caseId} ops={blockOps} busy={busy} sense={sense} onResolve={onResolve} />}
      {after !== null && <AddBlock after={after} ops={blockOps} busy={busy} />}</>
  }
  return <>
    <p className="label">{metadata.label}</p>
    {added('')}
    {layout.parts.map(part => {
      const body = metadata.parts[part.key] || {}
      const own = claims.filter(c => c.part === part.key)
      const note = body.note && <p className={body.status === 'gap' ? 'part-gap' : 'part-note'}>{body.note}</p>
      const found = sense?.findings.filter(f => f.table === part.key) || []
      const flagged = new Set(found.filter(f => !sense.resolutions[f.id]).map(f => f.row))
      return <div key={part.key} className="part">
        {part.title && <h4>{part.title}</h4>}
        {own.map(claim => <p key={claim.id}><Text claim={claim} cites={cellCites({ cites: claim.evidence_ids }, numbering)} onCite={onCite} editing={editing} edits={edits} setEdits={setEdits} />
          {(claim.section_refs || []).map(n => <span key={n} className="note"> (see section {n})</span>)}</p>)}
        {part.type === 'narrative' && !own.length && (note || <p className="part-gap">Not drafted.</p>)}
        {part.type !== 'narrative' && !body.rows?.length && !body.answers && !body.slots?.length && note}
        {(part.type === 'table' || part.type === 'keyvalue') && body.rows?.length > 0 && <div className="scroll"><table className={part.type === 'keyvalue' ? 'kv' : ''}>
          {body.columns && <thead><tr>{body.columns.map((name, i) => <th key={i}>{name}</th>)}</tr></thead>}
          <tbody>{body.rows.map((row, i) => <tr key={i} className={flagged.has(i) ? 'flag' : ''}>{row.map((cell, k) => <Cell key={k} cell={cell} numbering={numbering} onCite={onCite} />)}</tr>)}
            {body.total && <tr className="total">{body.total.map((cell, k) => <Cell key={k} cell={cell} numbering={numbering} onCite={onCite} />)}</tr>}</tbody></table></div>}
        <Suggested findings={found} resolutions={sense?.resolutions} onResolve={onResolve} busy={busy} />
        {part.type === 'choice' && (body.answers || []).map((answer, i) => <div key={i} className="choice"><b>{answer.question}</b>
          <span>{answer.options.map(option => <span key={option} className={option === answer.selected ? 'on' : ''}>{option === answer.selected ? '☒' : '☐'} {option}</span>)}</span>
          {answer.note && <small>{answer.note}<Cites cites={cellCites(answer, numbering)} onCite={onCite} /></small>}</div>)}
        {part.type === 'image' && body.slots?.length > 0 && <div className={`images n${body.slots.length}`}>{body.slots.map((slot, i) => <figure key={i}>
          <img src={`/api/cases/${encodeURIComponent(caseId)}/assets?path=${encodeURIComponent(slot.path)}`} alt={slot.caption} /><figcaption>{slot.caption}</figcaption></figure>)}</div>}
        {added(part.key)}
      </div>
    })}
    {added(null)}
    {notes.length > 0 && <div className="part"><h4>Credit analyst's notes</h4>
      {notes.map(claim => <p key={claim.id}><Text claim={{ ...claim, text: claim.text.replace(/^CA input \(verbatim; not independently verified\):\n/, '') }} cites={cellCites({ cites: claim.evidence_ids }, numbering)} onCite={onCite} editing={false} edits={edits} setEdits={setEdits} /></p>)}</div>}
  </>
}

export default function SectionView({ section, draft, gaps, children, layout, caseId, ...body }) {
  return <article className="paper">
    <h2><span>{section.section_id}.</span>{section.name.toUpperCase()}</h2>
    <div className="box">
      {children}
      {draft ? (draft.claim_spans[0]?.parts && layout ? <SpecBody draft={draft} layout={layout} caseId={caseId} {...body} /> : <SectionBody draft={draft} {...body} />) : <p className="empty">{section.applicable ? 'No draft yet.' : `Not applicable. ${section.na_reason || ''}`}</p>}
      {gaps.slice(0, 3).map(gap => <div className="gap" key={gap}><b>Gap:</b> {gap}</div>)}
      {gaps.length > 3 && <details className="more"><summary>{gaps.length - 3} more gap{gaps.length === 4 ? '' : 's'}</summary>{gaps.slice(3).map(gap => <div className="gap" key={gap}><b>Gap:</b> {gap}</div>)}</details>}
    </div>
  </article>
}

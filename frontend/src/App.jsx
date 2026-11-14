import { useCallback, useEffect, useRef, useState } from 'react'
import CaseDashboard from './CaseDashboard'
import { dashboard, request } from './api/client'

export default function App() {
  const [cases, setCases] = useState([])
  const [caseId, setCaseId] = useState('')
  const [data, setData] = useState(null)
  const [actor, setActor] = useState('demo-ca')
  const [busy, setBusy] = useState(false)
  const [editorDirty, setEditorDirty] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)
  const sequence = useRef(0)
  const actionLock = useRef(false)
  const refresh = useCallback(async id => {
    const ticket = ++sequence.current
    const next = await dashboard(id)
    if (ticket === sequence.current) setData(next)
  }, [])
  useEffect(() => {
    let cancelled = false
    request('/cases').then(list => {
      if (cancelled) return
      setCases(list)
      setCaseId(list[0]?.id || '')
      setLoaded(true)
    }).catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [])
  useEffect(() => {
    if (!caseId) return
    const ticket = ++sequence.current
    dashboard(caseId).then(next => {
      if (ticket === sequence.current) setData(next)
    }).catch(e => { if (ticket === sequence.current) setError(e.message) })
    return () => { sequence.current += 1 }
  }, [caseId])
  const run = async (label, operation) => {
    if (actionLock.current) return
    actionLock.current = true
    setBusy(true); setError(''); setNotice(`${label}…`)
    let result
    try { result = await operation() } catch (e) { setError(e.message) }
    try { await refresh(caseId) } catch (e) { setError(`Refresh failed: ${e.message}. Reload before relying on the displayed status.`) }
    setNotice(result || '')
    setBusy(false); actionLock.current = false
  }
  return <>
    <header className="app-header"><a href="#" className="brand">WB <span>Credit</span></a><span className="workspace-label">Credit analyst workspace</span><div className="header-controls">
      {cases.length > 1 && <label>Case<select value={caseId} disabled={busy || editorDirty} onChange={e => { setData(null); setCaseId(e.target.value) }}>{cases.map(c => <option key={c.id} value={c.id}>{c.borrower_name} · {c.case_type}</option>)}</select></label>}
      <label>CA name<input aria-label="CA name" value={actor} disabled={busy} onChange={e => setActor(e.target.value)} maxLength="200" /></label>
    </div></header>
    <main aria-busy={busy}>
      <div className="feedback" aria-live="polite">{notice && <p role="status">{notice}</p>}</div>
      {error && <div className="error" role="alert"><p>{error}</p><button disabled={busy} onClick={() => caseId ? run('Refreshing', async () => 'Status refreshed.') : window.location.reload()}>Retry</button></div>}
      {!data && !error && <p>{caseId ? 'Loading case…' : loaded ? 'No cases available. Start the local demo backend to seed the synthetic case.' : 'Loading cases…'}</p>}
      {data && <><div className="refresh-row"><span>Local prototype · saved sources and mock provider</span><button disabled={busy} onClick={() => run('Refreshing', async () => 'Status refreshed.')}>Refresh status</button></div>
        <CaseDashboard key={caseId} data={data} actor={actor} busy={busy} run={run} onDirtyChange={setEditorDirty} /></>}
    </main>
    <footer>WB Credit · Intake review supports the credit analyst’s work. Credit decisions remain with the designated human reviewers.</footer>
  </>
}

import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { dashboard, request } from '../api/client'
import TopBar from './TopBar'
import InputsScreen from './InputsScreen'
import Workbench from './Workbench'
import PapersScreen from './PapersScreen'
import { ROLES } from './status'

const ClassicApp = lazy(() => import('../ClassicApp'))
const route = () => {
  const [view = 'inputs', tab] = window.location.hash.replace(/^#\/?/, '').split('/')
  return { view: ['inputs', 'workbench', 'classic', 'papers'].includes(view) ? view : 'inputs', tab: tab || '' }
}

export default function Root({ user, signOut }) {
  const [where, setWhere] = useState(route)
  const [data, setData] = useState(null)
  const [spec, setSpec] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [assistantOpen, setAssistantOpen] = useState(() => window.innerWidth > 1000)
  const lock = useRef(false)
  // The paper being worked on and the role being shown are kept in this browser, so a reload returns to the same place.
  const stored = key => { try { return window.localStorage.getItem(key) } catch { return null } }
  const keep = (key, value) => { try { window.localStorage.setItem(key, value) } catch { /* private mode: not kept */ } }
  const [papers, setPapers] = useState([])
  const paper = useRef(stored('wb.paper'))
  // A signed-in person works in their own role only. Without sign-in the role is a demo switch.
  const [picked, setRole] = useState(() => ROLES[stored('wb.role')] ? stored('wb.role') : 'CA')
  const role = user ? user.role : picked
  const actor = ROLES[role].actor
  useEffect(() => {
    const changed = () => {
      // The classic view loads its own global styles; start clean when leaving it.
      if (where.view === 'classic' && route().view !== 'classic') window.location.reload()
      else setWhere(route())
    }
    window.addEventListener('hashchange', changed)
    return () => window.removeEventListener('hashchange', changed)
  }, [where.view])
  const refresh = useCallback(async () => {
    const list = await request('/papers')
    if (!list.length) throw new Error('No case found. Start the local demo back end first.')
    setPapers(list)
    const id = list.some(p => p.id === paper.current) ? paper.current : list[0].id
    paper.current = id
    const next = await dashboard(id)
    setData(next)
    request(`/cases/${encodeURIComponent(id)}/es-spec`).then(setSpec).catch(() => setSpec(null))
    return next
  }, [])
  const choose = id => {
    paper.current = id; keep('wb.paper', id); setData(null); setSpec(null)
    refresh().then(next => { window.location.hash = next.sections.some(s => s.current_draft_id) ? '#/workbench/full' : '#/inputs' }).catch(e => setError(e.message))
  }
  const changeRole = next => { keep('wb.role', next); setRole(next) }
  useEffect(() => { refresh().catch(e => setError(e.message)) }, [refresh])
  // One action at a time: show what is running, then reload the case so every status is current.
  const run = useCallback(async (label, operation) => {
    if (lock.current) return
    lock.current = true
    setBusy(label); setError('')
    try { return await operation() }
    catch (e) { setError(e.message) }
    finally {
      try { await refresh() } catch (e) { setError(e.message) }
      setBusy(''); lock.current = false
    }
  }, [refresh])
  if (where.view === 'classic') return <Suspense fallback={<p>Loading…</p>}><p className="classic-back"><a href="#/inputs">← Back to Inputs</a></p><ClassicApp /></Suspense>
  return <div className="wb">
    <TopBar data={data} spec={spec} view={where.view} assistantOpen={assistantOpen} toggleAssistant={() => setAssistantOpen(open => !open)}
      papers={papers} choose={choose} role={role} changeRole={user ? null : changeRole} />
    {busy && <div className="wb-busy" role="status">{busy}…</div>}
    {error && <div className="wb-error" role="alert">{error} <button className="btn small" onClick={() => setError('')}>Dismiss</button></div>}
    {!data && !error && <p className="wb-loading">Loading case…</p>}
    {where.view === 'papers' && papers.length > 0 && <PapersScreen papers={papers} current={data?.case.id} role={role} choose={choose} />}
    {data && where.view === 'inputs' && <InputsScreen key={data.case.id} data={data} spec={spec} actor={actor} busy={!!busy} run={run} />}
    {data && where.view === 'workbench' && <Workbench key={data.case.id} data={data} spec={spec} actor={actor} role={role} busy={!!busy} run={run} tab={where.tab}
      assistantOpen={assistantOpen} closeAssistant={() => setAssistantOpen(false)} />}
    <footer className="wb-foot">{data?.synthetic_demo && 'SYNTHETIC DEMO DATA · '}{spec ? 'AI drafts are checked against cited sources' : 'Mock mode, no live model calls'} · Drafts are for analyst review. Credit decisions are made by the approving officers.{user && <span className="who"> · Signed in as {user.name} <button onClick={signOut}>Sign out</button></span>}</footer>
  </div>
}

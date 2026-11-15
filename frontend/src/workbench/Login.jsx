import { useState } from 'react'
import logo from '../../../templates/UOB_logo.png'
import { post } from '../api/client'
import Root from './Root'
import { ROLES } from './status'

// Demo sign-in (see backend/app/api/auth.py). The signed-in person is kept for this browser tab only.
const KEY = 'wb.user'
const saved = () => {
  try {
    const user = JSON.parse(window.sessionStorage.getItem(KEY))
    return user && ROLES[user.role] ? user : null
  } catch { return null }
}

export default function Gate() {
  const [user, setUser] = useState(saved)
  const signIn = next => {
    try {
      window.sessionStorage.setItem(KEY, JSON.stringify(next))
      window.localStorage.setItem('wb.role', next.role) // the workbench opens in this person's role
    } catch { /* private mode: signed in until the page is reloaded */ }
    setUser(next)
  }
  const signOut = () => {
    try { window.sessionStorage.removeItem(KEY) } catch { /* nothing kept */ }
    setUser(null)
  }
  return user ? <Root user={user} signOut={signOut} /> : <Login signIn={signIn} />
}

function Login({ signIn }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async event => {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError('')
    try { signIn(await post('/auth/login', { username, password })) }
    catch (e) {
      setError(e.status === 401 || e.status === 503 ? e.message : 'Could not reach the server. Check that the back end is running and try again.')
      setPassword(''); setBusy(false)
    }
  }
  return <main className="login">
    <form className="login-card" onSubmit={submit}>
      <img className="logo" src={logo} alt="UOB" />
      <h1>WB Credit</h1>
      <p className="sub">Sign in to the credit analyst workbench</p>
      <label>Username<input name="username" autoComplete="username" autoCapitalize="none" spellCheck="false" autoFocus required maxLength="200"
        value={username} onChange={e => setUsername(e.target.value)} /></label>
      <label>Password<input name="password" type="password" autoComplete="current-password" required maxLength="200"
        value={password} onChange={e => setPassword(e.target.value)} /></label>
      {error && <p className="login-error" role="alert">{error}</p>}
      <button className="btn primary" type="submit" disabled={busy || !username || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
      <p className="note">Prototype with demo accounts. Do not enter your real UOB password.</p>
    </form>
  </main>
}

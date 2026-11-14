import { useState } from 'react'

const REPLY = {
  pending: 'I have suggested a change, marked up in the section. Nothing changes until you accept it.',
  accepted: 'Change accepted. It is saved as a new version of the section.',
  rejected: 'Change rejected. The section is unchanged.',
  stale: 'The section changed after this suggestion, so it no longer applies. Send it again if you still need it.',
}

export default function AssistantPanel({ scope, chat, sections, target, setTarget, disabledReason, busy, onSend }) {
  const [message, setMessage] = useState('')
  const blocked = busy || !!disabledReason || (sections && !target)
  const send = () => { if (message.trim() && !blocked) { onSend(message.trim()); setMessage('') } }
  return <>
    <div className="scope">{scope}</div>
    <div className="chat" aria-live="polite">
      {!chat?.messages.length && <p className="empty">No messages yet. Type a change below. Every suggestion is shown in the section with additions highlighted and deletions struck through, for you to accept or reject.</p>}
      {chat?.messages.map(m => {
        const proposal = chat.proposals.find(p => p.message_id === m.id)
        return <div key={m.id} className="turn">
          <div className="msg me"><span className="who">You</span>{m.text}</div>
          {proposal && <div className="msg ai"><span className="who">Credit Assistant · mock mode</span>{REPLY[proposal.status] || proposal.status}
            {proposal.status === 'pending' && <span className="srcs">Your note is added as CA input and cited as such. It is not independently verified.</span>}</div>}
        </div>
      })}
    </div>
    <div className="composer">
      {sections && <label className="which">Which section is this about?<select value={target} onChange={e => setTarget(e.target.value)}>
        <option value="">Choose a section</option>{sections.map(s => <option key={s.section_id} value={s.section_id}>{s.section_id}. {s.name}</option>)}</select></label>}
      <div className="in"><textarea aria-label="Message to the Credit Assistant" rows={2} value={message} disabled={busy || !!disabledReason} maxLength={10000}
        placeholder={disabledReason || 'Type a change or a fact to add'} onChange={e => setMessage(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
        <button className="btn small primary" disabled={blocked || !message.trim()} onClick={send}>Send</button></div>
      <small>Mock mode: the assistant adds what you type to the section as cited CA input, without figures. Rewording and answering questions need the live model, which is not switched on yet.</small>
    </div>
  </>
}

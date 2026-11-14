const tones = {
  Provided: 'good', 'Found publicly': 'public', 'Can generate': 'neutral', Missing: 'attention',
  Suggested: 'neutral', 'Not applicable': 'quiet', Dismissed: 'quiet',
  'Can draft (full)': 'good', 'Can draft (partial)': 'public', 'Waiting for input': 'quiet',
  Drafted: 'public', Stale: 'attention', 'CA confirmed': 'good',
}
export default function Badge({ children }) {
  return <span className={`badge ${tones[children] || 'neutral'}`}>{children}</span>
}

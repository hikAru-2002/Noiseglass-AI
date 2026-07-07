function timeAgo(isoString) {
  const then = new Date(isoString)
  const now = new Date()
  const days = Math.floor((now - then) / (1000 * 60 * 60 * 24))
  if (days <= 0) return 'today'
  if (days === 1) return '1d ago'
  if (days < 7) return `${days}d ago`
  const weeks = Math.floor(days / 7)
  return `${weeks}w ago`
}

export default function IncomingStream({ fragments, loading, onSelect, searching }) {
  const sorted = [...fragments].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  )
  return (
    <div className={`stream-list ${loading ? 'stream-list-resolving' : ''}`}>
      {sorted.map((f) => (
        <div className="stream-item" key={f.id} onClick={() => onSelect(f)}>
          <div className="stream-item-top">
            <span className="channel-tag mono">{f.channel}</span>
            <span className="stream-item-time mono">{timeAgo(f.created_at)}</span>
          </div>
          <div className="stream-item-subject">{f.subject}</div>
          <div className="stream-item-meta">
            {f.customer_name} · {f.company}
          </div>
        </div>
      ))}
      {sorted.length === 0 && (
        <div className="stream-empty">
          {searching
            ? 'No fragments match your search.'
            : 'No fragments yet. Load a source to get started.'}
        </div>
      )}
    </div>
  )
}

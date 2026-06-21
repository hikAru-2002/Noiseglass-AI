const CHANNEL_LABEL = { email: 'EMAIL', chat: 'CHAT', 'in-app': 'IN-APP' }

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

export default function IncomingStream({ tickets, loading }) {
  const sorted = [...tickets].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  )

  return (
    <div className={`stream-list ${loading ? 'stream-list-resolving' : ''}`}>
      {sorted.map((t) => (
        <div className="stream-item" key={t.id}>
          <div className="stream-item-top">
            <span className={`channel-tag channel-${t.channel}`}>
              {CHANNEL_LABEL[t.channel] || t.channel}
            </span>
            <span className="stream-item-time mono">{timeAgo(t.created_at)}</span>
          </div>
          <div className="stream-item-subject">{t.subject}</div>
          <div className="stream-item-meta">
            {t.customer_name} · {t.company}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function FragmentDetailPanel({ fragment, onClose }) {
  if (!fragment) return null

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="detail-panel-header">
          <span className="mono detail-panel-id">{fragment.id}</span>
          <button className="detail-panel-close" onClick={onClose}>Esc</button>
        </div>
        <div className="detail-panel-channel mono">{fragment.channel}</div>
        <h2 className="detail-panel-subject">{fragment.subject}</h2>
        <div className="detail-panel-meta">
          {fragment.customer_name} · {fragment.company}
        </div>
        <p className="detail-panel-body">{fragment.body}</p>
      </div>
    </div>
  )
}

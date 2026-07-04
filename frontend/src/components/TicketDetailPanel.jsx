export default function TicketDetailPanel({ ticket, onClose }) {
  if (!ticket) return null

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="detail-panel-header">
          <span className="mono detail-panel-id">{ticket.id}</span>
          <button className="detail-panel-close" onClick={onClose}>Esc</button>
        </div>
        <div className="detail-panel-channel mono">{ticket.channel}</div>
        <h2 className="detail-panel-subject">{ticket.subject}</h2>
        <div className="detail-panel-meta">
          {ticket.customer_name} · {ticket.company}
        </div>
        <p className="detail-panel-body">{ticket.body}</p>
      </div>
    </div>
  )
}

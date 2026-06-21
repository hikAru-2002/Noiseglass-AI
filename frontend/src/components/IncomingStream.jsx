import './IncomingStream.css'

export default function IncomingStream({ tickets }) {
  return (
    <div className="incoming-stream">
      {tickets.map((ticket, idx) => (
        <div key={idx} className="ticket">
          <div className="ticket-id">{ticket.id}</div>
          <div className="ticket-text">{ticket.description}</div>
          <div className="ticket-meta">
            <span className="customer">{ticket.customer}</span>
            <span className="severity" data-severity={ticket.severity}>
              {ticket.severity}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}


import { useState } from 'react'
import './SignalCard.css'

export default function SignalCard({ signal }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="signal-card">
      <div className="signal-header" onClick={() => setExpanded(!expanded)}>
        <div className="signal-title">
          <h3>{signal.headline}</h3>
          <span className={`severity ${signal.severity}`}>{signal.severity}</span>
        </div>
        <div className="signal-meta">
          <span className="count">{signal.count} tickets</span>
          <span className={`trend ${signal.trend}`}>
            {signal.trend === 'increasing' && '↑'}
            {signal.trend === 'decreasing' && '↓'}
            {signal.trend === 'stable' && '→'}
            {' ' + signal.trend}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="signal-details">
          <div className="action">
            <strong>Suggested action:</strong>
            <p>{signal.action}</p>
          </div>

          <div className="samples">
            <strong>Sample tickets:</strong>
            <ul>
              {signal.samples.map((sample, idx) => (
                <li key={idx}>{sample.normalized || sample.description}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}


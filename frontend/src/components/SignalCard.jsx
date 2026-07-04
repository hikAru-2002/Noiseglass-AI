const FALLBACK_LABEL = { high: 'HIGH', medium: 'MODERATE', low: 'LOW' }

function TrendBadge({ pct }) {
  if (pct === undefined || pct === null) return null
  const rising = pct > 0
  const flat = pct === 0
  return (
    <span className="trend-badge mono">
      {rising ? '+' : flat ? '' : '-'}{Math.abs(pct).toFixed(0)}%
    </span>
  )
}

function categoryToTitle(slug) {
  return slug
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ')
}

export default function SignalCard({ cluster, expanded, onToggle }) {
  if (!cluster) return null

  return (
    <div className={`signal-card ${expanded ? 'signal-card-expanded' : ''}`}>
      <button className="signal-card-header" onClick={onToggle}>
        <div className="signal-card-header-top">
          <span
            className={`signal-card-severity mono severity-${
              cluster.rank?.tier || cluster.severity || 'low'
            }`}
          >
            <span className="severity-dot" />
            {cluster.rank?.label || FALLBACK_LABEL[cluster.severity] || 'LOW'}
          </span>
          <span className="ticket-count mono">{cluster.total_tickets}</span>
        </div>
        <div className="signal-card-category">{categoryToTitle(cluster.category)}</div>
        <p className="signal-headline">{cluster.headline}</p>
        <div className="signal-card-header-bottom">
          <TrendBadge pct={cluster.trend_pct_vs_last_week} />
          <span className="chevron">{expanded ? '−' : '+'}</span>
        </div>
      </button>
      {expanded && (
        <div className="signal-card-detail">
          <div className="detail-row">
            <span className="detail-label">Suggested action</span>
            <p className="detail-action">{cluster.suggested_action}</p>
          </div>
          <div className="detail-row">
            <span className="detail-label">Volume, this week to 3 weeks ago</span>
            <div className="sparkbar-row">
              {cluster.week_counts.slice().reverse().map((count, i) => (
                <div className="sparkbar-col" key={i}>
                  <div
                    className="sparkbar-fill"
                    style={{ height: `${Math.max(count * 14, 4)}px` }}
                  />
                  <span className="sparkbar-count mono">{count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="detail-row">
            <span className="detail-label">Sample tickets</span>
            <ul className="sample-ticket-list">
              {cluster.sample_tickets?.map((t) => (
                <li key={t.id}>
                  <span className="mono sample-ticket-id">{t.id}</span> {t.normalized_issue}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
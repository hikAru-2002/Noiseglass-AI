import { useState } from 'react'

const FALLBACK_LABEL = { high: 'HIGH', medium: 'MODERATE', low: 'LOW' }

// Percentages mislead at low volume (+100% can mean 0 -> 1 fragment), so the
// badge shows the actual week-over-week movement in plain numbers.
function TrendBadge({ weekCounts }) {
  if (!weekCounts?.length) return null
  const [thisWk, lastWk] = weekCounts
  if (lastWk === 0 && thisWk > 0) {
    return (
      <span className="trend-badge trend-badge-new mono">
        new · {thisWk} this wk
      </span>
    )
  }
  if (thisWk === 0 && lastWk === 0) {
    return <span className="trend-badge mono">quiet · older reports</span>
  }
  if (thisWk > lastWk) {
    return (
      <span className="trend-badge trend-badge-up mono">
        ▲ {lastWk} → {thisWk} wk/wk
      </span>
    )
  }
  if (thisWk < lastWk) {
    return (
      <span className="trend-badge trend-badge-down mono">
        ▼ {lastWk} → {thisWk} wk/wk
      </span>
    )
  }
  return <span className="trend-badge mono">= steady at {thisWk}/wk</span>
}

function categoryToTitle(slug) {
  return slug
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ')
}

const WEEK_LABELS = ['3w ago', '2w ago', 'last wk', 'this wk']

// SVG area chart for the 4-week volume window. Oldest week on the left.
// Color tells the story at a glance: heating up = red, cooling off = green.
function TrendChart({ weekCounts }) {
  const [hovered, setHovered] = useState(null)

  // week_counts arrives newest-first; flip to chronological order
  const counts = weekCounts.slice().reverse()
  const thisWeek = counts[3]
  const lastWeek = counts[2]
  const direction = thisWeek > lastWeek ? 'rising' : thisWeek < lastWeek ? 'falling' : 'flat'
  const color =
    direction === 'rising' ? '#ff6b61' : direction === 'falling' ? '#7dd487' : '#a1a1a7'

  const W = 280
  const H = 72
  const PAD_X = 10
  const PAD_TOP = 12
  const PAD_BOTTOM = 8
  const max = Math.max(...counts, 1)

  const pts = counts.map((c, i) => ({
    x: PAD_X + (i * (W - PAD_X * 2)) / (counts.length - 1),
    y: PAD_TOP + (1 - c / max) * (H - PAD_TOP - PAD_BOTTOM),
    count: c,
  }))

  // smooth cubic path through the points
  let line = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1]
    const curr = pts[i]
    const cx = (prev.x + curr.x) / 2
    line += ` C ${cx} ${prev.y}, ${cx} ${curr.y}, ${curr.x} ${curr.y}`
  }
  const area = `${line} L ${pts[3].x} ${H} L ${pts[0].x} ${H} Z`

  return (
    <div className="trend-chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="trend-chart-svg"
        onMouseLeave={() => setHovered(null)}
      >
        <defs>
          <linearGradient id={`trend-fill-${color.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.22" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        <path d={area} fill={`url(#trend-fill-${color.slice(1)})`} />
        <path
          d={line}
          fill="none"
          stroke={color}
          strokeWidth="1.6"
          strokeLinecap="round"
          className="trend-chart-line"
        />

        {pts.map((p, i) => (
          <g key={i}>
            {/* generous invisible hit area per point */}
            <rect
              x={p.x - (W - PAD_X * 2) / 6 / 2 - 12}
              y="0"
              width={(W - PAD_X * 2) / 3}
              height={H}
              fill="transparent"
              onMouseEnter={() => setHovered(i)}
            />
            {hovered === i && (
              <line
                x1={p.x} y1={PAD_TOP - 6} x2={p.x} y2={H}
                stroke={color} strokeOpacity="0.25" strokeWidth="1"
              />
            )}
            <circle
              cx={p.x}
              cy={p.y}
              r={hovered === i ? 4 : i === 3 ? 3 : 2.2}
              fill={hovered === i || i === 3 ? color : 'var(--surface-3)'}
              stroke={color}
              strokeWidth="1.2"
              className="trend-chart-dot"
            />
          </g>
        ))}
      </svg>

      <div className="trend-chart-labels">
        {WEEK_LABELS.map((label, i) => (
          <span
            key={label}
            className={`trend-chart-label mono ${hovered === i ? 'trend-chart-label-active' : ''} ${
              i === 3 && hovered === null ? 'trend-chart-label-now' : ''
            }`}
          >
            {hovered === i ? `${pts[i].count} ${pts[i].count === 1 ? 'fragment' : 'fragments'}` : label}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function SignalCard({ cluster, expanded, onToggle, onSelectFragment }) {
  if (!cluster) return null

  return (
    <div className={`signal-card ${expanded ? 'signal-card-expanded' : ''}`}>
      <button className="signal-card-header" onClick={onToggle}>
        <div className="signal-card-header-top">
          <span
            className={`severity-badge mono severity-${
              cluster.rank?.tier || cluster.severity || 'low'
            }`}
          >
            {cluster.rank?.label || FALLBACK_LABEL[cluster.severity] || 'LOW'}
          </span>
          <span className="fragment-count mono">
            {cluster.total_fragments}
            <span className="fragment-count-unit">
              {cluster.total_fragments === 1 ? ' fragment' : ' fragments'}
            </span>
          </span>
        </div>
        <div className="signal-card-category">{categoryToTitle(cluster.category)}</div>
        <p className="signal-headline">{cluster.headline}</p>
        <div className="signal-card-header-bottom">
          <TrendBadge weekCounts={cluster.week_counts} />
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
            <span className="detail-label">4-week volume</span>
            <TrendChart weekCounts={cluster.week_counts} />
          </div>
          <div className="detail-row">
            <span className="detail-label">Sample fragments</span>
            <ul className="sample-fragment-list">
              {cluster.sample_fragments?.map((f) => (
                <li key={f.id}>
                  <button
                    className="sample-fragment-btn"
                    onClick={() => onSelectFragment?.(f)}
                    title="View full fragment"
                  >
                    <span className="mono sample-fragment-id">{f.id}</span>
                    <span className="sample-fragment-text">{f.normalized_issue}</span>
                    <span className="sample-fragment-arrow mono">→</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

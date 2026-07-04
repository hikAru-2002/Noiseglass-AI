import { useEffect, useState } from 'react'

function formatRunDate(iso) {
  if (!iso) return '?'
  const d = new Date(iso)
  const now = new Date()
  const sameYear = d.getFullYear() === now.getFullYear()
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: '2-digit' }),
  })
}

export default function RunHistory({ apiBase, refreshToken }) {
  const [runs, setRuns] = useState([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await fetch(`${apiBase}/api/runs?limit=14`)
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled) setRuns(data.runs || [])
      } catch {
        // history is a nice-to-have, fail silently
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [apiBase, refreshToken])

  if (runs.length === 0) return null

  return (
    <div className="run-history">
      <span className="run-history-label mono">Run history</span>
      <div className="run-history-strip">
        {runs.map((r) => (
          <div className="run-chip" key={r.id} title={r.generated_at}>
            <span className="run-chip-date mono">{formatRunDate(r.generated_at)}</span>
            <span className="run-chip-stats mono">
              {r.total_tickets_analyzed} tix · {r.cluster_count} signals
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

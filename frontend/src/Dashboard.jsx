import { useEffect, useState, useMemo } from 'react'
import './App.css'
import SignalCard from './components/SignalCard.jsx'
import IncomingStream from './components/IncomingStream.jsx'
import EmptyState from './components/EmptyState.jsx'
import GithubSourcePicker from './components/GithubSourcePicker.jsx'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Dashboard() {
  const [tickets, setTickets] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedCategory, setExpandedCategory] = useState(null)

  useEffect(() => {
    fetchTickets()
    fetchCachedAnalysis()
  }, [])

  async function fetchTickets() {
    try {
      const res = await fetch(`${API_BASE}/api/tickets`)
      const data = await res.json()
      setTickets(data)
    } catch (e) {
      setError('Could not reach the backend. Is it running?')
    }
  }

  function handleGithubLoaded(data) {
    setAnalysis(null)
    fetchTickets()
  }

  async function fetchCachedAnalysis() {
    try {
      const res = await fetch(`${API_BASE}/api/analysis`)
      const data = await res.json()
      if (data.cached) setAnalysis(data)
    } catch (e) {
      // silent, not critical, user can run analysis manually
    }
  }

  async function runAnalysis() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, { method: 'POST' })
      if (!res.ok) {
        const errBody = await res.json()
        throw new Error(errBody.detail || 'Analysis failed')
      }
      const data = await res.json()
      setAnalysis(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const noiseCount = analysis?.noise_filtered_count ?? null
  const totalCount = analysis?.total_tickets_analyzed ?? tickets.length

  const sortedClusters = useMemo(() => {
    if (!analysis?.actionable_clusters) return []
    const severityRank = { high: 0, medium: 1, low: 2 }
    return [...analysis.actionable_clusters].sort((a, b) => {
      const sa = severityRank[a.severity] ?? 3
      const sb = severityRank[b.severity] ?? 3
      if (sa !== sb) return sa - sb
      return b.total_tickets - a.total_tickets
    })
  }, [analysis])

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-left">
          <div className="wordmark-mark" />
          <span className="wordmark-text">Signal</span>
          <span className="topbar-sub">support trend intelligence</span>
        </div>
        <div className="topbar-right">
          <GithubSourcePicker apiBase={API_BASE} onLoaded={handleGithubLoaded} />
          <button
            className="run-btn"
            onClick={runAnalysis}
            disabled={loading || tickets.length === 0}
          >
            {loading ? 'Resolving signal...' : analysis ? 'Re-run analysis' : 'Run analysis'}
          </button>
        </div>
      </header>

      <div className="stats-row">
        <div className="stat">
          <span className="stat-value">{totalCount}</span>
          <span className="stat-label">tickets pulled</span>
        </div>
        <div className="stat-divider" />
        <div className="stat">
          <span className="stat-value">{sortedClusters.length}</span>
          <span className="stat-label">clustered signals</span>
        </div>
        <div className="stat-divider" />
        <div className="stat">
          <span className="stat-value">{noiseCount ?? '—'}</span>
          <span className="stat-label">filtered as noise</span>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <main className="main-grid">
        <section className="stream-panel">
          <div className="panel-label">
            <span className="eyebrow">Incoming</span>
            <span className="panel-label-sub">raw tickets, unsorted</span>
          </div>
          <IncomingStream tickets={tickets} loading={loading} />
        </section>

        <section className="signal-panel">
          <div className="panel-label">
            <span className="eyebrow">Signal</span>
            <span className="panel-label-sub">
              {analysis
                ? `${sortedClusters.length} issues worth a product team's attention`
                : 'run analysis to resolve noise into signal'}
            </span>
          </div>

          {!analysis && !loading && (
            <EmptyState onRun={runAnalysis} disabled={tickets.length === 0} />
          )}

          {loading && (
            <div className="loading-state">
              <div className="loading-pulse" />
              <p>Reading {tickets.length} tickets, clustering by underlying issue, and writing the brief...</p>
            </div>
          )}

          {!loading && analysis && (
            <div className="signal-stack">
              {sortedClusters.map((c) => (
                <SignalCard
                  key={c.category}
                  cluster={c}
                  expanded={expandedCategory === c.category}
                  onToggle={() =>
                    setExpandedCategory(
                      expandedCategory === c.category ? null : c.category
                    )
                  }
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
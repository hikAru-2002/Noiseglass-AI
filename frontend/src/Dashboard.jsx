import { useEffect, useState, useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import './App.css'
import SignalCard from './components/SignalCard.jsx'
import IncomingStream from './components/IncomingStream.jsx'
import EmptyState from './components/EmptyState.jsx'
import GithubSourcePicker from './components/GithubSourcePicker.jsx'
import TicketDetailPanel from './components/TicketDetailPanel.jsx'
import AnalysisLoader from './components/AnalysisLoader.jsx'
import AmbientField from './components/AmbientField.jsx'
import RunHistory from './components/RunHistory.jsx'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Derive a 4-tier rank from severity, trend momentum, and volume.
// SEVERE = high severity that is also spiking; LOW = quiet and flat.
function rankCluster(c) {
  const base = { high: 3, medium: 2, low: 1 }[c.severity] ?? 1
  const trend = c.trend_pct_vs_last_week ?? 0
  const vol = c.total_tickets ?? 0
  let score = base
  if (trend >= 100) score += 1.5
  else if (trend > 0) score += 0.75
  if (vol >= 6) score += 1
  else if (vol >= 3) score += 0.5
  if (score >= 4.25) return { tier: 'severe', label: 'SEVERE', score }
  if (score >= 3) return { tier: 'high', label: 'HIGH', score }
  if (score >= 2) return { tier: 'moderate', label: 'MODERATE', score }
  return { tier: 'low', label: 'LOW', score }
}

export default function Dashboard() {
  const [tickets, setTickets] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedCategory, setExpandedCategory] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTicket, setSelectedTicket] = useState(null)
  const searchInputRef = useRef(null)

  useEffect(() => {
    fetchTickets()
    fetchCachedAnalysis()
  }, [])

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === '/') {
        const tag = e.target.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) return
        e.preventDefault()
        searchInputRef.current?.focus()
      } else if (e.key === 'Escape') {
        setSelectedTicket((prev) => {
          if (prev) return null
          // no panel open: blur search instead
          if (document.activeElement === searchInputRef.current) {
            searchInputRef.current.blur()
          }
          return prev
        })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
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
    return analysis.actionable_clusters
      .map((c) => ({ ...c, rank: rankCluster(c) }))
      .sort((a, b) => {
        if (b.rank.score !== a.rank.score) return b.rank.score - a.rank.score
        return b.total_tickets - a.total_tickets
      })
  }, [analysis])

  // most common company across tickets = the source being analyzed
  const sourceLabel = useMemo(() => {
    if (!tickets.length) return null
    const counts = {}
    for (const t of tickets) {
      if (t.company) counts[t.company] = (counts[t.company] || 0) + 1
    }
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
    return top ? top[0] : null
  }, [tickets])

  const filteredTickets = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return tickets
    return tickets.filter((t) =>
      [t.subject, t.body, t.customer_name, t.company, t.channel, String(t.id)]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(q))
    )
  }, [tickets, searchQuery])

  return (
    <div className="app">
      <AmbientField />
      <header className="topbar">
        <div className="topbar-left">
          <Link to="/" className="back-link mono" title="Back to homepage">
            ←
          </Link>
          <div className="wordmark-mark" />
          <span className="wordmark-text">Noiseglass</span>
          <span className="topbar-sub">Support Trend Intelligence</span>
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
          <span className="stat-value">{noiseCount ?? '-'}</span>
          <span className="stat-label">filtered as noise</span>
        </div>
      </div>

      <RunHistory apiBase={API_BASE} refreshToken={analysis?.generated_at} />

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
          <div className="stream-search">
            <input
              ref={searchInputRef}
              className="stream-search-input mono"
              type="text"
              placeholder="Search tickets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <span className="stream-search-hint mono">/</span>
          </div>
          <IncomingStream
            tickets={filteredTickets}
            loading={loading}
            onSelect={setSelectedTicket}
            searching={searchQuery.trim().length > 0}
          />
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
            <AnalysisLoader
              ticketCount={tickets.length}
              sourceName={sourceLabel}
            />
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

      <footer className="footer">
        <span className="footer-brand mono">NOISEGLASS © 2026</span>
        <span className="footer-sub">
          real tickets · real trend math · written by Claude
        </span>
      </footer>

      <TicketDetailPanel
        ticket={selectedTicket}
        onClose={() => setSelectedTicket(null)}
      />
    </div>
  )
}
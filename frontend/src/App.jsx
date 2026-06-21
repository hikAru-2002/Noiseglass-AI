import { useState, useEffect } from 'react'
import IncomingStream from './components/IncomingStream'
import SignalCard from './components/SignalCard'
import EmptyState from './components/EmptyState'
import './App.css'

function App() {
  const [tickets, setTickets] = useState([])
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(false)
  const [analyzed, setAnalyzed] = useState(false)

  useEffect(() => {
    // Load initial tickets
    fetch('/api/tickets')
      .then(r => r.json())
      .then(data => setTickets(data.tickets || []))
      .catch(err => console.error('Failed to load tickets:', err))
  }, [])

  const handleAnalyze = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/analyze', { method: 'POST' })
      const data = await response.json()
      setSignals(data.signals || [])
      setAnalyzed(true)
    } catch (err) {
      console.error('Analysis failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerate = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/regenerate-tickets', { method: 'POST' })
      const data = await response.json()
      setTickets(data.tickets || [])
      setSignals([])
      setAnalyzed(false)
    } catch (err) {
      console.error('Regeneration failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Signal</h1>
        <p>Support Trend Intelligence for Flowline</p>
      </header>

      <div className="container">
        <div className="panel incoming">
          <div className="panel-header">
            <h2>Incoming Stream</h2>
            <span className="count">{tickets.length} tickets</span>
          </div>
          {tickets.length > 0 ? (
            <IncomingStream tickets={tickets} />
          ) : (
            <EmptyState message="Loading tickets..." />
          )}
        </div>

        <div className="divider"></div>

        <div className="panel signals">
          <div className="panel-header">
            <h2>Signals</h2>
            <button
              onClick={handleAnalyze}
              disabled={loading || tickets.length === 0}
              className="btn-primary"
            >
              {loading ? 'Analyzing...' : analyzed ? 'Re-run analysis' : 'Run analysis'}
            </button>
          </div>

          {signals.length > 0 ? (
            <div className="signals-list">
              {signals.map((signal, idx) => (
                <SignalCard key={idx} signal={signal} />
              ))}
            </div>
          ) : analyzed ? (
            <EmptyState message="No significant signals found." />
          ) : (
            <EmptyState message="Click 'Run analysis' to generate signals." />
          )}

          <button
            onClick={handleRegenerate}
            disabled={loading}
            className="btn-secondary"
          >
            {loading ? 'Regenerating...' : 'Regenerate tickets'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default App


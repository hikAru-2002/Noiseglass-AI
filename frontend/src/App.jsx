async function fetchTickets() {
  try {
    const res = await fetch(`${API_BASE}/api/tickets`)
    const data = await res.json()
    setTickets(data)
  } catch (e) {
    setError('Could not reach the backend. Is it running on port 8000?')
  }
}

async function fetchCachedAnalysis() {
  try {
    const res = await fetch(`${API_BASE}/api/analysis`)
    const data = await res.json()
    if (data.cached) setAnalysis(data)
  } catch (e) {
    // silent — not critical, user can run analysis manually
  }
}

async function runAnalysis() {
  setLoading(true)
  setError(null)
  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
    })

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
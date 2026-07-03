import { useState } from 'react'

export default function GithubSourcePicker({ apiBase, onLoaded }) {
  const [owner, setOwner] = useState('n8n-io')
  const [repo, setRepo] = useState('n8n')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [open, setOpen] = useState(false)

  async function handleFetch() {
    setLoading(true)
    setError(null)
    try {
      const body = new URLSearchParams({ owner, repo, limit: '50' })
      const res = await fetch(`${apiBase}/api/fetch-github-issues`, {
        method: 'POST',
        body,
      })
      if (!res.ok) {
        const errBody = await res.json()
        throw new Error(errBody.detail || 'Failed to fetch issues')
      }
      const data = await res.json()
      onLoaded(data)
      setOpen(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="github-picker">
      <button className="github-picker-toggle" onClick={() => setOpen(!open)}>
        Load from GitHub
      </button>

      {open && (
        <div className="github-picker-panel">
          <input
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            placeholder="owner"
          />
          <input
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="repo"
          />
          <button onClick={handleFetch} disabled={loading}>
            {loading ? 'Fetching...' : 'Fetch issues'}
          </button>
          {error && <div className="github-picker-error">{error}</div>}
        </div>
      )}
    </div>
  )
}
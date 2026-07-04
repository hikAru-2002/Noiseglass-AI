import { useState } from 'react'

const SOURCES = ['github', 'app store', 'zendesk']

export default function GithubSourcePicker({ apiBase, onLoaded }) {
  const [open, setOpen] = useState(false)
  const [source, setSource] = useState('github')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // github fields
  const [owner, setOwner] = useState('n8n-io')
  const [repo, setRepo] = useState('n8n')

  // zendesk fields
  const [subdomain, setSubdomain] = useState('')
  const [email, setEmail] = useState('')
  const [apiToken, setApiToken] = useState('')

  // app store fields
  const [appTerm, setAppTerm] = useState('')

  async function handleFetch() {
    setLoading(true)
    setError(null)
    try {
      let endpoint, body
      if (source === 'github') {
        endpoint = '/api/fetch-github-issues'
        body = new URLSearchParams({ owner, repo, limit: '100' })
      } else if (source === 'app store') {
        endpoint = '/api/fetch-appstore-reviews'
        body = new URLSearchParams({ app_term: appTerm, limit: '100' })
      } else {
        endpoint = '/api/fetch-zendesk-tickets'
        body = new URLSearchParams({
          subdomain,
          email,
          api_token: apiToken,
          limit: '100',
        })
      }
      const res = await fetch(`${apiBase}${endpoint}`, {
        method: 'POST',
        body,
      })
      if (!res.ok) {
        const errBody = await res.json()
        throw new Error(errBody.detail || 'Failed to fetch tickets')
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
        Load tickets
      </button>

      {open && (
        <div className="github-picker-panel">
          <div className="source-tabs">
            {SOURCES.map((s) => (
              <button
                key={s}
                className={`source-tab mono ${source === s ? 'source-tab-active' : ''}`}
                onClick={() => {
                  setSource(s)
                  setError(null)
                }}
              >
                {s}
              </button>
            ))}
          </div>

          {source === 'github' && (
            <div className="github-picker-fields mono">
              <input
                className="github-picker-input"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                placeholder="owner"
                spellCheck={false}
              />
              <span className="github-picker-slash">/</span>
              <input
                className="github-picker-input"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                placeholder="repo"
                spellCheck={false}
              />
            </div>
          )}

          {source === 'app store' && (
            <div className="zendesk-fields">
              <input
                className="github-picker-input mono"
                value={appTerm}
                onChange={(e) => setAppTerm(e.target.value)}
                placeholder="app name, e.g. spotify"
                spellCheck={false}
              />
              <span className="zendesk-note">
                public reviews via Apple's RSS feed, no auth needed
              </span>
            </div>
          )}

          {source === 'zendesk' && (
            <div className="zendesk-fields">
              <div className="github-picker-fields mono">
                <input
                  className="github-picker-input"
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value)}
                  placeholder="subdomain"
                  spellCheck={false}
                />
                <span className="github-picker-slash">.zendesk.com</span>
              </div>
              <input
                className="github-picker-input mono"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="agent email"
                spellCheck={false}
              />
              <input
                className="github-picker-input mono"
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder="api token"
                spellCheck={false}
              />
              <span className="zendesk-note">
                token stays on your backend, never stored
              </span>
            </div>
          )}

          <button
            className="github-picker-fetch"
            onClick={handleFetch}
            disabled={loading}
          >
            {loading ? 'Fetching...' : 'Fetch tickets'}
          </button>
          {error && <div className="github-picker-error">{error}</div>}
        </div>
      )}
    </div>
  )
}

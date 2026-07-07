import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '../api.js'

const SOURCES = ['upload', 'github']

export default function GithubSourcePicker({ apiBase, onLoaded, inline = false }) {
  const [open, setOpen] = useState(false)
  const [source, setSource] = useState('upload')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // upload fields
  const [file, setFile] = useState(null)
  const [pasteText, setPasteText] = useState('')
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef(null)
  const containerRef = useRef(null)

  // dismiss the dropdown when clicking anywhere outside it, or pressing Esc
  useEffect(() => {
    if (!open || inline) return
    function onMouseDown(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    function onKeyDown(e) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open, inline])

  // github fields
  const [owner, setOwner] = useState('n8n-io')
  const [repo, setRepo] = useState('n8n')

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) {
      setFile(dropped)
      setError(null)
    }
  }

  async function handleFetch() {
    setLoading(true)
    setError(null)
    try {
      let res
      if (source === 'upload') {
        if (file) {
          const form = new FormData()
          form.append('file', file)
          res = await apiFetch(apiBase, '/api/upload-csv', { method: 'POST', body: form })
        } else if (pasteText.trim()) {
          res = await apiFetch(apiBase, '/api/upload-text', {
            method: 'POST',
            body: new URLSearchParams({ text: pasteText }),
          })
        } else {
          throw new Error('Drop a CSV export or paste some text first.')
        }
      } else {
        const endpoint = '/api/fetch-github-issues'
        const body = new URLSearchParams({ owner, repo, limit: '100' })
        res = await apiFetch(apiBase, endpoint, { method: 'POST', body })
      }
      if (!res.ok) {
        const errBody = await res.json()
        throw new Error(errBody.detail || 'Failed to load fragments')
      }
      const data = await res.json()
      setFile(null)
      setPasteText('')
      onLoaded(data)
      setOpen(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function loadDemoData() {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch(apiBase, '/api/regenerate-fragments', { method: 'POST' })
      if (!res.ok) throw new Error('Failed to load demo data')
      onLoaded(await res.json())
      setOpen(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const panel = (
    <div className={inline ? 'github-picker-panel github-picker-panel-inline' : 'github-picker-panel'}>
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

          {source === 'upload' && (
            <div className="source-fields">
              <div
                className={`upload-dropzone ${dragging ? 'upload-dropzone-active' : ''} ${file ? 'upload-dropzone-filled' : ''}`}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
              >
                {file ? (
                  <>
                    <span className="upload-dropzone-file mono">{file.name}</span>
                    <span className="upload-dropzone-hint">click to choose a different file</span>
                  </>
                ) : (
                  <>
                    <span className="upload-dropzone-label">Drop a CSV export here</span>
                    <span className="upload-dropzone-hint">
                      works with exports from Zendesk, Intercom, Jira, or any ticketing tool
                    </span>
                  </>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv,text/plain"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null)
                    setError(null)
                  }}
                />
              </div>
              <div className="upload-divider mono">or paste raw text</div>
              <textarea
                className="upload-paste mono"
                rows={3}
                placeholder="One fragment per line..."
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
              />
            </div>
          )}

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

          <button
            className="github-picker-fetch"
            onClick={handleFetch}
            disabled={loading}
          >
            {loading ? 'Loading...' : source === 'upload' ? 'Analyze my data' : 'Fetch issues'}
          </button>
          {error && <div className="github-picker-error">{error}</div>}
          <button className="demo-data-link mono" onClick={loadDemoData} disabled={loading}>
            ...or explore with demo data
          </button>
        </div>
  )

  if (inline) return panel

  return (
    <div className="github-picker" ref={containerRef}>
      <button className="github-picker-toggle" onClick={() => setOpen(!open)}>
        Load data
      </button>
      {open && panel}
    </div>
  )
}

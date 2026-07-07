// Per-browser workspace identity. Every API call carries this ID so the
// backend can keep each visitor's fragments, analyses, and history isolated.

const WORKSPACE_KEY = 'noiseglass-workspace-id'

export function workspaceId() {
  let id = localStorage.getItem(WORKSPACE_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(WORKSPACE_KEY, id)
  }
  return id
}

export function apiFetch(base, path, options = {}) {
  return fetch(`${base}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-Workspace-Id': workspaceId(),
    },
  })
}

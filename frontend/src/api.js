const BASE = '/api'

async function http(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include'
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json()
}

export const conversations = {
  getById(id) { return http('GET', `/conversations/${id}`) },
  getMessages(id) { return http('GET', `/conversations/${id}/messages`) },
  sendMessage(id, content) { return http('POST', `/conversations/${id}/messages`, { content }) }
}

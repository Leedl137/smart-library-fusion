const API_BASE = import.meta.env.VITE_SMARTLIB_API_BASE || ''

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  })

  const text = await response.text()
  const payload = text ? JSON.parse(text) : {}

  if (!response.ok || (payload.code && payload.code !== 200)) {
    const message = payload.message || `数据请求失败：${response.status}`
    const error = new Error(message)
    error.payload = payload
    throw error
  }

  return payload
}

export function getDashboardOverview() {
  return request('/api/v2/dashboard/overview')
}

export function getDashboardExtra() {
  return request('/api/v2/dashboard/extra')
}

export function getAdvancedQueries() {
  return request('/api/v2/advanced/queries')
}

export function getAdvancedSkill() {
  return request('/api/v2/advanced/skill')
}

export function getAiConfigStatus() {
  return request('/api/v2/ai/config/status')
}

export function saveAiConfig(config) {
  return request('/api/v2/ai/config', {
    method: 'POST',
    body: JSON.stringify(config)
  })
}

export function testAiConfig(config) {
  return request('/api/v2/ai/config/test', {
    method: 'POST',
    body: JSON.stringify(config)
  })
}

export function askNl2Sql(payload) {
  return request('/api/v2/nl2sql/query', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export { API_BASE }

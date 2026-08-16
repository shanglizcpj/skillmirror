import http from './http'

export function logAction(data) {
  return http.post('/actions/log', data)
}

export function getSessionActions(
  sessionId
) {
  return http.get(
    `/sessions/${sessionId}/actions`
  )
}
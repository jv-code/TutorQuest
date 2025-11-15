const API_BASE = '/api'

export async function createSession(userId) {
  const response = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId })
  })
  return response.json()
}

export async function sendMessage(sessionId, content) {
  const response = await fetch(`${API_BASE}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, content })
  })
  return response.json()
}

export async function getMessages(sessionId) {
  const response = await fetch(`${API_BASE}/messages/${sessionId}`)
  return response.json()
}

export async function getNextQuestion(sessionId, difficulty = null) {
  const params = new URLSearchParams({ session_id: sessionId })
  if (difficulty !== null) {
    params.append('difficulty', difficulty)
  }
  const response = await fetch(`${API_BASE}/questions/next?${params}`)
  return response.json()
}

export async function validateAnswer(sessionId, questionId, answer) {
  const response = await fetch(`${API_BASE}/questions/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question_id: questionId, answer })
  })
  return response.json()
}

export async function getVideoStatus(videoId) {
  const response = await fetch(`${API_BASE}/videos/${videoId}/status`)
  return response.json()
}

export async function getVideo(videoId) {
  const response = await fetch(`${API_BASE}/videos/${videoId}`)
  return response.json()
}

export async function generateVideo(sessionId, questionId) {
  const response = await fetch(`${API_BASE}/videos/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question_id: questionId })
  })
  return response.json()
}

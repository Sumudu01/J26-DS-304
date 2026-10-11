import { API_URL } from '../App'

const getAuthHeaders = () => {
  const token = localStorage.getItem('emploeralk_token')
  if (!token) throw new Error('Your session has expired. Please sign in again.')
  return { Authorization: `Bearer ${token}` }
}

export const createNotification = async ({ type, title, body }) => {
  const response = await fetch(`${API_URL}/notifications`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ type, title, body }),
  })
  if (!response.ok) throw new Error(`Could not save notification (HTTP ${response.status})`)
  return response.json()
}

export { getAuthHeaders }

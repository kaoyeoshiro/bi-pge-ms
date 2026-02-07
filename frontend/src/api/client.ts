import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

export function buildQueryString(
  params: Record<string, string | string[] | number | undefined | null>
): string {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      value.forEach((v) => searchParams.append(key, v))
    } else {
      searchParams.set(key, String(value))
    }
  }

  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

export default api

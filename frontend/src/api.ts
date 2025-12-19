export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000/v1'

export type Json = any

export async function fetchJson<T = Json>(
  path: string,
  opts: RequestInit = {},
): Promise<{ data: T; headers: Headers; status: number }> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`

  const res = await fetch(url, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(opts.headers ?? {}),
    },
  })

  let data: any = null
  const contentType = res.headers.get('content-type') || ''
  try {
    if (contentType.includes('application/json')) {
      data = await res.json()
    } else {
      data = await res.text()
    }
  } catch {
    data = null
  }

  if (!res.ok) {
    const msg = typeof data === 'string' ? data : JSON.stringify(data)
    throw new Error(`HTTP ${res.status}: ${msg}`)
  }

  return { data: data as T, headers: res.headers, status: res.status }
}

export function buildQuery(params: Record<string, string | number | boolean | undefined | null>): string {
  const usp = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return
    usp.set(k, String(v))
  })
  const s = usp.toString()
  return s ? `?${s}` : ''
}

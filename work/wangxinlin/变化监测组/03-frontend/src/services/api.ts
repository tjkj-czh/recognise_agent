const API_BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`
  const token = localStorage.getItem('auth-storage')
    ? JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.token
    : null

  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Request failed' }))
    throw new Error(error.message || `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResponse {
  token: string
  user: {
    id: number
    username: string
    realName: string
    role: string
  }
}

export interface LandSupply {
  id: number
  resourceId: string
  transferNo: string
  district: string
  landUseType: string
  areaSqm: number
  areaMu: number
  plotRatio: number | null
  startingPrice: number | null
  transactionPrice: number | null
  transactionDate: string | null
  estimatedDate: string | null
  transactionStage: string
  systemType: string
  longitude: number
  latitude: number
  plotName: string
}

export const api = {
  login: (payload: LoginPayload) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  me: () =>
    request<LoginResponse['user']>('/auth/me'),

  getLandSupplies: (params?: { district?: string; page?: number; pageSize?: number }) => {
    const search = new URLSearchParams()
    if (params?.district) search.set('district', params.district)
    if (params?.page) search.set('page', String(params.page))
    if (params?.pageSize) search.set('pageSize', String(params.pageSize))
    return request<{ items: LandSupply[]; total: number }>(`/land-supplies?${search.toString()}`)
  },

  getLandSupply: (id: number) =>
    request<LandSupply>(`/land-supplies/${id}`),
}

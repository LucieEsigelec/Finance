// Seul module qui appelle l'API (UI §4.1). Son adresse vient de VITE_API_URL (.env.local).
// L'interface ne parle jamais directement à Supabase, yfinance ou NewsAPI.

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body, params } = {}) {
  const url = new URL(`${BASE_URL}${path}`)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
  })
  let response
  try {
    response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, "L'application ne parvient pas à joindre le serveur.")
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? 'Saisie invalide.' : data.detail
    throw new ApiError(response.status, detail || `Erreur ${response.status}`)
  }
  return data
}

export const api = {
  /** GET /api/dashboard — accueil, tableau de bord, en-tête du simulateur, alerte */
  dashboard: () => request('/api/dashboard'),
  /** POST /api/simulate — conseil sur une opération, rien n'est enregistré */
  simulate: (tickers, operation, montant) =>
    request('/api/simulate', { method: 'POST', body: { tickers, operation, montant_eur: montant } }),
  /** POST /api/transactions — enregistre une opération confirmée */
  recordTransaction: (payload) => request('/api/transactions', { method: 'POST', body: payload }),
  /** GET /api/stocks/{ticker} — fiche action, les deux onglets en un appel */
  stock: (ticker) => request(`/api/stocks/${encodeURIComponent(ticker)}`),
  /** GET /api/portfolio/history — journal, courbe et bilan */
  history: (params) => request('/api/portfolio/history', { params }),
  /** POST /api/market/refresh — actualise les données de marché */
  refresh: () => request('/api/market/refresh', { method: 'POST' }),
}

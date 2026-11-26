import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client'

// Données de GET /api/dashboard gardées pendant la session (UI §5.1) : la même réponse
// sert à l'accueil, au tableau de bord, au simulateur, à la NavBar et au bandeau d'alerte.
//
// Mise à jour automatique (D-13) :
// - si l'API annonce qu'elle a lancé une actualisation (données de plus d'une heure),
//   on suit son avancement puis on recharge ;
// - une page restée ouverte relit les données toutes les 5 minutes, et quand on revient
//   sur l'onglet après plus de 5 minutes.
const DashboardContext = createContext(null)
const RELECTURE_MS = 5 * 60 * 1000

/** Attend la fin de l'actualisation côté serveur (point toutes les 2 secondes, 5 minutes au plus). */
async function waitForRefresh() {
  for (let attempt = 0; attempt < 150; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000))
    const status = await api.refreshStatus()
    if (!status.en_cours) {
      if (status.erreur) throw new Error(`L'actualisation a échoué : ${status.erreur}`)
      return status.rapport
    }
  }
  throw new Error("L'actualisation prend plus de temps que prévu : réessayez dans quelques minutes.")
}

export function DashboardProvider({ children }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const following = useRef(false)
  const lastLoad = useRef(0)

  /** Range une réponse du tableau de bord ; si une actualisation tourne côté serveur,
   *  la suit puis relit. */
  const apply = useCallback(async (result) => {
    lastLoad.current = Date.now()
    setData(result)
    setError(null)
    if (result.actualisation?.en_cours && !following.current) {
      following.current = true
      setRefreshing(true)
      try {
        await waitForRefresh()
        setData(await api.dashboard())
        lastLoad.current = Date.now()
      } catch {
        // les données affichées restent valables ; l'erreur sera visible au prochain essai
      } finally {
        following.current = false
        setRefreshing(false)
      }
    }
    return result
  }, [])

  const load = useCallback(async () => apply(await api.dashboard()), [apply])

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      await load()
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [load])

  /** Bouton « Actualiser les données » : lance l'actualisation, la suit, puis recharge. */
  const refreshMarket = useCallback(async () => {
    setRefreshing(true)
    following.current = true
    try {
      await api.refresh()
      const report = await waitForRefresh()
      await load()
      return report
    } finally {
      following.current = false
      setRefreshing(false)
    }
  }, [load])

  useEffect(() => {
    let alive = true
    api.dashboard()
      .then((result) => alive && apply(result))
      .catch((err) => alive && setError(err))
      .finally(() => alive && setLoading(false))
    const timer = setInterval(() => load().catch(() => {}), RELECTURE_MS)
    const onVisible = () => {
      if (document.visibilityState === 'visible' && Date.now() - lastLoad.current > RELECTURE_MS) load().catch(() => {})
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      alive = false
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [apply, load])

  const value = useMemo(
    () => ({ data, error, loading, refreshing, reload, refreshMarket }),
    [data, error, loading, refreshing, reload, refreshMarket],
  )
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDashboard() {
  return useContext(DashboardContext)
}

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

// Données de GET /api/dashboard gardées pendant la session (UI §5.1) : la même réponse
// sert à l'accueil, au tableau de bord, au simulateur, à la NavBar et au bandeau d'alerte.
// On ne la redemande qu'après une opération ou une actualisation.
const DashboardContext = createContext(null)

export function DashboardProvider({ children }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await api.dashboard())
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  /** Bouton « Actualiser les données » : lance l'actualisation, suit son avancement
   *  toutes les 2 secondes (elle tourne en arrière-plan sur le serveur), puis recharge. */
  const refreshMarket = useCallback(async () => {
    setRefreshing(true)
    try {
      await api.refresh()
      for (let attempt = 0; attempt < 150; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000))
        const status = await api.refreshStatus()
        if (!status.en_cours) {
          if (status.erreur) throw new Error(`L'actualisation a échoué : ${status.erreur}`)
          await reload()
          return status.rapport
        }
      }
      throw new Error("L'actualisation prend plus de temps que prévu : réessayez dans quelques minutes.")
    } finally {
      setRefreshing(false)
    }
  }, [reload])

  useEffect(() => {
    let alive = true
    api.dashboard()
      .then((result) => alive && setData(result))
      .catch((err) => alive && setError(err))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [])

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

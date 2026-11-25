import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import Toast from '../components/layout/Toast'

// Messages courts de succès ou d'erreur (UI §4.1), affichés en bas de l'écran.
const ToastContext = createContext(() => {})

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null)
  const show = useCallback((message, tone = 'success') => {
    const id = Date.now()
    setToast({ id, message, tone })
    setTimeout(() => setToast((current) => (current?.id === id ? null : current)), 5000)
  }, [])
  const value = useMemo(() => show, [show])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toast toast={toast} onClose={() => setToast(null)} />
    </ToastContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  return useContext(ToastContext)
}

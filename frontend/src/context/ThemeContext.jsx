import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

// Thème clair / sombre (D-17). Le choix (« clair », « sombre » ou « systeme ») est gardé dans
// le navigateur ; « systeme » suit le réglage de l'ordinateur. Le thème s'applique avec
// data-theme="dark" sur <html> : les couleurs sombres de la charte (tokens.css) prennent le relais.
const ThemeContext = createContext(null)
const STORAGE_KEY = 'primeinvest-theme'
const media = () => window.matchMedia('(prefers-color-scheme: dark)')

function resolve(choice) {
  return choice === 'sombre' || (choice === 'systeme' && media().matches) ? 'dark' : 'light'
}

export function ThemeProvider({ children }) {
  const [choice, setChoice] = useState(() => localStorage.getItem(STORAGE_KEY) || 'systeme')
  const [systemDark, setSystemDark] = useState(() => media().matches)
  const resolved = choice === 'systeme' ? (systemDark ? 'dark' : 'light') : resolve(choice)

  useEffect(() => {
    document.documentElement.dataset.theme = resolved
  }, [resolved])

  useEffect(() => {
    const query = media()
    const onChange = (event) => setSystemDark(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const choose = useCallback((value) => {
    localStorage.setItem(STORAGE_KEY, value)
    setChoice(value)
  }, [])

  const toggle = useCallback(() => choose(resolved === 'dark' ? 'clair' : 'sombre'), [choose, resolved])

  const value = useMemo(() => ({ choice, resolved, choose, toggle }), [choice, resolved, choose, toggle])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  return useContext(ThemeContext)
}

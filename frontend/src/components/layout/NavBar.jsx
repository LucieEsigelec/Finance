import { LogOut, Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useDashboard } from '../../context/DashboardContext'
import { useTheme } from '../../context/ThemeContext'
import { useToast } from '../../context/ToastContext'
import { formatDateTime } from '../../lib/format'
import LogoutDialog from '../LogoutDialog'
import Button from '../ui/Button'
import Logo from './Logo'

// NavBar (UI §4.1, maquette NavBar) : logo « Prisme » (D-21) (retour à l'accueil), 6 onglets
// (dont Profil, D-17), date des données, bouton « Actualiser les données », bascule clair / sombre. « Actions » ouvre la fiche DSY.PA (D-09).
const TABS = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/tableau-de-bord', label: 'Tableau de bord' },
  { to: '/simulateur', label: 'Simulateur' },
  { to: '/action/DSY.PA', label: 'Actions', match: '/action/' },
  { to: '/historique', label: 'Historique' },
  { to: '/profil', label: 'Profil' },
]

/** Date des données, version courte pour la barre : « 26 nov., 15:34 » (complète au survol). */
const stampFormat = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
function shortStamp(iso) {
  return iso ? stampFormat.format(new Date(iso)).replace(' à ', ', ') : '—'
}

export default function NavBar() {
  const { data, refreshing, refreshMarket } = useDashboard()
  const toast = useToast()
  const { pathname } = useLocation()
  const { resolved, toggle } = useTheme()
  const [logout, setLogout] = useState(false)

  async function onRefresh() {
    try {
      const report = await refreshMarket()
      const failures = report?.erreurs?.length || 0
      toast(failures ? `Données actualisées, avec ${failures} source(s) indisponible(s).` : 'Données actualisées.')
    } catch (error) {
      toast(error.message, 'error')
    }
  }

  return (
    <header className="sticky top-0 z-40 h-16 border-b border-line bg-card">
      <div className="mx-auto flex h-full max-w-[1280px] items-center gap-6 px-4 sm:px-6">
        <NavLink to="/" aria-label="PrimeInvest, retour à l'accueil" className="shrink-0 no-underline">
          <Logo />
        </NavLink>
        <nav aria-label="Navigation principale" className="flex flex-1 gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) => {
                const active = isActive || (tab.match && pathname.startsWith(tab.match))
                return `rounded-md px-3 py-2 text-[15px] whitespace-nowrap no-underline ${active ? 'bg-brand-soft font-semibold text-brand' : 'text-muted hover:text-ink'}`
              }}
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
        <span className="hidden text-[13px] whitespace-nowrap text-muted lg:inline" title={`Données du ${formatDateTime(data?.date_donnees)}`}>
          {shortStamp(data?.date_donnees)}
        </span>
        <button
          type="button"
          onClick={toggle}
          aria-label={resolved === 'dark' ? 'Passer au thème clair' : 'Passer au thème sombre'}
          title={resolved === 'dark' ? 'Thème clair' : 'Thème sombre'}
          className="flex size-8 flex-none items-center justify-center rounded-md border border-line-strong text-ink hover:bg-sunken"
        >
          {resolved === 'dark' ? <Sun className="size-4" strokeWidth={1.75} /> : <Moon className="size-4" strokeWidth={1.75} />}
        </button>
        <Button size="sm" onClick={onRefresh} disabled={refreshing} title="Actualiser les données">
          {refreshing ? 'Actualisation…' : 'Actualiser'}
        </Button>
        <button
          type="button"
          onClick={() => setLogout(true)}
          aria-label="Se déconnecter"
          title={data?.nom_client ? `Se déconnecter (${data.nom_client})` : 'Se déconnecter'}
          className="flex size-8 flex-none items-center justify-center rounded-md border border-line-strong text-ink hover:bg-sunken"
        >
          <LogOut className="size-4" strokeWidth={1.75} />
        </button>
        {logout && <LogoutDialog onClose={() => setLogout(false)} />}
      </div>
    </header>
  )
}

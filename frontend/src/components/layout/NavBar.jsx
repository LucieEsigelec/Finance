import { NavLink, useLocation } from 'react-router-dom'
import { useDashboard } from '../../context/DashboardContext'
import { useToast } from '../../context/ToastContext'
import { formatDateTime } from '../../lib/format'
import Button from '../ui/Button'

// NavBar (UI §4.1, maquette NavBar) : nom de l'application (retour à l'accueil), 5 onglets,
// date des données, bouton « Actualiser les données ». « Actions » ouvre la fiche DSY.PA (D-09).
const TABS = [
  { to: '/', label: 'Accueil', end: true },
  { to: '/tableau-de-bord', label: 'Tableau de bord' },
  { to: '/simulateur', label: 'Simulateur' },
  { to: '/action/DSY.PA', label: 'Actions', match: '/action/' },
  { to: '/historique', label: 'Historique' },
]

function Logo() {
  return (
    <svg viewBox="0 0 20 20" className="size-5 text-brand" aria-hidden="true">
      <rect x="2" y="9" width="3.5" height="9" rx="1" fill="currentColor" />
      <rect x="8.25" y="5" width="3.5" height="13" rx="1" fill="currentColor" />
      <rect x="14.5" y="2" width="3.5" height="16" rx="1" fill="currentColor" />
    </svg>
  )
}

export default function NavBar() {
  const { data, refreshing, refreshMarket } = useDashboard()
  const toast = useToast()
  const { pathname } = useLocation()

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
        <NavLink to="/" className="flex items-center gap-2 text-[17px] font-bold tracking-[-.01em] text-ink no-underline">
          <Logo />
          <span className="hidden sm:inline">PrimeInvest</span>
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
        <span className="hidden text-[13px] text-muted lg:inline">Données du {formatDateTime(data?.date_donnees)}</span>
        <Button size="sm" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? 'Actualisation…' : 'Actualiser les données'}
        </Button>
      </div>
    </header>
  )
}

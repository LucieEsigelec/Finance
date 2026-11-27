import { Outlet } from 'react-router-dom'
import { useDashboard } from '../../context/DashboardContext'
import { MENTION } from '../../lib/stocks'
import WelcomeDialog from '../WelcomeDialog'
import AlertBanner from '../ui/AlertBanner'
import NavBar from './NavBar'

// Cadre de l'application : NavBar fixe, bandeau d'alerte juste dessous sur toutes les pages
// dès que le niveau n'est pas AUCUN (RG-01), contenu sur 1 280 px au plus (charte §7.6).
// Pied de page sur toutes les pages : avertissement sur les conseils (ENF-03, D-25).
export default function AppLayout() {
  const { data } = useDashboard()
  return (
    <div className="flex min-h-screen flex-col bg-page">
      <NavBar />
      <main className="mx-auto w-full max-w-[1280px] flex-1 px-4 pt-6 pb-12 sm:px-6">
        {data && data.niveau_alerte !== 'AUCUN' && (
          <div className="mb-6">
            <AlertBanner level={data.niveau_alerte} variation={data.variation_hebdo_pct} />
          </div>
        )}
        <Outlet />
      </main>
      <footer className="border-t border-line bg-card">
        <p className="mx-auto my-0 max-w-[1280px] px-4 py-4 text-[13px] leading-[18px] text-muted sm:px-6">{MENTION}</p>
      </footer>
      <WelcomeDialog />
    </div>
  )
}

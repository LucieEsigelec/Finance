import { Outlet } from 'react-router-dom'
import { useDashboard } from '../../context/DashboardContext'
import AlertBanner from '../ui/AlertBanner'
import NavBar from './NavBar'

// Cadre de l'application : NavBar fixe, bandeau d'alerte juste dessous sur toutes les pages
// dès que le niveau n'est pas AUCUN (RG-01), contenu sur 1 280 px au plus (charte §7.6).
export default function AppLayout() {
  const { data } = useDashboard()
  return (
    <div className="min-h-screen bg-page">
      <NavBar />
      <main className="mx-auto max-w-[1280px] px-4 pt-6 pb-12 sm:px-6">
        {data && data.niveau_alerte !== 'AUCUN' && (
          <div className="mb-6">
            <AlertBanner level={data.niveau_alerte} variation={data.variation_hebdo_pct} />
          </div>
        )}
        <Outlet />
      </main>
    </div>
  )
}

import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import LoadingState from './components/layout/LoadingState'
import AccueilPage from './pages/AccueilPage'
import DashboardPage from './pages/DashboardPage'
import SimulatorPage from './pages/SimulatorPage'

// Les pages avec graphiques (bibliothèques lourdes) ne sont chargées qu'à leur ouverture.
const StockDetailPage = lazy(() => import('./pages/StockDetailPage'))
const HistoryPage = lazy(() => import('./pages/HistoryPage'))

// Routes React (UI §3) : 5 onglets + fiche action. Toutes les pages partagent la NavBar
// et le bandeau d'alerte (AppLayout).
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<AccueilPage />} />
        <Route path="tableau-de-bord" element={<DashboardPage />} />
        <Route path="simulateur" element={<SimulatorPage />} />
        <Route path="action/:ticker" element={<Suspense fallback={<LoadingState />}><StockDetailPage /></Suspense>} />
        <Route path="historique" element={<Suspense fallback={<LoadingState />}><HistoryPage /></Suspense>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

function NotFound() {
  return (
    <div className="card p-6">
      <h1>Page introuvable</h1>
      <p className="text-muted">Cette adresse n'existe pas. Utilisez la barre de navigation pour continuer.</p>
    </div>
  )
}

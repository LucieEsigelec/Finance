import { Link } from 'react-router-dom'
import Disclaimer from '../components/layout/Disclaimer'
import ErrorState from '../components/layout/ErrorState'
import LoadingState from '../components/layout/LoadingState'
import RiskIndicator from '../components/RiskIndicator'
import StocksTable from '../components/StocksTable'
import KpiCard from '../components/ui/KpiCard'
import { useDashboard } from '../context/DashboardContext'
import { eurKpi, formatDate, formatDateTime, pct, pctPlain } from '../lib/format'

// Tableau de bord (/tableau-de-bord) — EF-01, RG-01, maquettes 02 et 05.
export default function DashboardPage() {
  const { data, loading, error, reload } = useDashboard()
  if (loading && !data) return <LoadingState rows={5} />
  if (error && !data) return <ErrorState error={error} onRetry={reload} />

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1>Tableau de bord</h1>
          <p className="mt-1 mb-0 text-[13px] text-muted">
            Semaine du {formatDate(data.semaine.debut)} au {formatDate(data.semaine.fin)} · capital de départ {eurKpi(data.capital_initial)}
          </p>
        </div>
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <Link to="/simulateur" className="inline-flex h-10 items-center rounded-md bg-brand px-4 font-semibold text-on-brand no-underline hover:opacity-90">
            Lancer une simulation
          </Link>
          <RiskIndicator variation={data.variation_hebdo_pct} level={data.niveau_alerte} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Capital total" value={eurKpi(data.capital_total)} delta={data.variation_depuis_depart_pct} deltaLabel="depuis le départ" />
        <KpiCard label="Cash disponible" value={eurKpi(data.cash_disponible)} hint={`${pctPlain(data.cash_pct)} du capital`} />
        <KpiCard
          label="Performance de la semaine"
          value={pct(data.variation_hebdo_pct)}
          valueClassName={data.variation_hebdo_pct < 0 ? 'text-sell' : ''}
          hint="Limite de perte : −10 %"
        />
        <KpiCard label="Part investie" value={pctPlain(data.part_investie_pct)} hint={`${data.nb_titres_detenus} titre${data.nb_titres_detenus > 1 ? 's' : ''} sur 5`} />
      </div>

      <section className="card">
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-4 pb-2">
          <h2>Vos 5 actions</h2>
          <span className="text-[13px] text-muted">Conseils recalculés le {formatDateTime(data.date_conseils)}</span>
        </div>
        <StocksTable actions={data.actions} />
      </section>

      <Disclaimer />
    </div>
  )
}

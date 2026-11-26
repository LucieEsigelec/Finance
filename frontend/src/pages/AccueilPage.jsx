import { ArrowRight, History, LayoutGrid, Calculator } from 'lucide-react'
import { Link } from 'react-router-dom'
import Disclaimer from '../components/layout/Disclaimer'
import ErrorState from '../components/layout/ErrorState'
import LoadingState from '../components/layout/LoadingState'
import DecisionBadge from '../components/ui/DecisionBadge'
import KpiCard from '../components/ui/KpiCard'
import { useDashboard } from '../context/DashboardContext'
import { eurKpi, eurSigned, formatDateTime, formatLongDate, pct, pctPlain, trendClass } from '../lib/format'
import { COLOR_BY_TICKER } from '../lib/stocks'

// Accueil (/) — maquette 01 : saluer le client, résumer sa semaine, l'orienter (UI §4.2).

const LINKS = [
  { to: '/tableau-de-bord', title: 'Tableau de bord', text: 'Valeur, alerte de perte et conseil sur vos 5 actions.', Icon: LayoutGrid },
  { to: '/simulateur', title: 'Simulateur', text: 'Testez un achat ou une vente et obtenez un conseil argumenté.', Icon: Calculator },
  { to: '/historique', title: 'Historique', text: 'Vos opérations et la performance du portefeuille.', Icon: History },
]

const alertText = { AUCUN: 'Aucune alerte de perte', APPROCHE: 'Proche de la limite de perte', ATTEINT: 'Limite de perte atteinte' }

export default function AccueilPage() {
  const { data, loading, error, reload, refreshing } = useDashboard()
  if (loading && !data) return <LoadingState rows={2} />
  if (error && !data) return <ErrorState error={error} onRetry={reload} />

  const groups = ['ACHAT', 'RIEN', 'VENTE'].map((decision) => ({ decision, actions: data.actions.filter((a) => a.conseil === decision) }))
  const name = data.nom_client || 'M. X'

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="label-caps">{formatLongDate()}</div>
          <h1 className="mt-2 text-[40px] leading-[48px] font-bold tracking-[-.02em]">Bonjour {name},</h1>
          <p className="mt-2 mb-0 text-[18px] text-muted">Bienvenue sur votre portefeuille de {eurKpi(data.capital_initial)}. Voici où vous en êtes cette semaine.</p>
        </div>
        <span className="inline-flex items-center gap-2 self-start rounded-md bg-buy-soft px-3 py-1.5 text-[13px] font-semibold text-buy sm:self-auto">
          <span className="size-2 rounded-full bg-buy" aria-hidden="true" /> {refreshing ? 'Actualisation en cours…' : `Données à jour · ${formatDateTime(data.date_donnees)}`}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard
          label="Valeur du portefeuille"
          value={eurKpi(data.capital_total)}
          delta={data.variation_depuis_depart_pct}
          deltaLabel={`depuis le départ (${eurSigned(data.variation_depuis_depart_eur)})`}
        />
        <KpiCard
          label="Cette semaine"
          value={pct(data.variation_hebdo_pct)}
          hint={`${eurSigned(data.variation_hebdo_eur)} · ${alertText[data.niveau_alerte]}`}
          valueClassName={trendClass(data.variation_hebdo_pct)}
        />
        <KpiCard label="Cash disponible" value={eurKpi(data.cash_disponible)} hint={`${pctPlain(data.cash_pct)} du capital`} />
      </div>

      <section className="card flex flex-col gap-4 p-4 sm:p-6">
        <div className="flex items-baseline justify-between">
          <h2>Les conseils de la semaine</h2>
          <Link to="/tableau-de-bord" className="inline-flex items-center gap-1 text-[15px] text-brand no-underline">Voir le détail <ArrowRight className="size-4" strokeWidth={1.75} /></Link>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {groups.map(({ decision, actions }) => (
            <div key={decision} className="flex flex-col gap-3 rounded-md bg-sunken p-4">
              <div><DecisionBadge decision={decision} /></div>
              {actions.length === 0 && <span className="text-[13px] text-muted">Aucune action</span>}
              {actions.map((a) => (
                <Link key={a.ticker} to={`/action/${a.ticker}`} className="flex items-center gap-2 text-ink no-underline hover:underline">
                  <span className="size-2 rounded-full" style={{ background: `var(--${COLOR_BY_TICKER[a.ticker]})` }} aria-hidden="true" />
                  <span>{a.nom}</span>
                  <span className="ticker">{a.ticker}</span>
                </Link>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2>Que voulez-vous faire ?</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {LINKS.map(({ to, title, text, Icon }) => (
            <Link key={to} to={to} className="card flex gap-4 p-4 text-ink no-underline hover:bg-sunken sm:p-5">
              <span className="flex size-10 flex-none items-center justify-center rounded-md bg-brand-soft text-brand"><Icon className="size-5" strokeWidth={1.75} /></span>
              <span>
                <span className="flex items-center gap-1 text-[18px] font-semibold">{title} <ArrowRight className="size-4" strokeWidth={1.75} /></span>
                <span className="mt-1 block text-muted">{text}</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <div className="flex flex-col gap-1">
        <p className="m-0 text-[13px] text-muted">
          Vos objectifs : environ +10 % par semaine visés (jamais garantis) · perte maximale acceptée : −10 % par semaine. Les conseils sont une aide à la décision : vous restez seul décideur.
        </p>
        <Disclaimer />
      </div>
    </div>
  )
}

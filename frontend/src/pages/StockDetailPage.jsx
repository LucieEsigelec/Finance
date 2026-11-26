import { ArrowLeft } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import Disclaimer from '../components/layout/Disclaimer'
import ErrorState from '../components/layout/ErrorState'
import LoadingState from '../components/layout/LoadingState'
import PriceChart from '../components/stock/PriceChart'
import {
  DividendSimulator,
  ForecastCard,
  NewsList,
  PillarWeights,
  RatiosTable,
  RecommendationCard,
  StockHeader,
} from '../components/stock/StockCards'
import { COLOR_BY_TICKER, STOCKS } from '../lib/stocks'

// Fiche action (/action/:ticker) — EF-03, RG-03, maquettes 06 et 07.
// Un seul appel GET /api/stocks/{ticker} alimente les deux onglets (UI §5.3) ;
// les périodes et les cases des indicateurs ne changent que l'affichage.

// 1J et 1S : bougies de 5 min et de 30 min (cours intrajournaliers, D-12) ; au-delà, bougies d'un jour.
const PERIODS = [['1J', 'jour'], ['1S', 'semaine'], ['1M', 31], ['3M', 92], ['6M', 183], ['1A', 366]]
const INDICATORS = [['mm20', 'MM20', 'chart-ma20'], ['mm50', 'MM50', 'chart-ma50'], ['mm200', 'MM200', 'chart-ma200'], ['bollinger', 'Bollinger', 'brand']]

export default function StockDetailPage() {
  const { ticker = 'DSY.PA' } = useParams()
  const code = ticker.toUpperCase()
  const [state, setState] = useState({ key: null, data: null, error: null })
  const [tab, setTab] = useState('graphique')
  const [period, setPeriod] = useState('3M')
  const [show, setShow] = useState({ mm20: true, mm50: true, mm200: true, bollinger: true })
  const [attempt, setAttempt] = useState(0)

  const requestKey = `${code}#${attempt}`
  useEffect(() => {
    let alive = true
    api.stock(code)
      .then((data) => alive && setState({ key: requestKey, data, error: null }))
      .catch((error) => alive && setState({ key: requestKey, data: null, error }))
    return () => {
      alive = false
    }
  }, [code, requestKey])
  const loading = state.key !== requestKey
  const sameStock = state.data?.entete.ticker === code

  const series = useMemo(() => {
    const graph = state.data?.graphique
    const span = PERIODS.find(([p]) => p === period)[1]
    if (typeof span === 'string') return graph?.intraday?.[span] || []
    const all = graph?.series || []
    if (!all.length) return all
    const days = span
    const last = new Date(all[all.length - 1].date)
    const start = new Date(last.getTime() - days * 86400000).toISOString().slice(0, 10)
    return all.filter((row) => row.date >= start)
  }, [state.data, period])

  if (loading && !sameStock) return <LoadingState rows={4} />
  if (state.error?.status === 404) {
    return (
      <div className="card flex flex-col items-start gap-3 p-6">
        <h1>Action inconnue</h1>
        <p className="m-0 text-muted">Le code « {code} » ne fait pas partie des 5 actions suivies.</p>
        <Link to="/tableau-de-bord" className="font-semibold text-brand">Retour au tableau de bord</Link>
      </div>
    )
  }
  if (state.error) return <ErrorState error={state.error} onRetry={() => setAttempt((n) => n + 1)} />

  const { data } = state
  const { graphique } = data
  const intraday = period === '1J' || period === '1S'
  const rsiLabel = graphique.rsi.valeur !== null ? `${graphique.rsi.valeur} · ${graphique.rsi.zone}` : null

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/tableau-de-bord" className="inline-flex items-center gap-1 text-[13px] font-medium text-brand no-underline">
          <ArrowLeft className="size-4" strokeWidth={1.75} aria-hidden="true" /> Tableau de bord
        </Link>
        <nav aria-label="Choisir une action" className="flex flex-wrap items-center gap-2">
          <span className="text-[13px] font-semibold text-muted">Voir une autre action :</span>
          {STOCKS.map((s) => {
            const current = s.ticker === code
            return (
              <Link
                key={s.ticker}
                to={`/action/${s.ticker}`}
                aria-current={current ? 'page' : undefined}
                title={`${s.nom} (${s.ticker})`}
                className={`inline-flex h-9 items-center gap-2 rounded-full border px-3 text-[14px] no-underline ${current ? 'border-brand bg-brand-soft font-semibold text-brand' : 'border-line-strong bg-card text-ink hover:bg-sunken'}`}
              >
                <span className="size-2 rounded-full" style={{ background: `var(--${s.color})` }} aria-hidden="true" />
                {s.nom}
              </Link>
            )
          })}
        </nav>
      </div>

      <StockHeader entete={data.entete} color={COLOR_BY_TICKER[code]} />

      <div role="tablist" aria-label="Onglets de la fiche" className="flex gap-6 border-b border-line">
        {[['graphique', 'Graphique'], ['infos', "Infos sur l'action"]].map(([key, label]) => (
          <button
            key={key}
            role="tab"
            type="button"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`-mb-px border-b-2 px-1 pb-3 text-[15px] ${tab === key ? 'border-brand font-semibold text-brand' : 'border-transparent text-muted hover:text-ink'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'graphique' ? (
        <div className="grid items-start gap-6 lg:grid-cols-[1fr_360px]">
          <section className="card p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div className="flex gap-2" role="group" aria-label="Période">
                {PERIODS.map(([p]) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setPeriod(p)}
                    aria-pressed={period === p}
                    className={`h-8 rounded-md border px-3 text-[13px] font-semibold ${period === p ? 'border-brand bg-brand-soft text-brand' : 'border-line-strong bg-card text-ink hover:bg-sunken'}`}
                  >
                    {p}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-3 text-[13px]">
                {INDICATORS.map(([key, label, color]) => (
                  <label key={key} className="flex cursor-pointer items-center gap-1.5">
                    <input type="checkbox" checked={show[key]} onChange={() => setShow((s) => ({ ...s, [key]: !s[key] }))} className="accent-[var(--brand)]" />
                    <span className="h-0.5 w-3" style={{ background: `var(--${color})` }} aria-hidden="true" />
                    {label}
                  </label>
                ))}
              </div>
            </div>
            {series.length ? (
              <>
                <PriceChart series={series} show={show} rsiLabel={rsiLabel} macdLabel={graphique.macd.libelle} intraday={intraday} />
                {intraday && (
                  <p className="mt-2 mb-0 text-[13px] text-muted">
                    {period === '1J' ? 'Dernière séance, bougies de 5 minutes' : '5 dernières séances, bougies de 30 minutes'}, heure de Paris. Indicateurs calculés sur ces bougies ; le conseil, lui, repose sur les cours de clôture.
                  </p>
                )}
              </>
            ) : (
              <p className="m-0 text-muted">
                {intraday ? 'Cours intrajournaliers pas encore disponibles : ils arrivent avec la prochaine actualisation.' : 'Aucun cours disponible : lancez une actualisation des données.'}
              </p>
            )}
          </section>
          <div className="flex flex-col gap-6">
            <RecommendationCard conseil={data.conseil} />
            <ForecastCard prevision={data.prevision} />
            <DividendSimulator key={code} dividende={data.dividende} />
          </div>
        </div>
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-[1fr_360px]">
          <NewsList infos={data.infos} />
          <div className="flex flex-col gap-6">
            <RatiosTable ratios={data.infos.ratios} />
            <PillarWeights piliers={data.infos.piliers} />
          </div>
        </div>
      )}

      <Disclaimer />
    </div>
  )
}

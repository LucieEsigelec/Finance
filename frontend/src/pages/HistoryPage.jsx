import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import ErrorState from '../components/layout/ErrorState'
import LoadingState from '../components/layout/LoadingState'
import Button from '../components/ui/Button'
import DecisionBadge from '../components/ui/DecisionBadge'
import KpiCard from '../components/ui/KpiCard'
import { eur, eurKpi, formatDate, formatDateTime, integer, trendClass } from '../lib/format'
import { STOCKS } from '../lib/stocks'

// Historique (/historique) — RG-06, maquette 08. Chaque changement de période, de titre
// ou de page rappelle GET /api/portfolio/history (UI §5.7).

const PERIODS = [['1s', '1 semaine'], ['1m', '1 mois'], ['3m', '3 mois'], ['1a', '1 an']]
const shortDate = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' })
const eur0 = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
const axisEur = (v) => eur0.format(v).replace(/-/g, '\u2212')

/** Graduations « rondes » (pas de 1, 2, 2,5 ou 5 × 10ⁿ €) couvrant la courbe, avec de la place
 *  en haut pour les étiquettes des opérations (D-18). */
function niceTicks(min, max) {
  const raw = Math.max(max - min, 400) / 4
  const power = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((v) => v >= raw)
  const low = Math.floor((min - step * 0.25) / step) * step
  const high = Math.ceil((max + step * 0.25) / step) * step + step
  const ticks = []
  for (let v = low; v <= high + 1e-6; v += step) ticks.push(Math.round(v))
  return ticks
}

/** Les opérations d'un même jour sont regroupées : un seul repère, une étiquette sur deux lignes. */
function groupMarkers(markers) {
  const byDate = {}
  markers.forEach((m) => {
    const day = (byDate[m.date] ||= { date: m.date, achats: [], ventes: [] })
    const list = m.operation === 'ACHAT' ? day.achats : day.ventes
    const code = m.ticker.split('.')[0]
    if (!list.includes(code)) list.push(code)
  })
  return Object.values(byDate)
}

function MarkerLabel({ viewBox, day, edge }) {
  if (!viewBox) return null
  // Au premier et au dernier jour, l'étiquette est tournée vers l'intérieur du graphique (pas coupée au bord).
  const center = viewBox.x + viewBox.width / 2
  const x = edge === 'end' ? center + 6 : edge === 'start' ? center - 6 : center
  const anchor = edge === 'end' ? 'end' : edge === 'start' ? 'start' : 'middle'
  const lines = [
    day.achats.length && { text: `▲ ${day.achats.join(', ')}`, fill: 'var(--buy)' },
    day.ventes.length && { text: `▼ ${day.ventes.join(', ')}`, fill: 'var(--sell)' },
  ].filter(Boolean)
  return (
    <text x={x} y={viewBox.y - 8 - (lines.length - 1) * 15} textAnchor={anchor} fontSize={12} fontWeight={600} stroke="var(--surface-card)" strokeWidth={4} paintOrder="stroke" strokeLinejoin="round">
      {lines.map((line, i) => (
        <tspan key={line.text} x={x} dy={i === 0 ? 0 : 15} fill={line.fill}>{line.text}</tspan>
      ))}
    </text>
  )
}

function ChartTooltip({ active, payload, label, operations }) {
  if (!active || !payload?.length) return null
  const day = operations[label]
  return (
    <div className="rounded-md border border-line bg-card px-3 py-2 text-[13px] shadow-[var(--shadow-card)]">
      <div className="font-semibold">{formatDate(label)}</div>
      <div className="num">{eur(payload[0].value)}</div>
      {day?.achats.length > 0 && <div className="text-buy">▲ Achat : {day.achats.join(', ')}</div>}
      {day?.ventes.length > 0 && <div className="text-sell">▼ Vente : {day.ventes.join(', ')}</div>}
    </div>
  )
}

export default function HistoryPage() {
  const [periode, setPeriode] = useState('1m')
  const [ticker, setTicker] = useState('')
  const [page, setPage] = useState(1)
  const [state, setState] = useState({ key: null, data: null, error: null })
  const [attempt, setAttempt] = useState(0)

  const requestKey = `${periode}|${ticker}|${page}|${attempt}`
  useEffect(() => {
    let alive = true
    api.history({ periode, ticker, page, taille: 10 })
      .then((data) => alive && setState({ key: requestKey, data, error: null }))
      .catch((error) => alive && setState((s) => ({ ...s, key: requestKey, error })))
    return () => {
      alive = false
    }
  }, [periode, ticker, page, requestKey])

  const { data, error } = state
  const loading = state.key !== requestKey
  if (loading && !data) return <LoadingState rows={4} />
  if (error && !data) return <ErrorState error={error} onRetry={() => setAttempt((n) => n + 1)} />

  const { bilan } = data
  const values = data.courbe.map((p) => p.valeur).concat(data.capital_initial)
  const ticks = niceTicks(Math.min(...values), Math.max(...values))
  const valueAt = Object.fromEntries(data.courbe.map((p) => [p.date, p.valeur]))
  const days = groupMarkers(data.marqueurs).filter((d) => valueAt[d.date] !== undefined)
  const operations = Object.fromEntries(days.map((d) => [d.date, d]))
  const firstDate = data.courbe[0]?.date
  const lastDate = data.courbe[data.courbe.length - 1]?.date
  const dividendDetail = Object.entries(bilan.dividendes_par_titre).map(([t, v]) => `${t.split('.')[0]} ${eur(v)}`).join(' · ')

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1>Historique</h1>
          <p className="mt-1 mb-0 text-[13px] text-muted">Vos allers-retours et la performance du portefeuille, sur un an au plus.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {PERIODS.map(([code, label]) => (
            <button
              key={code}
              type="button"
              aria-pressed={periode === code}
              onClick={() => { setPeriode(code); setPage(1) }}
              className={`h-8 rounded-md border px-3 text-[13px] font-semibold ${periode === code ? 'border-brand bg-brand-soft text-brand' : 'border-line-strong bg-card hover:bg-sunken'}`}
            >
              {label}
            </button>
          ))}
          <label htmlFor="filtre-titre" className="ml-2 text-[13px] font-semibold">Titre</label>
          <select
            id="filtre-titre"
            value={ticker}
            onChange={(e) => { setTicker(e.target.value); setPage(1) }}
            className="h-8 rounded-md border border-line-strong bg-card px-2 text-[13px]"
          >
            <option value="">Tous les titres</option>
            {STOCKS.map((s) => <option key={s.ticker} value={s.ticker}>{s.nom}</option>)}
          </select>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Valeur du portefeuille" value={eurKpi(bilan.valeur)} delta={bilan.variation_depuis_depart_pct} deltaLabel="depuis le départ" />
        <KpiCard
          label="Plus-values réalisées"
          value={`${bilan.plus_values_realisees > 0 ? '+' : ''}${eur(bilan.plus_values_realisees)}`}
          valueClassName={trendClass(bilan.plus_values_realisees)}
          hint={bilan.nb_ventes ? `${bilan.nb_ventes} vente${bilan.nb_ventes > 1 ? 's' : ''} : ${[...new Set(bilan.ventes.map((v) => v.nom))].join(', ')}` : 'Aucune vente sur la période'}
        />
        <KpiCard label="Dividendes estimés / an" value={eur(bilan.dividendes_estimes_an)} hint={dividendDetail || 'Aucune action détenue'} />
        <KpiCard label="Opérations" value={integer(bilan.nb_operations)} hint={`${bilan.nb_achats} achat${bilan.nb_achats > 1 ? 's' : ''} · ${bilan.nb_ventes} vente${bilan.nb_ventes > 1 ? 's' : ''}`} />
      </div>

      <section className="card p-4">
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
          <h2>Valeur du portefeuille</h2>
          <span className="text-[13px] text-muted">Du {formatDate(data.periode.debut)} au {formatDate(data.periode.fin)} · ▲ achat · ▼ vente</span>
        </div>
        <div className="h-72" role="img" aria-label="Courbe de la valeur du portefeuille">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.courbe} margin={{ top: 16, right: 32, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="date" tickFormatter={(d) => shortDate.format(new Date(d))} stroke="var(--ink-muted)" tick={{ fontSize: 12 }} minTickGap={40} />
              <YAxis domain={[ticks[0], ticks[ticks.length - 1]]} ticks={ticks} tickFormatter={axisEur} stroke="var(--ink-muted)" tick={{ fontSize: 12 }} width={88} />
              <Tooltip content={<ChartTooltip operations={operations} />} />
              <ReferenceLine y={data.capital_initial} stroke="var(--ink-muted)" strokeDasharray="4 4" label={{ value: `Départ : ${eurKpi(data.capital_initial)}`, position: 'insideBottomLeft', fill: 'var(--ink-muted)', fontSize: 12 }} />
              <Line type="monotone" dataKey="valeur" stroke="var(--brand)" strokeWidth={2} dot={false} isAnimationActive={false} />
              {days.map((day) => {
                const mixed = day.achats.length && day.ventes.length
                return (
                  <ReferenceDot
                    key={day.date}
                    x={day.date}
                    y={valueAt[day.date]}
                    r={5}
                    fill="var(--surface-card)"
                    stroke={mixed ? 'var(--ink)' : day.achats.length ? 'var(--buy)' : 'var(--sell)'}
                    strokeWidth={2}
                    label={<MarkerLabel day={day} edge={day.date === lastDate ? 'end' : day.date === firstDate ? 'start' : null} />}
                  />
                )
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card">
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-4 pb-2">
          <h2>Journal des opérations</h2>
          <span className="text-[13px] text-muted">Le conseil affiché est celui donné au moment de l'opération.</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] border-collapse text-left">
            <thead>
              <tr className="border-b border-line">
                {['Date', 'Action', 'Opération', 'Actions', 'Prix', 'Montant', 'Conseil donné', 'Plus ou moins-value'].map((h, i) => (
                  <th key={h} className={`label-caps px-4 py-3 ${[3, 4, 5, 7].includes(i) ? 'text-right' : ''}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.transactions.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-6 text-center text-muted">Aucune opération sur cette période.</td></tr>
              )}
              {data.transactions.map((tx) => (
                <tr key={tx.id} className="border-b border-line last:border-0">
                  <td className="num px-4 py-3">{formatDateTime(tx.date)}</td>
                  <td className="px-4 py-3"><div className="font-medium">{tx.nom}</div><div className="ticker">{tx.ticker}</div></td>
                  <td className={`px-4 py-3 font-medium ${tx.operation === 'ACHAT' ? 'text-buy' : 'text-sell'}`}>{tx.operation === 'ACHAT' ? '▲ Achat' : '▼ Vente'}</td>
                  <td className="num px-4 py-3 text-right">{integer(tx.quantite)}</td>
                  <td className="num px-4 py-3 text-right">{eur(tx.prix)}</td>
                  <td className="num px-4 py-3 text-right font-semibold">{eur(tx.montant)}</td>
                  <td className="px-4 py-3"><DecisionBadge decision={tx.conseil_donne} /></td>
                  <td className={`num px-4 py-3 text-right font-semibold ${trendClass(tx.plus_ou_moins_value)}`}>
                    {tx.plus_ou_moins_value === null ? '—' : `${tx.plus_ou_moins_value > 0 ? '+' : ''}${eur(tx.plus_ou_moins_value)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-line px-4 py-3">
          <span className="text-[13px] text-muted">
            {data.pagination.total} opération{data.pagination.total > 1 ? 's' : ''} · page {data.pagination.page} sur {data.pagination.pages}
          </span>
          <div className="flex gap-2">
            <Button size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Précédent</Button>
            <Button size="sm" disabled={page >= data.pagination.pages} onClick={() => setPage((p) => p + 1)}>Suivant</Button>
          </div>
        </div>
      </section>
    </div>
  )
}

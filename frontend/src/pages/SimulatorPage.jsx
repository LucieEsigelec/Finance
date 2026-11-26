import { Info } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import ConfirmDialog from '../components/ConfirmDialog'
import Disclaimer from '../components/layout/Disclaimer'
import SimulatorPanel from '../components/SimulatorPanel'
import AdviceCard from '../components/ui/AdviceCard'
import Button from '../components/ui/Button'
import { useDashboard } from '../context/DashboardContext'
import { useToast } from '../context/ToastContext'
import { eur, formatDateTime, integer, pct, trendClass } from '../lib/format'
import { STOCKS } from '../lib/stocks'

// Simulateur (/simulateur) — EF-02, RG-02, RG-03, RG-05, maquettes 03 et 04.
// Seul chemin d'écriture : Simuler → Valider → ConfirmDialog → POST /api/transactions → tableau de bord.

/** « 20 000,50 » → 20000.5 ; NaN si la saisie n'est pas un nombre. */
function parseAmount(text) {
  const cleaned = text.replace(/[\s  €]/g, '').replace(',', '.')
  return cleaned === '' ? NaN : Number(cleaned)
}

export default function SimulatorPage() {
  const { data, reload } = useDashboard()
  const toast = useToast()
  const navigate = useNavigate()
  const [selected, setSelected] = useState([])
  const [operation, setOperation] = useState('ACHAT')
  const [amounts, setAmounts] = useState({})
  const [errors, setErrors] = useState({})
  const [simulation, setSimulation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [toConfirm, setToConfirm] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const toggle = (ticker) => {
    setSelected((current) => (current.includes(ticker) ? current.filter((t) => t !== ticker) : [...current, ticker]))
    setErrors((current) => ({ ...current, [ticker]: undefined }))
  }

  /** Saisir un montant coche l'action ; l'effacer la décoche. */
  const changeAmount = (ticker, value) => {
    setAmounts((current) => ({ ...current, [ticker]: value }))
    setErrors((current) => ({ ...current, [ticker]: undefined }))
    setSelected((current) => {
      if (value.trim() && !current.includes(ticker)) return [...current, ticker]
      if (!value.trim() && current.includes(ticker)) return current.filter((t) => t !== ticker)
      return current
    })
  }

  const total = selected.reduce((sum, t) => sum + (parseAmount(amounts[t] || '') || 0), 0)

  // Vente : actions détenues et cours, pour afficher la position et bloquer une vente trop grande (D-19).
  const holdings = Object.fromEntries((data?.actions || []).map((a) => [a.ticker, { detenues: a.detenues || 0, cours: a.cours }]))
  const sellErrors = operation === 'VENTE'
    ? Object.fromEntries(
        selected.flatMap((ticker) => {
          const held = holdings[ticker]
          if (!held) return []
          const name = STOCKS.find((s) => s.ticker === ticker)?.nom || ticker
          if (!held.detenues) return [[ticker, `Vous ne détenez aucune action ${name}`]]
          const max = held.detenues * held.cours
          const amount = parseAmount(amounts[ticker] || '')
          return amount > max + 0.005 ? [[ticker, `Vous ne détenez que ${integer(held.detenues)} actions (≈ ${eur(max)})`]] : []
        }),
      )
    : {}
  const blocked = Object.keys(sellErrors).length > 0

  async function onSimulate() {
    if (blocked) return
    if (!selected.length) {
      toast('Cochez au moins une action et indiquez son montant.', 'error')
      return
    }
    const invalid = Object.fromEntries(
      selected.filter((t) => !(parseAmount(amounts[t] || '') > 0)).map((t) => [t, 'Saisissez un montant supérieur à 0']),
    )
    if (Object.keys(invalid).length) {
      setErrors(invalid)
      return
    }
    setErrors({})
    setLoading(true)
    try {
      const lines = selected.map((t) => ({ ticker: t, montant_eur: parseAmount(amounts[t]) }))
      setSimulation(await api.simulate(lines, operation))
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  async function onConfirm() {
    setSubmitting(true)
    try {
      const response = await api.recordTransaction({
        ticker: toConfirm.ticker,
        operation: toConfirm.operation,
        quantite: toConfirm.quantite_entiere,
        cours_simule: toConfirm.cours_actuel,
        date_conseil: simulation.date_conseil,
      })
      toast(response.message)
      const recorded = toConfirm.ticker
      setToConfirm(null)
      await reload()
      // D'autres opérations restent à valider : on reste sur le simulateur.
      const remaining = simulation.resultats.filter(
        (r) => r.ticker !== recorded && r.verdict !== 'REFUSE' && r.quantite_entiere > 0 && !r.enregistre,
      )
      if (remaining.length) {
        setSimulation((current) => ({
          ...current,
          resultats: current.resultats.map((r) => (r.ticker === recorded ? { ...r, enregistre: true } : r)),
        }))
      } else {
        navigate('/tableau-de-bord')
      }
    } catch (error) {
      toast(error.message, 'error') // la fenêtre reste ouverte, rien n'est enregistré
    } finally {
      setSubmitting(false)
    }
  }

  const dismiss = (ticker) =>
    setSimulation((current) => {
      const resultats = current.resultats.filter((r) => r.ticker !== ticker)
      return resultats.length ? { ...current, resultats } : null
    })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1>Simulateur</h1>
          <p className="mt-1 mb-0 text-[13px] text-muted">
            Choisissez une ou plusieurs actions, un montant et une opération : l'application vous donne son conseil avant que vous décidiez.
          </p>
        </div>
        {data && (
          <div className="flex gap-6 text-right">
            <div>
              <div className="label-caps">Cash disponible</div>
              <div className="num font-semibold">{eur(data.cash_disponible)}</div>
            </div>
            <div>
              <div className="label-caps">Perte de la semaine</div>
              <div className={`num font-semibold ${trendClass(data.variation_hebdo_pct)}`}>{pct(data.variation_hebdo_pct)} · limite −10 %</div>
            </div>
          </div>
        )}
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[400px_1fr]">
        <SimulatorPanel
          selected={selected}
          onToggle={toggle}
          operation={operation}
          onOperation={setOperation}
          amounts={amounts}
          onAmount={changeAmount}
          errors={{ ...sellErrors, ...Object.fromEntries(Object.entries(errors).filter(([, message]) => message)) }}
          holdings={holdings}
          blocked={blocked}
          total={total}
          cash={data?.cash_disponible}
          onSimulate={onSimulate}
          loading={loading}
        />

        <section className="flex flex-col gap-4" aria-live="polite">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2>Conseil pour votre opération</h2>
            {simulation && (
              <span className="text-[13px] text-muted">Simulation du {formatDateTime(simulation.date_conseil)} · rien n'est encore enregistré</span>
            )}
          </div>
          {!simulation && (
            <div className="card p-6 text-muted">
              Cochez une action, saisissez un montant puis cliquez sur « Simuler » : le conseil et ses raisons s'afficheront ici.
            </div>
          )}
          {simulation?.avertissement && (
            <div className="rounded-md bg-warn-soft px-4 py-3 text-[13px]">{simulation.avertissement}</div>
          )}
          <div className="grid gap-4 xl:grid-cols-2">
            {simulation?.resultats.map((result) => (
              <AdviceCard key={result.ticker} result={result}>
                {result.enregistre ? (
                  <div className="rounded-md bg-buy-soft px-3 py-2 text-right font-semibold text-buy">✓ Opération enregistrée</div>
                ) : (
                  <div className="flex justify-end gap-2">
                    <Button onClick={() => dismiss(result.ticker)}>Annuler</Button>
                    <Button
                      variant={result.operation === 'ACHAT' ? 'buy' : 'sell'}
                      disabled={result.verdict === 'REFUSE' || !result.quantite_entiere}
                      onClick={() => setToConfirm(result)}
                    >
                      {result.operation === 'ACHAT' ? "Valider l'achat" : 'Valider la vente'}
                    </Button>
                  </div>
                )}
              </AdviceCard>
            ))}
          </div>
          {simulation?.total && simulation.resultats.length > 1 && <SimulationTotal total={simulation.total} operation={operation} />}
          <div className="flex gap-3 rounded-md bg-sunken p-4 text-[13px] leading-[18px]">
            <Info className="mt-px size-4 flex-none text-brand" strokeWidth={1.75} aria-hidden="true" />
            <span>
              Le conseil est une aide : vous restez libre de valider ou non. Le nombre d'actions est arrondi à l'entier inférieur, le reste du montant reste en cash. Chaque action se valide séparément.
            </span>
          </div>
          <Disclaimer />
        </section>
      </div>

      {toConfirm && (
        <ConfirmDialog
          result={toConfirm}
          cash={data?.cash_disponible ?? simulation.cash_disponible}
          submitting={submitting}
          onCancel={() => setToConfirm(null)}
          onConfirm={onConfirm}
        />
      )}
    </div>
  )
}

/** Récapitulatif de toutes les lignes simulées (D-14). */
function SimulationTotal({ total, operation }) {
  const isBuy = operation === 'ACHAT'
  const rows = [
    [isBuy ? 'Montant réellement investi' : 'Montant encaissé', eur(total.montant_reel)],
    [isBuy ? 'Reste en cash (arrondis)' : 'Montant non vendu', eur(total.reliquat)],
    [isBuy ? 'Dividendes estimés / an' : 'Dividendes perdus / an', eur(total.dividende_annuel)],
    ['Cash après toutes les opérations', eur(total.cash_apres)],
  ]
  return (
    <section className="card p-4" aria-label="Total de la simulation">
      <div className="flex items-baseline justify-between">
        <h2>Total de l'opération</h2>
        <span className="text-[13px] text-muted">
          {total.nb_operations} action{total.nb_operations > 1 ? 's' : ''}
          {total.nb_refusees ? ` · ${total.nb_refusees} refusée${total.nb_refusees > 1 ? 's' : ''}` : ''} · demandé {eur(total.montant_demande)}
        </span>
      </div>
      <dl className="m-0 mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 border-b border-line py-1.5">
            <dt className="text-muted">{label}</dt>
            <dd className="num m-0 font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

import { Info } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import ConfirmDialog from '../components/ConfirmDialog'
import SimulatorPanel from '../components/SimulatorPanel'
import AdviceCard from '../components/ui/AdviceCard'
import Button from '../components/ui/Button'
import { useDashboard } from '../context/DashboardContext'
import { useToast } from '../context/ToastContext'
import { eur, formatDateTime, integer, pct, pctPlain, trendClass } from '../lib/format'
import { STOCKS } from '../lib/stocks'

// Acheter / vendre (/ordres, ex-« Simulateur », D-26) — EF-02, RG-02, RG-03, RG-05, maquettes 03 et 04.
// Seul chemin d'écriture : Voir le conseil → Valider → ConfirmDialog → POST /api/transactions → tableau de bord.
// Saisie au choix en euros ou en nombre d'actions ; à l'achat, un avertissement s'affiche si la part du
// capital sur une même action dépasse le seuil du profil (Prudent 10 %, Équilibré 20 %, Dynamique 35 %).
// Rien n'est bloqué : le client reste seul décideur (D-27).

/** « 20 000,50 » → 20000.5 ; NaN si la saisie n'est pas un nombre. */
function parseAmount(text) {
  const cleaned = text.replace(/[\s  €]/g, '').replace(',', '.')
  return cleaned === '' ? NaN : Number(cleaned)
}

/** « 1 250 » → 1250 ; NaN si ce n'est pas un nombre entier d'actions. */
function parseShares(text) {
  const cleaned = text.replace(/[\s  ]/g, '')
  return /^\d+$/.test(cleaned) ? Number(cleaned) : NaN
}

export default function SimulatorPage() {
  const { data, reload } = useDashboard()
  const toast = useToast()
  const navigate = useNavigate()
  // Arrivée depuis la fiche action (« Acheter / vendre », D-22) : ?action=DSY.PA&operation=VENTE
  const [params] = useSearchParams()
  const [selected, setSelected] = useState(() => {
    const ticker = params.get('action')
    return STOCKS.some((s) => s.ticker === ticker) ? [ticker] : []
  })
  const [operation, setOperation] = useState(() => (params.get('operation') === 'VENTE' ? 'VENTE' : 'ACHAT'))
  const [unit, setUnit] = useState('eur') // 'eur' : montant ; 'actions' : nombre d'actions (D-26)
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


  // Actions détenues et cours : position affichée, ventes trop grandes (D-19), part du capital (D-27).
  const holdings = Object.fromEntries((data?.actions || []).map((a) => [a.ticker, { detenues: a.detenues || 0, cours: a.cours }]))
  /** Changer d'unité convertit ce qui est déjà saisi : 10 000 € → 127 actions, 50 actions → 9 535 €. */
  const changeUnit = (value) => {
    if (value === unit) return
    setAmounts((current) =>
      Object.fromEntries(
        Object.entries(current).map(([ticker, text]) => {
          const price = holdings[ticker]?.cours
          const number = unit === 'eur' ? parseAmount(text || '') : parseShares(text || '')
          if (!price || !(number > 0)) return [ticker, '']
          return [ticker, value === 'actions' ? String(Math.floor(number / price)) : (Math.round(number * price * 100) / 100).toString().replace('.', ',')]
        }),
      ),
    )
    setUnit(value)
    setErrors({})
  }

  const parsed = (ticker) => (unit === 'eur' ? parseAmount(amounts[ticker] || '') : parseShares(amounts[ticker] || ''))
  /** Valeur en euros d'une ligne (montant saisi, ou nombre d'actions × cours). */
  const lineValue = (ticker) => {
    const value = parsed(ticker)
    if (!(value > 0)) return 0
    return unit === 'eur' ? value : value * (holdings[ticker]?.cours || 0)
  }
  const total = selected.reduce((sum, t) => sum + lineValue(t), 0)
  const nameOf = (ticker) => STOCKS.find((s) => s.ticker === ticker)?.nom || ticker
  const profil = data?.profil
  const capital = data?.capital_total

  const lineErrors = Object.fromEntries(
    selected.flatMap((ticker) => {
      const held = holdings[ticker]
      if (!held) return []
      if (operation !== 'VENTE') return []
      const value = lineValue(ticker)
      if (!held.detenues) return [[ticker, `Vous ne détenez aucune action ${nameOf(ticker)}`]]
      const tooMany = unit === 'eur' ? value > held.detenues * held.cours + 0.005 : parsed(ticker) > held.detenues
      return tooMany ? [[ticker, `Vous ne détenez que ${integer(held.detenues)} actions (≈ ${eur(held.detenues * held.cours)})`]] : []
    }),
  )
  const blocked = Object.keys(lineErrors).length > 0
  const blockedMessage = "Vous ne pouvez pas vendre plus d'actions que vous n'en possédez : corrigez les lignes en rouge."
  const threshold = profil?.seuil_exposition_pct ?? 35

  // Aide sous chaque ligne : conversion euros ↔ actions et part du capital après l'achat.
  const hints = Object.fromEntries(
    selected.flatMap((ticker) => {
      const held = holdings[ticker]
      const value = lineValue(ticker)
      if (!held || !(value > 0)) return []
      const parts = [unit === 'eur' ? `≈ ${integer(Math.floor(value / held.cours))} actions` : `≈ ${eur(value)}`]
      let warn = false
      if (operation === 'ACHAT' && capital) {
        const after = (held.detenues * held.cours + value) / capital * 100
        parts.push(`${pctPlain(after)} de votre capital sur cette action`)
        warn = after > threshold
      }
      return [[ticker, { text: parts.join(' · '), warn }]]
    }),
  )

  async function onSimulate() {
    if (blocked) return
    if (!selected.length) {
      toast('Cochez au moins une action et indiquez son montant.', 'error')
      return
    }
    const invalid = Object.fromEntries(
      selected
        .filter((t) => !(parsed(t) > 0))
        .map((t) => [t, unit === 'eur' ? 'Saisissez un montant supérieur à 0' : "Saisissez un nombre entier d'actions"]),
    )
    if (Object.keys(invalid).length) {
      setErrors(invalid)
      return
    }
    setErrors({})
    setLoading(true)
    try {
      const lines = selected.map((t) => (unit === 'eur' ? { ticker: t, montant_eur: parsed(t) } : { ticker: t, quantite: parsed(t) }))
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
      // D'autres opérations restent à valider : on reste sur la page.
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
          <h1>Acheter ou vendre</h1>
          <p className="mt-1 mb-0 text-[13px] text-muted">
            Choisissez une ou plusieurs actions, un montant ou un nombre d'actions : l'application vous donne son conseil avant que vous décidiez.
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
          unit={unit}
          onUnit={changeUnit}
          amounts={amounts}
          onAmount={changeAmount}
          errors={{ ...lineErrors, ...Object.fromEntries(Object.entries(errors).filter(([, message]) => message)) }}
          hints={hints}
          holdings={holdings}
          blocked={blocked}
          blockedMessage={blockedMessage}
          total={total}
          cash={data?.cash_disponible}
          onSimulate={onSimulate}
          loading={loading}
        />

        <section className="flex flex-col gap-4" aria-live="polite">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2>Conseil pour votre opération</h2>
            {simulation && (
              <span className="text-[13px] text-muted">Conseil du {formatDateTime(simulation.date_conseil)} · rien n'est encore enregistré</span>
            )}
          </div>
          {!simulation && (
            <div className="card p-6 text-muted">
              Cochez une action, saisissez un montant ou un nombre d'actions puis cliquez sur « Voir le conseil » : le conseil et ses raisons s'afficheront ici.
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
              Vous restez libre de valider ou non. Saisi en euros, le nombre d'actions est arrondi à l'entier inférieur et le reste du montant reste en cash. Chaque action se valide séparément.
            </span>
          </div>
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

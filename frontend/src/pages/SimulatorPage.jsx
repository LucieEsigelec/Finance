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
import { eur, formatDateTime, pct, trendClass } from '../lib/format'

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
  const [amount, setAmount] = useState('')
  const [amountError, setAmountError] = useState(null)
  const [simulation, setSimulation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [toConfirm, setToConfirm] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const toggle = (ticker) =>
    setSelected((current) => (current.includes(ticker) ? current.filter((t) => t !== ticker) : [...current, ticker]))

  async function onSimulate() {
    const value = parseAmount(amount)
    if (!selected.length) {
      toast('Cochez au moins une action.', 'error')
      return
    }
    if (!(value > 0)) {
      setAmountError('Saisissez un montant supérieur à 0')
      return
    }
    setAmountError(null)
    setLoading(true)
    try {
      setSimulation(await api.simulate(selected, operation, value))
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
      setToConfirm(null)
      await reload()
      navigate('/tableau-de-bord')
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
          amount={amount}
          onAmount={(value) => {
            setAmount(value)
            setAmountError(null)
          }}
          amountError={amountError}
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
              </AdviceCard>
            ))}
          </div>
          <div className="flex gap-3 rounded-md bg-sunken p-4 text-[13px] leading-[18px]">
            <Info className="mt-px size-4 flex-none text-brand" strokeWidth={1.75} aria-hidden="true" />
            <span>
              Le conseil est une aide : vous restez libre de valider ou non. Le nombre d'actions est arrondi à l'entier inférieur, le reste du montant reste en cash. Plusieurs actions cochées : le montant s'applique à chacune.
            </span>
          </div>
          <Disclaimer />
        </section>
      </div>

      {toConfirm && (
        <ConfirmDialog
          result={toConfirm}
          cash={simulation.cash_disponible}
          submitting={submitting}
          onCancel={() => setToConfirm(null)}
          onConfirm={onConfirm}
        />
      )}
    </div>
  )
}

import { Info } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { eur, integer } from '../lib/format'
import Button from './ui/Button'
import DecisionBadge from './ui/DecisionBadge'

// ConfirmDialog (UI §4.4, maquette 04) : récapitulatif de l'opération avant enregistrement.
// « Annuler » ferme la fenêtre et laisse le simulateur tel quel.
export default function ConfirmDialog({ result, cash, submitting, onCancel, onConfirm }) {
  const cancelRef = useRef(null)
  useEffect(() => {
    cancelRef.current?.focus()
    const onKey = (event) => event.key === 'Escape' && !submitting && onCancel()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel, submitting])

  const isBuy = result.operation === 'ACHAT'
  const cashAfter = isBuy ? cash - result.montant_reel_investi : cash + result.montant_reel_investi
  const rows = [
    ['Action', `${result.nom} · ${result.ticker}`],
    ['Opération', isBuy ? 'Achat' : 'Vente'],
    ["Nombre d'actions", integer(result.quantite_entiere)],
    ['Cours retenu', eur(result.cours_actuel)],
    ["Montant de l'opération", eur(result.montant_reel_investi)],
    ["Cash après l'opération", eur(cashAfter)],
  ]
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4" role="presentation">
      <div role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-[480px] rounded-lg bg-card p-6 shadow-[var(--shadow-dialog)]">
        <div className="flex items-start justify-between gap-3">
          <h2 id="confirm-title">{isBuy ? "Confirmer l'achat" : 'Confirmer la vente'}</h2>
          <DecisionBadge decision={result.conseil} />
        </div>
        <p className="mt-3 mb-4 text-muted">Vérifiez l'opération avant de l'enregistrer dans votre portefeuille.</p>
        <dl className="m-0">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4 border-b border-line py-2.5">
              <dt className="text-muted">{label}</dt>
              <dd className="num m-0 text-right font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-4 flex gap-3 rounded-md bg-sunken p-3 text-[13px] leading-[18px]">
          <Info className="mt-px size-4 flex-none text-brand" strokeWidth={1.75} aria-hidden="true" />
          <span>Le cours et votre cash seront revérifiés au moment de l'enregistrement. Si le cours a changé, vous devrez relancer la simulation.</span>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <Button ref={cancelRef} onClick={onCancel} disabled={submitting}>Annuler</Button>
          <Button variant={isBuy ? 'buy' : 'sell'} onClick={onConfirm} disabled={submitting}>
            {submitting ? 'Envoi…' : isBuy ? "Valider l'achat" : 'Valider la vente'}
          </Button>
        </div>
      </div>
    </div>
  )
}

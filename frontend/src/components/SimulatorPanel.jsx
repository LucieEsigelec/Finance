import { eur } from '../lib/format'
import { STOCKS } from '../lib/stocks'
import Button from './ui/Button'
import StockCheckbox from './ui/StockCheckbox'

// SimulatorPanel (fichier du squelette, D-02) : le formulaire « Votre opération » de la page
// Simulateur (UI §4.4). Une ligne par action : la case à cocher et, à côté, le montant que le
// client veut investir (ou vendre) sur cette action (D-14). En bas, le total de l'opération
// comparé au cash disponible. Le panneau ne fait aucun appel : la page reçoit la demande.
export default function SimulatorPanel({ amounts, onAmount, selected, onToggle, operation, onOperation, errors, total, cash, onSimulate, loading }) {
  const isBuy = operation === 'ACHAT'
  const over = isBuy && cash !== undefined && cash !== null && total > cash
  return (
    <form
      className="card flex flex-col gap-4 p-4"
      onSubmit={(event) => {
        event.preventDefault()
        onSimulate()
      }}
      noValidate
    >
      <div>
        <h2>Votre opération</h2>
        <p className="mt-1 mb-0 text-[13px] text-muted">Cochez une ou plusieurs actions et indiquez un montant pour chacune. Rien n'est enregistré avant votre validation.</p>
      </div>

      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-2 text-[13px] font-semibold">Opération</legend>
        <div className="grid grid-cols-2 gap-1 rounded-md bg-sunken p-1" role="radiogroup">
          {[['ACHAT', 'Achat'], ['VENTE', 'Vente']].map(([value, label]) => (
            <label
              key={value}
              className={`flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md ${operation === value ? 'bg-card font-semibold shadow-[var(--shadow-card)]' : 'text-muted'}`}
            >
              <input type="radio" name="operation" value={value} checked={operation === value} onChange={() => onOperation(value)} className="accent-[var(--brand)]" />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="sr-only">Actions et montants</legend>
        <div className="grid grid-cols-[1fr_140px] gap-2 text-[13px] font-semibold" aria-hidden="true">
          <span>Actions</span>
          <span className="text-right">{isBuy ? 'Montant à investir' : 'Montant à vendre'}</span>
        </div>
        {STOCKS.map((stock) => {
          const checked = selected.includes(stock.ticker)
          const error = errors[stock.ticker]
          return (
            <div key={stock.ticker} className="flex flex-col gap-1">
              <div className="grid grid-cols-[1fr_140px] items-center gap-2">
                <StockCheckbox name={stock.nom} ticker={stock.ticker} color={stock.color} checked={checked} onChange={() => onToggle(stock.ticker)} />
                <div
                  className={`flex h-10 items-center rounded-md border bg-card px-3 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-brand ${error ? 'border-sell' : 'border-line-strong'} ${checked ? '' : 'opacity-60'}`}
                >
                  <input
                    aria-label={`Montant pour ${stock.nom}`}
                    inputMode="decimal"
                    placeholder="0"
                    value={amounts[stock.ticker] || ''}
                    onChange={(e) => onAmount(stock.ticker, e.target.value)}
                    aria-invalid={error ? 'true' : undefined}
                    className="num min-w-0 flex-1 border-0 bg-transparent text-right text-ink outline-none"
                  />
                  <span className="ml-2 text-muted">€</span>
                </div>
              </div>
              {error && <div role="alert" className="text-right text-[13px] font-medium text-sell">{error}</div>}
            </div>
          )
        })}
      </fieldset>

      <section aria-label="Total de l'opération" className="rounded-md bg-sunken p-3">
        <div className="flex items-baseline justify-between">
          <span className="label-caps">Total {isBuy ? 'à investir' : 'à vendre'}</span>
          <span className="num text-[18px] font-semibold">{eur(total)}</span>
        </div>
        <div className="mt-1 flex justify-between text-[13px] text-muted">
          <span>Cash disponible</span>
          <span className="num">{eur(cash)}</span>
        </div>
        {isBuy && (
          <div className={`flex justify-between text-[13px] ${over ? 'font-medium text-sell' : 'text-muted'}`}>
            <span>{over ? 'Dépassement du cash' : 'Cash restant (au plus)'}</span>
            <span className="num">{eur(over ? total - cash : cash - total)}</span>
          </div>
        )}
        {over && <p className="mt-2 mb-0 text-[13px] text-sell">Le total dépasse votre cash : les dernières lignes seront refusées.</p>}
      </section>

      <div>
        <Button type="submit" variant="primary" disabled={loading}>{loading ? 'Calcul…' : 'Simuler'}</Button>
      </div>
    </form>
  )
}

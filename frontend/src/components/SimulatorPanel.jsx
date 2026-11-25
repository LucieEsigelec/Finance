import AmountInput from './ui/AmountInput'
import Button from './ui/Button'
import StockCheckbox from './ui/StockCheckbox'
import { STOCKS } from '../lib/stocks'

// SimulatorPanel (fichier du squelette, D-02) : le formulaire « Votre opération » de la page
// Simulateur — cases des 5 actions, Achat / Vente, montant, bouton Simuler (UI §4.4).
// Il ne fait aucun appel : la page reçoit la demande par onSimulate.
export default function SimulatorPanel({ selected, onToggle, operation, onOperation, amount, onAmount, amountError, cash, onSimulate, loading }) {
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
        <p className="mt-1 mb-0 text-[13px] text-muted">Rien n'est enregistré avant votre validation.</p>
      </div>

      <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
        <legend className="mb-2 text-[13px] font-semibold">Actions</legend>
        {STOCKS.map((stock) => (
          <StockCheckbox
            key={stock.ticker}
            name={stock.nom}
            ticker={stock.ticker}
            color={stock.color}
            checked={selected.includes(stock.ticker)}
            onChange={() => onToggle(stock.ticker)}
          />
        ))}
      </fieldset>

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

      <AmountInput
        id="montant"
        label={operation === 'ACHAT' ? 'Montant à investir' : 'Montant à vendre'}
        value={amount}
        onChange={(event) => onAmount(event.target.value)}
        cash={cash}
        error={amountError}
      />

      <div>
        <Button type="submit" variant="primary" disabled={loading}>{loading ? 'Calcul…' : 'Simuler'}</Button>
      </div>
    </form>
  )
}

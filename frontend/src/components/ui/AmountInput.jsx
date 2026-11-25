import { eur } from '../../lib/format'

// AmountInput — charte composants/AmountInput.md : saisie alignée à droite, « € » fixe,
// aide = cash disponible, remplacée par l'erreur (en sell) ; bordure line-strong.
export default function AmountInput({ id = 'montant', label = 'Montant', value, onChange, cash, error, unit = '€', inputMode = 'decimal', placeholder = '0' }) {
  return (
    <div className="flex max-w-80 flex-col gap-1">
      <label htmlFor={id} className="text-[13px] leading-[18px] font-semibold">{label}</label>
      <div
        className={`flex h-10 items-center rounded-md border bg-card px-3 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-brand ${error ? 'border-sell' : 'border-line-strong'}`}
      >
        <input
          id={id}
          inputMode={inputMode}
          value={value}
          placeholder={placeholder}
          onChange={onChange}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={`${id}-aide`}
          className="num min-w-0 flex-1 border-0 bg-transparent text-right text-ink outline-none"
        />
        {unit && <span className="ml-2 text-muted">{unit}</span>}
      </div>
      {error ? (
        <div id={`${id}-aide`} role="alert" className="text-[13px] leading-[18px] font-medium text-sell">{error}</div>
      ) : cash !== undefined && cash !== null ? (
        <div id={`${id}-aide`} className="text-[13px] leading-[18px] text-muted">Cash disponible : {eur(cash)}</div>
      ) : null}
    </div>
  )
}

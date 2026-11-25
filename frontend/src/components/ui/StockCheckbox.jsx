// StockCheckbox — charte composants/StockCheckbox.md : pastille de la couleur du titre,
// cochée = fond brand-soft + bordure brand ; toute la ligne est cliquable (label).
export default function StockCheckbox({ name, ticker, color = 'brand', checked = false, onChange }) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 ${checked ? 'border-brand bg-brand-soft' : 'border-line bg-card hover:bg-sunken'}`}
    >
      <input type="checkbox" checked={checked} onChange={onChange} className="m-0 size-[18px] accent-[var(--brand)]" />
      <span className="size-2 flex-none rounded-full" style={{ background: `var(--${color})` }} aria-hidden="true" />
      <span className="flex-1 font-medium">{name}</span>
      <span className="ticker">{ticker}</span>
    </label>
  )
}

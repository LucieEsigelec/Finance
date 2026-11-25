// DecisionBadge — charte composants/DecisionBadge.md : toujours le signe ET le mot
// (daltonisme), fond -soft ; RIEN est gris, pas orange.
const STYLES = {
  ACHAT: { glyph: '▲', cls: 'bg-buy-soft text-buy' },
  VENTE: { glyph: '▼', cls: 'bg-sell-soft text-sell' },
  RIEN: { glyph: '■', cls: 'bg-hold-soft text-hold' },
}

export default function DecisionBadge({ decision, size = 'md' }) {
  if (!decision) return <span className="text-muted">—</span>
  const { glyph, cls } = STYLES[decision] || STYLES.RIEN
  const sizing = size === 'lg' ? 'text-[14px] leading-5 px-3 py-1.5' : 'text-[12px] leading-4 px-2 py-1'
  return (
    <span className={`inline-flex items-center gap-1 rounded-sm font-bold tracking-[.04em] whitespace-nowrap ${sizing} ${cls}`}>
      <span aria-hidden="true">{glyph}</span>
      {decision}
    </span>
  )
}

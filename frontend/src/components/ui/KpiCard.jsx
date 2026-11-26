import { pct, trendArrow, trendClass } from '../../lib/format'

// KpiCard — charte composants/KpiCard.md : reçoit une valeur DÉJÀ formatée ;
// la variation porte son signe et sa flèche, verte si positive, rouge si négative.
export default function KpiCard({ label, value, delta, deltaLabel, hint, valueClassName = '' }) {
  let deltaLine = null
  if (delta !== undefined && delta !== null) {
    const cls = trendClass(delta)
    const arrow = trendArrow(delta)
    deltaLine = <div className={`num mt-1 text-[13px] leading-[18px] font-semibold ${cls}`}>{arrow}{pct(delta)}{deltaLabel ? ` ${deltaLabel}` : ''}</div>
  } else if (hint) {
    deltaLine = <div className="num mt-1 text-[13px] leading-[18px] font-semibold text-muted">{hint}</div>
  }
  return (
    <div className="card p-4">
      <div className="label-caps">{label}</div>
      <div className={`num mt-2 text-[28px] leading-[34px] font-semibold tracking-[-.01em] ${valueClassName}`}>{value}</div>
      {deltaLine}
    </div>
  )
}

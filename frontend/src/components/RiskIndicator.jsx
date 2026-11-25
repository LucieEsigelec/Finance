import { pct, trendClass } from '../lib/format'

// RiskIndicator (UI §4.3) : jauge de la perte de la semaine avec repères à −7 % et −10 %.
export default function RiskIndicator({ variation, level }) {
  const loss = Math.max(0, -(variation || 0))
  const width = Math.min(100, (loss / 12) * 100)
  const color = level === 'ATTEINT' ? 'bg-sell' : level === 'APPROCHE' ? 'bg-warn' : 'bg-buy'
  const text = level === 'ATTEINT' ? 'Limite atteinte' : level === 'APPROCHE' ? 'Proche de la limite' : loss > 0 ? 'Perte limitée' : 'Aucune perte cette semaine'
  return (
    <div className="card w-full p-4 sm:w-80">
      <div className="flex items-baseline justify-between">
        <span className="label-caps">Perte de la semaine</span>
        <span className={`num font-semibold ${trendClass(variation)}`}>{pct(variation)}</span>
      </div>
      <div className="relative mt-3 h-2 rounded-full bg-sunken" role="meter" aria-valuemin={0} aria-valuemax={12} aria-valuenow={loss} aria-label="Perte de la semaine">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${width}%` }} />
        <div className="absolute -top-1 h-4 w-0.5 bg-warn" style={{ left: `${(7 / 12) * 100}%` }} title="−7 %" />
        <div className="absolute -top-1 h-4 w-0.5 bg-sell" style={{ left: `${(10 / 12) * 100}%` }} title="−10 %" />
      </div>
      <div className="mt-2 flex justify-between text-[13px] text-muted">
        <span>{text}</span>
        <span>−7 % · −10 %</span>
      </div>
    </div>
  )
}

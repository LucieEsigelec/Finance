import { eurSigned, pct, trendClass } from '../../lib/format'

// ForecastBar — charte composants/ForecastBar.md : toujours les 3 scénarios, dans l'ordre
// défavorable / central / favorable ; central sur fond brand-soft ; euros si fournis.
export default function ForecastBar({ defavorable, central, favorable, euros }) {
  const cells = [
    ['Défavorable', defavorable, euros?.defavorable, false],
    ['Central', central, euros?.central, true],
    ['Favorable', favorable, euros?.favorable, false],
  ]
  return (
    <div className="grid grid-cols-3 gap-2">
      {cells.map(([name, value, amount, highlight]) => (
        <div key={name} className={`rounded-md px-3 py-2 ${highlight ? 'bg-brand-soft' : 'bg-sunken'}`}>
          <div className="label-caps">{name}</div>
          <div className={`num text-[18px] leading-[26px] font-semibold ${trendClass(value)}`}>{pct(value)}</div>
          {amount !== undefined && amount !== null && (
            <div className="num text-[13px] leading-[18px] text-muted">{eurSigned(amount)}</div>
          )}
        </div>
      ))}
    </div>
  )
}

import { useNavigate } from 'react-router-dom'
import { eur, integer, pct, trendClass } from '../lib/format'
import { COLOR_BY_TICKER } from '../lib/stocks'
import DecisionBadge from './ui/DecisionBadge'

// StocksTable (UI §4.3) : les 5 actions ; un clic sur une ligne ouvre la fiche.
export default function StocksTable({ actions }) {
  const navigate = useNavigate()
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] border-collapse text-left">
        <thead>
          <tr className="border-b border-line">
            {['Action', 'Cours', 'Jour', 'Détenues', 'Conseil', 'Prévision semaine', 'Dividende / an'].map((h, i) => (
              <th key={h} className={`label-caps px-4 py-3 ${i === 0 || i === 4 ? 'text-left' : 'text-right'}`}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {actions.map((a) => (
            <tr
              key={a.ticker}
              onClick={() => navigate(`/action/${a.ticker}`)}
              onKeyDown={(e) => e.key === 'Enter' && navigate(`/action/${a.ticker}`)}
              tabIndex={0}
              className="cursor-pointer border-b border-line last:border-0 hover:bg-sunken"
            >
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="size-2 flex-none rounded-full" style={{ background: `var(--${COLOR_BY_TICKER[a.ticker]})` }} aria-hidden="true" />
                  <div>
                    <div className="font-medium">{a.nom}</div>
                    <div className="ticker">{a.ticker}</div>
                  </div>
                </div>
              </td>
              <td className="num px-4 py-3 text-right font-medium">{eur(a.cours)}</td>
              <td className={`num px-4 py-3 text-right font-medium ${trendClass(a.variation_jour_pct)}`}>{pct(a.variation_jour_pct)}</td>
              <td className="num px-4 py-3 text-right">{a.detenues ? integer(a.detenues) : '—'}</td>
              <td className="px-4 py-3"><DecisionBadge decision={a.conseil} /></td>
              <td className={`num px-4 py-3 text-right font-medium ${trendClass(a.prevision_semaine_pct?.central)}`}>
                {a.prevision_semaine_pct ? pct(a.prevision_semaine_pct.central) : '—'}
              </td>
              <td className="num px-4 py-3 text-right text-muted">{a.dividende_estime_eur ? eur(a.dividende_estime_eur) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

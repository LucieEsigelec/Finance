import { eur, integer } from '../../lib/format'
import { VERDICTS } from '../../lib/verdicts'
import DecisionBadge from './DecisionBadge'
import ForecastBar from './ForecastBar'

// AdviceCard — charte composants/AdviceCard.md : ordre fixe — nom et conseil, verdict,
// chiffres, prévision, raisons (2 à 4, RG-03), boutons en bas.
export default function AdviceCard({ result, children }) {
  const [verdictText, verdictClass] = VERDICTS[result.verdict] || VERDICTS.NE_RIEN_FAIRE
  const isBuy = result.operation === 'ACHAT'
  return (
    <article className="card flex flex-col gap-4 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="m-0 text-[18px] leading-[26px] font-semibold">{result.nom}</h3>
          <div className="ticker">{result.ticker} · {eur(result.cours_actuel)}</div>
        </div>
        <DecisionBadge decision={result.conseil} size="lg" />
      </div>
      <div className={`font-semibold ${verdictClass}`}>{verdictText}</div>
      <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-2">
        <Fact label="Actions" value={integer(result.quantite_entiere)} />
        <Fact label={isBuy ? 'Montant investi' : 'Montant encaissé'} value={eur(result.montant_reel_investi)} />
        <Fact label={isBuy ? 'Reste en cash' : 'Montant non vendu'} value={eur(result.reliquat_cash)} />
        <Fact label={isBuy ? 'Dividende estimé / an' : 'Dividende perdu / an'} value={eur(result.dividende_annuel_estime_eur)} />
      </dl>
      {result.prevision_semaine_pct ? (
        <div>
          <div className="label-caps mb-2">Prévision de la semaine</div>
          <ForecastBar {...result.prevision_semaine_pct} euros={result.quantite_entiere ? result.prevision_semaine_eur : null} />
        </div>
      ) : (
        <p className="m-0 text-[13px] text-muted">Prévision indisponible : moins de 6 mois d'historique.</p>
      )}
      {result.raisons?.length > 0 && (
        <div>
          <div className="label-caps mb-2">Pourquoi ce conseil</div>
          <ul className="m-0 flex list-disc flex-col gap-1 pl-5">
            {result.raisons.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
      )}
      {children}
    </article>
  )
}

function Fact({ label, value }) {
  return (
    <div>
      <dt className="text-[13px] leading-[18px] text-muted">{label}</dt>
      <dd className="num m-0 font-semibold">{value}</dd>
    </div>
  )
}

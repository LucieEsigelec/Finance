import { TriangleAlert } from 'lucide-react'
import { pct } from '../../lib/format'

// AlertBanner — charte composants/AlertBanner.md (RG-01) : rien si AUCUN ; orange à −7 % ;
// rouge plein à −10 % (seul fond rouge plein de l'application). Ne se ferme pas.
export default function AlertBanner({ level, variation }) {
  if (!level || level === 'AUCUN') return null
  const reached = level === 'ATTEINT'
  return (
    <div
      role={reached ? 'alert' : 'status'}
      className={`flex items-start gap-3 rounded-md px-4 py-3 ${reached ? 'bg-sell text-on-sell' : 'bg-warn-soft text-ink'}`}
    >
      <TriangleAlert className={`mt-px size-5 flex-none ${reached ? '' : 'text-warn'}`} strokeWidth={1.75} aria-hidden="true" />
      <div>
        {reached ? (
          <>
            <strong className="font-bold">Limite de perte atteinte : {pct(variation)} cette semaine.</strong> La vente est conseillée sur les positions en baisse.
          </>
        ) : (
          <>
            <strong className="font-bold">Perte de la semaine : {pct(variation)}.</strong> Vous approchez de la limite de −10 % : aucun achat n'est conseillé.
          </>
        )}
      </div>
    </div>
  )
}

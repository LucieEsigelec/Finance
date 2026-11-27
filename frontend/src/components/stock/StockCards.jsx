import { ArrowLeftRight, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { eur, eurKpi, integer, note, pct, pctPlain, trendClass } from '../../lib/format'
import AmountInput from '../ui/AmountInput'
import DecisionBadge from '../ui/DecisionBadge'
import ForecastBar from '../ui/ForecastBar'

// Cartes de la fiche action (UI §4.5, maquettes 06 et 07).

/** Conseil de la semaine : badge, note sur 100 avec les seuils 40 / 60, 2 à 4 raisons (RG-03). */
export function RecommendationCard({ conseil }) {
  const position = Math.max(0, Math.min(100, conseil.note ?? 50))
  return (
    <section className="card flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <h2>Conseil de la semaine</h2>
        <DecisionBadge decision={conseil.decision} />
      </div>
      <div>
        <div className="flex justify-between text-[13px] text-muted">
          <span>Vente ≤ {conseil.seuil_vente}</span>
          <span className="num font-semibold text-ink">{note(conseil.note)}</span>
          <span>Achat ≥ {conseil.seuil_achat}</span>
        </div>
        <div className="relative mt-1 flex h-2 overflow-hidden rounded-full" aria-label={`Note ${note(conseil.note)} sur 100`} role="img">
          <div className="bg-sell-soft" style={{ width: `${conseil.seuil_vente}%` }} />
          <div className="bg-hold-soft" style={{ width: `${conseil.seuil_achat - conseil.seuil_vente}%` }} />
          <div className="flex-1 bg-buy-soft" />
        </div>
        <div className="relative h-0">
          <div className="absolute -top-3 h-4 w-1 -translate-x-1/2 rounded-full bg-ink" style={{ left: `${position}%` }} />
        </div>
        <p className="mt-3 mb-0 text-[13px] text-muted">Note {note(conseil.note)} / 100 · confiance {conseil.confiance ?? '—'}</p>
      </div>
      <ul className="m-0 flex list-disc flex-col gap-2 pl-5">
        {conseil.raisons.map((reason) => <li key={reason}>{reason}</li>)}
      </ul>
    </section>
  )
}

/** Prévision de la semaine : 3 scénarios en % et en euros sur la position détenue. */
export function ForecastCard({ prevision }) {
  return (
    <section className="card flex flex-col gap-3 p-4">
      <div>
        <h2>Prévision de la semaine</h2>
        <p className="mt-1 mb-0 text-[13px] text-muted">
          {prevision.eur ? `Sur votre position de ${eur(prevision.valeur_position)}` : 'Vous ne détenez pas ce titre : variations en % seulement.'}
        </p>
      </div>
      {prevision.pct ? (
        <ForecastBar {...prevision.pct} euros={prevision.eur} />
      ) : (
        <p className="m-0 text-muted">Prévision indisponible : moins de 6 mois d'historique.</p>
      )}
      <p className="m-0 text-[13px] text-muted">Environ 2 semaines sur 3 se terminent entre les scénarios défavorable et favorable.</p>
    </section>
  )
}

/** Simulateur de dividende : nombre d'actions saisi → dividende annuel estimé (calcul dans le navigateur). */
export function DividendSimulator({ dividende }) {
  const [shares, setShares] = useState(String(dividende.detenues || ''))
  const count = Number(shares.replace(/[\s  ]/g, ''))
  const valid = Number.isInteger(count) && count >= 0
  const total = valid && dividende.par_action ? Math.round(count * dividende.par_action * 100) / 100 : null
  return (
    <section className="card flex flex-col gap-3 p-4">
      <h2>Simulateur de dividende</h2>
      <AmountInput
        id="nb-actions"
        label="Nombre d'actions"
        value={shares}
        onChange={(e) => setShares(e.target.value)}
        unit=""
        inputMode="numeric"
        error={shares && !valid ? 'Saisissez un nombre entier d’actions' : null}
      />
      <div>
        <div className="label-caps">Dividende estimé / an</div>
        <div className="num text-[28px] leading-[34px] font-semibold">{total === null ? '—' : eur(total)}</div>
      </div>
      <p className="m-0 text-[13px] text-muted">
        {dividende.par_action ? `${eur(dividende.par_action)} par action attendu · montant avant impôts.` : 'Dividende non disponible pour ce titre.'}
      </p>
    </section>
  )
}

function scoreTone(score) {
  if (score >= 60) return 'bg-buy-soft text-buy'
  if (score <= 40) return 'bg-sell-soft text-sell'
  return 'bg-hold-soft text-hold'
}

/** Onglet Infos : actualités notées sur 100, les plus importantes d'abord (EF-03). */
export function NewsList({ infos }) {
  return (
    <section className="card flex flex-col gap-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2>Actualités récentes</h2>
        <span className="text-[13px] text-muted">Les plus importantes d'abord · 7 derniers jours</span>
      </div>
      <div className="flex flex-wrap gap-8">
        <div>
          <div className="label-caps">Note informations</div>
          <div className="num text-[24px] font-semibold">{note(infos.note)} / 100</div>
        </div>
        <div>
          <div className="label-caps">Impact récent sur la note finale</div>
          <div className={`num text-[24px] font-semibold ${trendClass(infos.impact_points)}`}>
            {infos.impact_points > 0 ? '+' : ''}{note(infos.impact_points).replace('-', '−')} points
          </div>
        </div>
      </div>
      {infos.actualites.length === 0 && <p className="m-0 text-muted">Aucune actualité récente sur ce titre.</p>}
      <ul className="m-0 flex list-none flex-col p-0">
        {infos.actualites.map((article) => (
          <li key={article.url || article.titre} className="flex gap-4 border-b border-line py-4 last:border-0">
            <div className={`flex size-14 flex-none flex-col items-center justify-center rounded-md ${scoreTone(article.score_impact)}`}>
              <span className="num text-[18px] leading-6 font-semibold">{Math.round(article.score_impact)}</span>
              <span className="text-[11px]">/ 100</span>
            </div>
            <div className="min-w-0">
              <div className="text-[13px] text-muted">{article.age} · {article.source || 'Source inconnue'} · {article.type}</div>
              {article.url ? (
                <a href={article.url} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1 font-semibold text-ink no-underline hover:underline">
                  {article.titre} <ExternalLink className="mt-1 size-3.5 flex-none" strokeWidth={1.75} aria-label="(nouvel onglet)" />
                </a>
              ) : (
                <div className="font-semibold">{article.titre}</div>
              )}
              {article.resume && <p className="mt-1 mb-0 text-muted">{article.resume}</p>}
            </div>
          </li>
        ))}
      </ul>
      <p className="m-0 text-[13px] text-muted">
        Note de 0 (très défavorable) à 100 (très favorable), calculée sur le titre et le résumé de l'article. Les liens ouvrent l'article dans un nouvel onglet.
      </p>
    </section>
  )
}

/** Ratios financiers sur deux exercices. */
export function RatiosTable({ ratios }) {
  const [old, recent] = ratios.exercices.length === 2 ? ratios.exercices : [null, ratios.exercices[0]]
  const md = (value) => (value ? `${(value / 1e9).toFixed(2).replace('.', ',')} Md€` : '—')
  const rows = [
    ["Chiffre d'affaires", md(old?.chiffre_affaires), md(recent?.chiffre_affaires), ratios.evolution.chiffre_affaires_pct],
    ['Dividende par action', old ? eur(old.dividende_par_action) : '—', recent ? eur(recent.dividende_par_action) : '—', ratios.evolution.dividende_par_action_pct],
  ]
  return (
    <section className="card flex flex-col gap-3 p-4">
      <div className="flex items-baseline justify-between">
        <h2>Ratios financiers</h2>
        <span className="text-[13px] text-muted">Note {note(ratios.note)} / 100</span>
      </div>
      {!recent ? (
        <p className="m-0 text-muted">Ratios non disponibles pour ce titre.</p>
      ) : (
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line">
              <th className="label-caps py-2 text-left">Critère</th>
              <th className="label-caps py-2 text-right">{old?.annee ?? ''}</th>
              <th className="label-caps py-2 text-right">{recent.annee}</th>
              <th className="label-caps py-2 text-right">Évolution</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, a, b, evolution]) => (
              <tr key={label} className="border-b border-line">
                <td className="py-3">{label}</td>
                <td className="num py-3 text-right">{a}</td>
                <td className="num py-3 text-right font-semibold">{b}</td>
                <td className={`num py-3 text-right font-semibold ${trendClass(evolution)}`}>{pct(evolution)}</td>
              </tr>
            ))}
            <tr>
              <td className="py-3">Rendement du dividende</td>
              <td className="num py-3 text-right">{old ? pctPlain(old.rendement_pct) : '—'}</td>
              <td className="num py-3 text-right font-semibold">{pctPlain(ratios.rendement_actuel_pct)}</td>
              <td className={`py-3 text-right font-semibold ${trendClass((ratios.rendement_actuel_pct ?? 0) - (ratios.moyenne_rendement_5_pct ?? 0))}`}>
                moyenne des 5 : {pctPlain(ratios.moyenne_rendement_5_pct)}
              </td>
            </tr>
          </tbody>
        </table>
      )}
      <p className="m-0 text-[13px] text-muted">Sources : rapports annuels via yfinance, mis à jour une fois par an. Rendement actuel : dividendes des 12 derniers mois / cours.</p>
    </section>
  )
}

/** Ce qui compte dans le conseil : poids et note de chaque pilier. */
export function PillarWeights({ piliers }) {
  return (
    <section className="card flex flex-col gap-3 p-4">
      <h2>Ce qui compte dans le conseil</h2>
      {piliers.map((p) => (
        <div key={p.cle}>
          <div className="flex justify-between text-[13px]">
            <span className="font-semibold">{p.nom}</span>
            <span className="text-muted">poids {pctPlain(p.poids * 100).replace(',0', '')} · note {note(p.note)}</span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-sunken">
            <div className="h-1.5 rounded-full bg-brand" style={{ width: `${p.poids * 100 * 2.5}%` }} />
          </div>
        </div>
      ))}
      <p className="m-0 text-[13px] text-muted">Le hasard ne peut déplacer la note que de 5 points au plus.</p>
    </section>
  )
}

/** En-tête de la fiche : nom, code, cours, variation, conseil, note, actions détenues. */
/**
 * Raccourci « Acheter / vendre » (D-22) : ouvre le simulateur avec l'action déjà cochée.
 * Mode Vente si le conseil est VENTE et que des actions sont détenues, sinon mode Achat.
 * Rien n'est enregistré ici : le seul chemin d'écriture reste Simuler → Valider → confirmation.
 */
function TradeLink({ entete }) {
  const operation = entete.conseil === 'VENTE' && entete.detenues > 0 ? 'VENTE' : 'ACHAT'
  return (
    <Link
      to={`/simulateur?action=${encodeURIComponent(entete.ticker)}&operation=${operation}`}
      title={`Simuler un achat ou une vente de ${entete.nom}`}
      className="inline-flex h-8 items-center gap-1.5 rounded-md border border-line-strong bg-card px-3 text-[13px] font-semibold text-brand no-underline hover:bg-brand-soft"
    >
      <ArrowLeftRight className="size-4" strokeWidth={1.75} aria-hidden="true" />
      Acheter / vendre
    </Link>
  )
}

/**
 * Analyse graphique détaillée (D-24) : moyennes mobiles, croisements, supports et résistances.
 * Explication seule : ces éléments n'entrent pas dans la note du conseil (SPEC §3 inchangée).
 */
export function ChartAnalysisCard({ analyse }) {
  if (!analyse) return null
  const levels = [
    ...[...analyse.resistances].reverse().map((lv) => ({ ...lv, kind: 'Résistance' })),
    { niveau: analyse.cours, kind: 'Cours actuel', current: true },
    ...analyse.supports.map((lv) => ({ ...lv, kind: 'Support' })),
  ]
  return (
    <section className="card flex flex-col gap-4 p-4 sm:p-6" aria-labelledby="analyse-graphique-titre">
      <div>
        <h2 id="analyse-graphique-titre" className="m-0">Analyse graphique</h2>
        <p className="mt-1 mb-0 text-[13px] text-muted">
          Lecture des moyennes mobiles et des niveaux clés des 6 derniers mois. Explication seule : elle n'entre pas dans la note du conseil.
        </p>
      </div>
      <ul className="m-0 flex list-disc flex-col gap-1.5 pl-5">
        {analyse.lecture.map((sentence) => <li key={sentence}>{sentence}</li>)}
      </ul>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <div className="label-caps mb-2">Moyennes mobiles</div>
          <table className="w-full border-collapse text-[14px]">
            <thead>
              <tr className="text-left text-[13px] text-muted">
                <th className="pb-1 font-medium">Moyenne</th>
                <th className="pb-1 text-right font-medium">Niveau</th>
                <th className="pb-1 text-right font-medium">Cours par rapport</th>
              </tr>
            </thead>
            <tbody>
              {analyse.moyennes.map((mm) => (
                <tr key={mm.nom} className="border-t border-line">
                  <td className="py-1.5">{mm.libelle}</td>
                  <td className="num py-1.5 text-right">{eur(mm.valeur)}</td>
                  <td className="num py-1.5 text-right">{mm.ecart_pct >= 0 ? 'au-dessus ' : 'en dessous '}{pct(mm.ecart_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <div className="label-caps mb-2">Niveaux clés</div>
          <ul className="m-0 flex list-none flex-col p-0 text-[14px]">
            {levels.map((lv) => (
              <li key={`${lv.kind}-${lv.niveau}`} className={`flex items-baseline justify-between gap-3 border-t border-line py-1.5 ${lv.current ? 'font-semibold text-brand' : ''}`}>
                <span>
                  {lv.kind}
                  {!lv.current && <span className="text-[13px] text-muted">{lv.extreme ? ' · extrême 6 mois' : ` · ${lv.touches} contacts`}</span>}
                </span>
                <span className="num">{eur(lv.niveau)}{!lv.current && <span className="text-muted"> ({pct(lv.ecart_pct)})</span>}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

export function StockHeader({ entete, color }) {
  return (
    <section className="card flex flex-wrap items-center gap-x-10 gap-y-4 p-4 sm:p-6">
      <div className="flex min-w-[240px] flex-1 items-center gap-3">
        <span className="size-3 rounded-full" style={{ background: `var(--${color})` }} aria-hidden="true" />
        <div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h1>{entete.nom}</h1>
            <TradeLink entete={entete} />
          </div>
          <div className="ticker">{entete.ticker} · {entete.place} · {entete.secteur.toLowerCase()}</div>
        </div>
      </div>
      <div className="text-right">
        <div className="num text-[28px] leading-[34px] font-semibold">{eur(entete.cours)}</div>
        <div className={`num text-[13px] font-semibold ${trendClass(entete.variation_jour_pct)}`}>
          {entete.variation_jour_pct > 0 ? '▲ ' : entete.variation_jour_pct < 0 ? '▼ ' : ''}{pct(entete.variation_jour_pct)} aujourd'hui
        </div>
      </div>
      <div className="flex flex-col items-center gap-1">
        <DecisionBadge decision={entete.conseil} size="lg" />
        <span className="text-[13px] text-muted">Note {note(entete.note)} / 100 · confiance {entete.confiance ?? '—'}</span>
      </div>
      <div className="text-right">
        <div className="label-caps">Vous détenez</div>
        <div className="num font-semibold">{entete.detenues ? `${integer(entete.detenues)} actions · ${eurKpi(entete.valeur_position)}` : 'Aucune action'}</div>
      </div>
    </section>
  )
}

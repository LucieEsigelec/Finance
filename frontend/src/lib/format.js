// Formats français de la charte (docs/charte/README.md §2) :
// 49 972,80 € · 503 067 € (grands montants) · +3,2 % · −1,8 % · 1 436 · 25 nov. 2026, 18:02
// Le signe moins est le vrai « − » (U+2212), le « + » est toujours affiché sur les variations.

const eur2 = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2 })
const eur0 = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
const pct1 = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: 'always' })
const pct2 = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'always' })
const pct1Plain = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const int = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 })
const dec1 = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

const minus = (text) => text.replace(/-/g, '−')
const missing = (value) => value === null || value === undefined || Number.isNaN(value)
/** En dessous de 0,005 %, une variation est considérée comme nulle (ni signe, ni couleur). */
const NEGLIGIBLE = 0.005
const NBSP = ' '

/** Montant en euros, 2 décimales. */
export function eur(value) {
  return missing(value) ? '—' : minus(eur2.format(value))
}

/** Grand montant (carte chiffrée) : sans décimales au-delà de 100 000 €. */
export function eurKpi(value) {
  if (missing(value)) return '—'
  return minus((Math.abs(value) >= 100000 ? eur0 : eur2).format(value))
}

/** Montant arrondi à l'euro, avec signe : +1 599 € · −900 € · 0 €. */
export function eurSigned(value) {
  if (missing(value)) return '—'
  const rounded = Math.round(value)
  if (rounded === 0) return minus(eur0.format(0))
  return (rounded > 0 ? '+' : '') + minus(eur0.format(rounded))
}

/** Variation : signe toujours affiché, 1 décimale ; 2 décimales pour les petites variations
 *  (−0,04 % au lieu de « −0,0 % ») ; « 0,00 % » sans signe quand elle est négligeable. */
export function pct(value) {
  if (missing(value)) return '—'
  const abs = Math.abs(value)
  if (abs < NEGLIGIBLE) return `0,00${NBSP}%`
  return `${minus((abs < 0.1 ? pct2 : pct1).format(value))}${NBSP}%`
}

/** Pourcentage sans signe (part investie, poids). */
export function pctPlain(value) {
  return missing(value) ? '—' : `${minus(pct1Plain.format(value))} %`
}

export function integer(value) {
  return missing(value) ? '—' : int.format(value)
}

export function note(value) {
  return missing(value) ? '—' : dec1.format(value)
}

const dateTime = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
const dateShort = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
const dateLong = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

/** 25 nov. 2026, 18:02 */
export function formatDateTime(iso) {
  return iso ? dateTime.format(new Date(iso)).replace(' à ', ', ') : '—'
}

export function formatDate(iso) {
  return iso ? dateShort.format(new Date(iso)) : '—'
}

/** MERCREDI 25 NOVEMBRE 2026 (en-tête de l'accueil) */
export function formatLongDate(date = new Date()) {
  return dateLong.format(date)
}

/** Classe de couleur d'une variation : vert si hausse, rouge si baisse. */
export function trendClass(value) {
  if (missing(value) || Math.abs(value) < NEGLIGIBLE) return 'text-muted'
  return value > 0 ? 'text-buy' : 'text-sell'
}

/** Flèche d'une variation : ▲ hausse, ▼ baisse, rien si négligeable. */
export function trendArrow(value) {
  if (missing(value) || Math.abs(value) < NEGLIGIBLE) return ''
  return value > 0 ? '▲ ' : '▼ '
}

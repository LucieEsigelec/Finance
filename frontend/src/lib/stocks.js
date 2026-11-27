// Les 5 actions du périmètre (CdCF §2.1) et leur couleur fixe dans tous les graphiques (charte §3).
export const STOCKS = [
  { ticker: 'DSY.PA', nom: 'Dassault Systèmes', color: 'chart-dsy' },
  { ticker: 'TTE.PA', nom: 'TotalEnergies', color: 'chart-tte' },
  { ticker: 'CAP.PA', nom: 'Capgemini', color: 'chart-cap' },
  { ticker: 'RMS.PA', nom: 'Hermès', color: 'chart-rms' },
  { ticker: 'AI.PA', nom: 'Air Liquide', color: 'chart-ai' },
]

export const COLOR_BY_TICKER = Object.fromEntries(STOCKS.map((s) => [s.ticker, s.color]))

export const MENTION = "Les conseils sont une aide à la décision, ils ne garantissent pas le succès : vous restez seul décideur."

/** Lit la valeur d'une variable CSS (pour les bibliothèques de graphiques qui n'acceptent pas var()). */
export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim()
}

// Logo PrimeInvest « Prisme » (D-21) : une pierre taillée en 5 facettes de bleu pétrole.
// La qualité « prime » et les facettes d'un portefeuille diversifié. Les couleurs viennent des
// variables --logo-1 à --logo-5 (index.css), qui s'éclaircissent en thème sombre.
const FACETS = [
  ['14,7 24,18 4,18', 'var(--logo-1)'],
  ['14,7 34,7 24,18', 'var(--logo-2)'],
  ['34,7 44,18 24,18', 'var(--logo-3)'],
  ['4,18 24,18 24,43', 'var(--logo-4)'],
  ['24,18 44,18 24,43', 'var(--logo-5)'],
]

export function LogoMark({ className = 'size-7' }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      <g stroke="var(--logo-edge)" strokeWidth="0.8" strokeLinejoin="round">
        {FACETS.map(([points, fill]) => <polygon key={points} points={points} fill={fill} />)}
      </g>
    </svg>
  )
}

/** Emblème + nom en capitales espacées : PRIME en gras, INVEST en normal. */
export default function Logo({ showName = true }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      {showName && (
        <span className="hidden text-[15px] tracking-[.16em] text-ink sm:inline">
          <span className="font-bold">PRIME</span>
          <span className="font-normal">INVEST</span>
        </span>
      )}
    </span>
  )
}

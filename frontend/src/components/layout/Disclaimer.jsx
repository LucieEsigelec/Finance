import { MENTION } from '../../lib/stocks'

// Mention obligatoire sur chaque écran qui affiche un conseil, une prévision ou un dividende (ENF-03).
export default function Disclaimer({ className = '' }) {
  return <p className={`m-0 text-[13px] leading-[18px] text-muted ${className}`}>{MENTION}</p>
}

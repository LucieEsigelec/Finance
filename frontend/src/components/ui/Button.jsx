// Button — charte composants/Button.md : verbe en tête, primary une seule fois par écran,
// buy / sell uniquement dans la fenêtre de confirmation, 40 px (32 px en taille sm).
const VARIANTS = {
  primary: 'bg-brand text-on-brand border-transparent hover:opacity-90',
  secondary: 'bg-card text-ink border-line-strong hover:bg-sunken',
  ghost: 'bg-transparent text-brand border-transparent hover:bg-brand-soft',
  buy: 'bg-buy text-on-buy border-transparent hover:opacity-90',
  sell: 'bg-sell text-on-sell border-transparent hover:opacity-90',
}

export default function Button({ variant = 'secondary', size = 'md', className = '', type = 'button', children, ...rest }) {
  const height = size === 'sm' ? 'h-8 px-3 text-[13px]' : 'h-10 px-4 text-[15px]'
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-md border font-semibold whitespace-nowrap transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${height} ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}

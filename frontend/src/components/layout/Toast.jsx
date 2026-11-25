import { X } from 'lucide-react'

// Toast : succès sur fond carte, erreur sur fond sell-soft (charte §7.8).
export default function Toast({ toast, onClose }) {
  if (!toast) return null
  const error = toast.tone === 'error'
  return (
    <div className="fixed inset-x-0 bottom-6 z-50 flex justify-center px-4" aria-live="polite">
      <div
        role={error ? 'alert' : 'status'}
        className={`flex max-w-xl items-start gap-3 rounded-md border px-4 py-3 shadow-[var(--shadow-dialog)] ${error ? 'border-sell bg-sell-soft text-ink' : 'border-line bg-card text-ink'}`}
      >
        <span className={error ? 'font-semibold text-sell' : 'font-semibold text-buy'}>{error ? 'Erreur' : 'C’est fait'}</span>
        <span>{toast.message}</span>
        <button type="button" onClick={onClose} aria-label="Fermer le message" className="ml-2 text-muted hover:text-ink">
          <X className="size-4" strokeWidth={1.75} />
        </button>
      </div>
    </div>
  )
}

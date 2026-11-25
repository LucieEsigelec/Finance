import Button from '../ui/Button'

// Message d'erreur et bouton Réessayer (UI §5.1, §6.4).
export default function ErrorState({ error, onRetry, title = 'Les données ne sont pas disponibles' }) {
  return (
    <div className="card flex flex-col items-start gap-3 p-6" role="alert">
      <h2>{title}</h2>
      <p className="m-0 text-muted">{error?.message || 'Une erreur est survenue.'}</p>
      {onRetry && <Button onClick={onRetry}>Réessayer</Button>}
    </div>
  )
}

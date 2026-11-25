// Squelette de chargement à la forme du contenu (charte §7.8).
export default function LoadingState({ rows = 3 }) {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Chargement">
      <div className="skeleton h-8 w-64" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-28" />)}
      </div>
      {Array.from({ length: rows }, (_, i) => <div key={i} className="skeleton h-16" />)}
    </div>
  )
}

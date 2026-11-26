import { Monitor, Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import Disclaimer from '../components/layout/Disclaimer'
import ErrorState from '../components/layout/ErrorState'
import LoadingState from '../components/layout/LoadingState'
import Button from '../components/ui/Button'
import DecisionBadge from '../components/ui/DecisionBadge'
import { useDashboard } from '../context/DashboardContext'
import { useTheme } from '../context/ThemeContext'
import { useToast } from '../context/ToastContext'
import { note as fmtNote } from '../lib/format'

// Profil (/profil) — D-17 : le client choisit son profil de risque, qui règle les seuils des
// conseils (Prudent 60 / 40, Équilibré 55 / 45, Dynamique 50 / 40), et le thème clair / sombre.

/** Combien d'actions seraient à ACHAT / RIEN / VENTE avec ces seuils et les notes actuelles. */
function preview(notes, achat, vente) {
  const counts = { ACHAT: 0, RIEN: 0, VENTE: 0 }
  Object.values(notes).forEach((n) => {
    if (n === null || n === undefined) return
    counts[n >= achat ? 'ACHAT' : n <= vente ? 'VENTE' : 'RIEN'] += 1
  })
  return counts
}

const THEMES = [
  ['clair', 'Clair', Sun],
  ['sombre', 'Sombre', Moon],
  ['systeme', "Comme l'ordinateur", Monitor],
]

export default function ProfilePage() {
  const toast = useToast()
  const { reload } = useDashboard()
  const { choice, choose } = useTheme()
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [selected, setSelected] = useState(null)
  const [saving, setSaving] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let alive = true
    api.profile()
      .then((data) => {
        if (!alive) return
        setState({ data, error: null, loading: false })
        setSelected(data.profil.id)
      })
      .catch((error) => alive && setState({ data: null, error, loading: false }))
    return () => {
      alive = false
    }
  }, [attempt])

  if (state.loading && !state.data) return <LoadingState rows={3} />
  if (state.error) return <ErrorState error={state.error} onRetry={() => setAttempt((n) => n + 1)} />

  const { data } = state
  const saved = data.profil.id

  async function save() {
    setSaving(true)
    try {
      const response = await api.setProfile(selected)
      toast(response.message)
      setState((s) => ({ ...s, data: { ...s.data, profil: response.profil } }))
      await reload() // les conseils de tous les écrans suivent le nouveau profil
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1>Profil</h1>
        <p className="mt-1 mb-0 text-[13px] text-muted">
          {data.nom_client || 'Client'} · réglez votre profil de risque et l'apparence de l'application.
        </p>
      </div>

      <section className="card flex flex-col gap-4 p-4 sm:p-6" aria-labelledby="titre-risque">
        <div>
          <h2 id="titre-risque">Votre profil de risque</h2>
          <p className="mt-1 mb-0 text-muted">
            Chaque action reçoit une note sur 100. Votre profil décide à partir de quelle note l'application vous conseille
            d'acheter ou de vendre. Les notes ne changent pas : seuls les seuils bougent.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3" role="radiogroup" aria-labelledby="titre-risque">
          {data.profils.map((p) => {
            const active = selected === p.id
            const counts = preview(data.notes, p.seuil_achat, p.seuil_vente)
            return (
              <label
                key={p.id}
                className={`flex cursor-pointer flex-col gap-3 rounded-lg border p-4 ${active ? 'border-brand bg-brand-soft' : 'border-line bg-card hover:bg-sunken'}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-[18px] font-semibold">
                    <input type="radio" name="profil" value={p.id} checked={active} onChange={() => setSelected(p.id)} className="accent-[var(--brand)]" />
                    {p.nom}
                  </span>
                  {saved === p.id && <span className="rounded-sm bg-buy-soft px-2 py-0.5 text-[12px] font-semibold text-buy">Actuel</span>}
                </div>
                <div className="num text-[13px] font-semibold">
                  Achat si note ≥ {fmtNote(p.seuil_achat)} · Vente si note ≤ {fmtNote(p.seuil_vente)}
                </div>
                <p className="m-0 text-[13px] text-muted">{p.description}</p>
                <div className="mt-auto border-t border-line pt-3">
                  <div className="label-caps mb-2">Avec les notes actuelles</div>
                  <div className="flex flex-wrap gap-2">
                    {['ACHAT', 'RIEN', 'VENTE'].map((d) => (
                      <span key={d} className="flex items-center gap-1 text-[13px]">
                        <DecisionBadge decision={d} /> × {counts[d]}
                      </span>
                    ))}
                  </div>
                </div>
              </label>
            )
          })}
        </div>

        {!data.enregistrable && (
          <p className="m-0 rounded-md bg-warn-soft px-3 py-2 text-[13px]">
            Le profil ne peut pas encore être enregistré : la base doit d'abord être mise à jour (migration 005).
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" onClick={save} disabled={saving || !selected || selected === saved || !data.enregistrable}>
            {saving ? 'Enregistrement…' : 'Enregistrer le profil'}
          </Button>
          <span className="text-[13px] text-muted">
            Profil actuel : {data.profil.nom} (achat ≥ {fmtNote(data.profil.seuil_achat)}, vente ≤ {fmtNote(data.profil.seuil_vente)}).
            Le garde-fou de perte (−10 % par semaine) ne change pas.
          </span>
        </div>
      </section>

      <section className="card flex flex-col gap-4 p-4 sm:p-6" aria-labelledby="titre-apparence">
        <div>
          <h2 id="titre-apparence">Apparence</h2>
          <p className="mt-1 mb-0 text-muted">Le choix est gardé sur cet appareil.</p>
        </div>
        <div className="grid max-w-xl grid-cols-3 gap-2 rounded-md bg-sunken p-1" role="radiogroup" aria-labelledby="titre-apparence">
          {THEMES.map(([value, label, Icon]) => (
            <label
              key={value}
              className={`flex h-10 cursor-pointer items-center justify-center gap-2 rounded-md text-[15px] ${choice === value ? 'bg-card font-semibold shadow-[var(--shadow-card)]' : 'text-muted'}`}
            >
              <input type="radio" name="theme" value={value} checked={choice === value} onChange={() => choose(value)} className="sr-only" />
              <Icon className="size-4" strokeWidth={1.75} aria-hidden="true" />
              {label}
            </label>
          ))}
        </div>
      </section>

      <Disclaimer />
    </div>
  )
}

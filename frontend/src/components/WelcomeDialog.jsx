import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useDashboard } from '../context/DashboardContext'
import { useToast } from '../context/ToastContext'
import { note as fmtNote } from '../lib/format'
import Button from './ui/Button'
import { LogoMark } from './layout/Logo'

// Dialogue de bienvenue (D-18) : à la première connexion, tant qu'aucun profil de risque n'a
// été choisi, l'application demande le nom du client et son profil (Prudent, Équilibré,
// Dynamique). « Plus tard » le referme pour la session ; il reviendra à la prochaine visite.
import { WELCOME_LATER_KEY as LATER_KEY } from './LogoutDialog'

export default function WelcomeDialog() {
  const { data, reload } = useDashboard()
  const toast = useToast()
  const [later, setLater] = useState(() => sessionStorage.getItem(LATER_KEY) === '1')
  const [profiles, setProfiles] = useState([])
  const [name, setName] = useState('')
  const [choice, setChoice] = useState(null)
  const [saving, setSaving] = useState(false)
  const nameRef = useRef(null)
  const open = Boolean(data?.profil?.a_choisir) && !later

  useEffect(() => {
    if (!open) return undefined
    let alive = true
    api.profile()
      .then((result) => {
        if (!alive) return
        setProfiles(result.profils)
        setName((current) => current || result.nom_client || '')
      })
      .catch(() => {})
    nameRef.current?.focus()
    return () => {
      alive = false
    }
  }, [open])

  if (!open) return null

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      await api.setProfile(choice, name.trim())
      toast(`Bienvenue ${name.trim()} : votre profil est enregistré. Vous pourrez le changer dans l'onglet Profil.`)
      await reload()
    } catch (error) {
      toast(error.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  function postpone() {
    sessionStorage.setItem(LATER_KEY, '1')
    setLater(true)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-ink/40 p-4" role="presentation">
      <form
        onSubmit={submit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="bienvenue-titre"
        className="my-auto flex w-full max-w-2xl flex-col gap-5 rounded-lg bg-card p-6 shadow-[var(--shadow-dialog)]"
      >
        <div>
          <LogoMark className="mb-3 size-10" />
          <h2 id="bienvenue-titre" className="text-[24px] leading-8">Bienvenue sur PrimeInvest</h2>
          <p className="mt-2 mb-0 text-muted">
            Avant de commencer, indiquez votre nom et la façon dont vous souhaitez être conseillé. Vous pourrez changer ces
            réglages à tout moment dans l'onglet Profil.
          </p>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="bienvenue-nom" className="text-[13px] font-semibold">Votre nom</label>
          <input
            id="bienvenue-nom"
            ref={nameRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Par exemple : M. Dupont"
            maxLength={80}
            autoComplete="name"
            className="h-10 rounded-md border border-line-strong bg-card px-3 text-ink"
          />
        </div>

        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="mb-2 text-[13px] font-semibold">Votre profil de risque</legend>
          {profiles.length === 0 && <div className="skeleton h-24" aria-busy="true" />}
          {profiles.map((p) => (
            <label
              key={p.id}
              className={`flex cursor-pointer gap-3 rounded-md border p-3 ${choice === p.id ? 'border-brand bg-brand-soft' : 'border-line hover:bg-sunken'}`}
            >
              <input
                type="radio"
                name="bienvenue-profil"
                value={p.id}
                checked={choice === p.id}
                onChange={() => setChoice(p.id)}
                className="mt-1 accent-[var(--brand)]"
              />
              <span>
                <span className="font-semibold">{p.nom}</span>
                <span className="num ml-2 text-[13px] text-muted">
                  achat si note ≥ {fmtNote(p.seuil_achat)} · vente si note ≤ {fmtNote(p.seuil_vente)}
                  {` · alerte au-delà de ${p.seuil_exposition_pct} % du capital par action`}
                </span>
                <span className="mt-1 block text-[13px] text-muted">{p.description}</span>
              </span>
            </label>
          ))}
        </fieldset>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button onClick={postpone} disabled={saving}>Plus tard</Button>
          <Button type="submit" variant="primary" disabled={saving || !choice || !name.trim()}>
            {saving ? 'Enregistrement…' : 'Commencer'}
          </Button>
        </div>
      </form>
    </div>
  )
}

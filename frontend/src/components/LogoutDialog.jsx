import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useToast } from '../context/ToastContext'
import Button from './ui/Button'

// « Se déconnecter » (D-20) : efface le nom et le profil de risque (DELETE /api/profil), puis
// recharge l'application, qui rouvre le dialogue de bienvenue. Le portefeuille, le cash et les
// opérations sont conservés. Il n'y a pas de comptes : la déconnexion vaut pour tout le groupe.
export const WELCOME_LATER_KEY = 'primeinvest-bienvenue-plus-tard'

export default function LogoutDialog({ onClose }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const cancelRef = useRef(null)

  useEffect(() => {
    cancelRef.current?.focus()
    const onKey = (event) => event.key === 'Escape' && !busy && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onClose])

  async function confirm() {
    setBusy(true)
    try {
      await api.logout()
      sessionStorage.removeItem(WELCOME_LATER_KEY)
      window.location.assign('/') // application rechargée : le dialogue de bienvenue s'ouvre
    } catch (error) {
      toast(error.message, 'error')
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4" role="presentation">
      <div role="dialog" aria-modal="true" aria-labelledby="deconnexion-titre" className="w-full max-w-md rounded-lg bg-card p-6 shadow-[var(--shadow-dialog)]">
        <h2 id="deconnexion-titre">Se déconnecter ?</h2>
        <ul className="mt-3 mb-0 flex list-disc flex-col gap-1 pl-5 text-[15px]">
          <li>Votre <strong>nom</strong> et votre <strong>profil de risque</strong> seront effacés.</li>
          <li>Le portefeuille, le cash et l'historique des opérations sont <strong>conservés</strong>.</li>
          <li>Le portefeuille est partagé : la déconnexion vaut pour tous ceux qui l'utilisent.</li>
        </ul>
        <p className="mt-3 mb-0 text-[13px] text-muted">L'application s'ouvrira ensuite sur le dialogue de bienvenue.</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button ref={cancelRef} onClick={onClose} disabled={busy}>Annuler</Button>
          <Button variant="primary" onClick={confirm} disabled={busy}>{busy ? 'Déconnexion…' : 'Se déconnecter'}</Button>
        </div>
      </div>
    </div>
  )
}

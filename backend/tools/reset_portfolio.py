"""Remet le portefeuille à zéro après des tests : 500 000 € de cash, aucune opération.

En bref : supprime toutes les opérations (achats et ventes) du portefeuille, puis remet le
cash et la valeur de référence de la semaine au capital de départ (500 000 €). Les cours,
actualités et conseils ne sont pas touchés. Le nom et le profil de risque sont gardés, sauf
avec ``--profil``. ATTENTION : la base est partagée par tout le groupe et la suppression est
définitive ; l'outil affiche ce qui va être effacé et demande de taper RESET (D-23).

Lancement depuis ``backend/`` :
    python -m tools.reset_portfolio            # résumé puis confirmation
    python -m tools.reset_portfolio --profil   # efface aussi nom et profil (dialogue de bienvenue)
    python -m tools.reset_portfolio --oui      # sans question (à éviter)
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from services.decision_engine import positions
from services.refresh_service import monday_of

CONFIRMATION = "RESET"


def summary(repo) -> tuple[dict, list]:
    """Portefeuille et opérations actuels (lecture seule)."""
    portfolio = repo.get_portfolio()
    return portfolio, repo.get_transactions(portfolio["id"])


def reset(repo, today: date, clear_profile: bool = False) -> int:
    """Efface les opérations et remet le cash au capital ; renvoie le nombre d'opérations effacées."""
    portfolio = repo.get_portfolio()
    count = repo.reset_investments(portfolio["id"], portfolio["capital_initial"], monday_of(today))
    if clear_profile:
        repo.reset_portfolio_profile(portfolio["id"])
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remet le portefeuille à 500 000 € sans opération.")
    parser.add_argument("--profil", action="store_true", help="efface aussi le nom et le profil de risque")
    parser.add_argument("--oui", action="store_true", help="ne pas demander de confirmation")
    args = parser.parse_args(argv)

    from db.repository import SupabaseRepository  # import tardif : les tests n'ont pas besoin de Supabase
    from db.supabase_client import get_client

    repo = SupabaseRepository(get_client())
    portfolio, transactions = summary(repo)
    held = {t: q for t, q in positions(transactions).items() if q > 0}
    print(f"Portefeuille : {portfolio.get('nom_client') or 'sans nom'} · profil {portfolio.get('profil_risque') or 'non choisi'}")
    print(f"Cash actuel  : {portfolio['cash_disponible']} €  →  {portfolio['capital_initial']} €")
    print(f"Opérations   : {len(transactions)} à supprimer")
    if held:
        print("Positions    : " + ", ".join(f"{t} {q}" for t, q in sorted(held.items())))
    if args.profil:
        print("Nom et profil de risque : effacés (le dialogue de bienvenue rouvrira)")
    print("\nLa base est PARTAGÉE par tout le groupe et la suppression est définitive.")

    if not args.oui and input(f"Tapez {CONFIRMATION} pour confirmer : ").strip() != CONFIRMATION:
        print("Annulé, rien n'a été modifié.")
        return 1

    count = reset(repo, date.today(), clear_profile=args.profil)
    print(f"Fait : {count} opération(s) supprimée(s), cash remis à {portfolio['capital_initial']} €.")
    print("Le site en ligne peut garder l'ancien état jusqu'à 30 s (mémoire courte de l'API).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

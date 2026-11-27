"""GET /api/profil et PUT /api/profil — profil de risque du client (onglet Profil, D-17).

En bref : le client choisit Prudent (achat ≥ 60, vente ≤ 40), Équilibré (55 / 45) ou
Dynamique (50 / 40). Le choix est enregistré dans portefeuille.profil_risque et s'applique
tout de suite à tous les conseils affichés (ils sont relus avec ces seuils). Les notes,
elles, ne changent pas : seul l'endroit où l'on coupe entre ACHAT, RIEN et VENTE bouge.
Le garde-fou de perte (RG-01) ne dépend pas du profil.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

import config
from routers.dashboard import profile_summary
from routers.deps import get_repo
from services.portfolio_service import load_state

router = APIRouter(prefix="/api", tags=["profil"])


class ProfileRequest(BaseModel):
    """Profil de risque, et nom du client à la première connexion (dialogue de bienvenue, D-18)."""

    model_config = ConfigDict(extra="forbid")

    profil: Literal["prudent", "equilibre", "dynamique"]
    nom_client: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("nom_client")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if not value:
            raise ValueError("Saisissez votre nom")
        return value


def _profiles() -> list[dict[str, Any]]:
    return [
        {"id": key, "nom": p["nom"], "seuil_achat": p["achat"], "seuil_vente": p["vente"], "description": p["description"],
         "part_max_action_pct": p.get("part_max_action_pct")}
        for key, p in config.PROFILS_RISQUE.items()
    ]


@router.get("/profil")
def get_profile(repo=Depends(get_repo)) -> dict[str, Any]:
    state = load_state(repo)
    return {
        "nom_client": state.portfolio.get("nom_client"),
        "profil": profile_summary(state),
        "profils": _profiles(),
        "enregistrable": "profil_risque" in state.portfolio,  # False tant que la migration 005 n'est pas faite
        "notes": {t: (s.get("details_piliers") or {}).get("note") for t, s in state.scores.items()},
    }


@router.put("/profil")
def set_profile(request: ProfileRequest, repo=Depends(get_repo)) -> dict[str, Any]:
    state = load_state(repo)
    if "profil_risque" not in state.portfolio:
        raise HTTPException(
            status_code=409,
            detail="Le profil ne peut pas encore être enregistré : la migration 005 de la base n'a pas été exécutée.",
        )
    repo.update_portfolio_profile(state.portfolio["id"], request.profil, nom_client=request.nom_client)
    after = load_state(repo)
    return {
        "message": f"Profil « {config.PROFILS_RISQUE[request.profil]['nom']} » enregistré.",
        "profil": profile_summary(after),
    }


@router.delete("/profil")
def logout(repo=Depends(get_repo)) -> dict[str, Any]:
    """« Se déconnecter » (D-20) : efface le nom et le profil de risque pour revoir le dialogue de
    bienvenue. Le portefeuille, le cash et les opérations sont conservés. Il n'y a pas de comptes :
    le portefeuille est partagé, la déconnexion vaut donc pour tous ceux qui l'utilisent."""
    state = load_state(repo)
    if "profil_risque" not in state.portfolio:
        raise HTTPException(status_code=409, detail="La migration 005 de la base n'a pas été exécutée.")
    repo.reset_portfolio_profile(state.portfolio["id"])
    return {"message": "Vous êtes déconnecté : le nom et le profil de risque ont été effacés."}

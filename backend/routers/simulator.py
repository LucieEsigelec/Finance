"""POST /api/simulate — conseil sur une opération, SANS RIEN ENREGISTRER
(EF-02, RG-03, RG-05, ENF-02, SPEC §10, algorigramme §2.3).

En bref, pour chaque titre coché :
1. on relit le dernier conseil du titre (déjà calculé), le cours, le cash et les
   actions détenues ;
2. on calcule le nombre d'actions entier, le reste en cash et le dividende estimé ;
3. on croise l'opération voulue et le conseil pour donner un verdict ; une opération
   impossible donne le verdict REFUSE avec sa raison (affichée comme un conseil) ;
4. on ajoute la prévision en % et en euros, les raisons et le niveau d'alerte.

Plusieurs titres cochés : le montant s'applique à chacun (D-08).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends

from models.schemas import SimulateRequest
from routers.deps import check_ticker, get_now, get_repo, money
from services.decision_engine import (
    ATTEINT,
    RIEN,
    fmt_eur,
    forecast_euros,
    simulate_operation,
)
from services.portfolio_service import MENTION, load_state, with_alert

router = APIRouter(prefix="/api", tags=["simulateur"])


@router.post("/simulate")
def simulate(request: SimulateRequest, repo=Depends(get_repo), now: datetime = Depends(get_now)) -> dict[str, Any]:
    state = load_state(repo)
    for ticker in request.tickers:
        check_ticker(ticker, state.actions)

    results = []
    for ticker in request.tickers:
        action = state.actions[ticker]
        score = state.scores.get(ticker) or {}
        details = score.get("details_piliers", {})
        conseil = score.get("decision", RIEN)
        price = state.prices[ticker]
        operation = simulate_operation(
            request.operation,
            request.montant_eur,
            price,
            state.cash,
            state.held.get(ticker, 0),
            conseil,
            state.niveau_alerte,
            action.get("dividende_estime"),
        )
        raisons = with_alert(details.get("raisons", []), state.niveau_alerte, state.variation_pct)
        if operation.motif_refus:
            raisons = [operation.motif_refus] + raisons[:3]
        prevision = details.get("prevision")
        scenarios = None if not prevision else {k: prevision[k] for k in ("defavorable", "central", "favorable")}
        results.append(
            {
                "ticker": ticker,
                "nom": action["nom"],
                "cours_actuel": money(price),
                "operation": request.operation,
                "quantite_entiere": operation.quantite,
                "montant_reel_investi": money(operation.montant_reel),
                "reliquat_cash": money(operation.reliquat),
                "conseil": conseil,
                "note": details.get("note"),
                "confiance": details.get("confiance"),
                "verdict": operation.verdict,
                "motif_refus": operation.motif_refus,
                "prevision_semaine_pct": scenarios,
                "prevision_semaine_eur": forecast_euros(scenarios, operation.montant_reel),
                "dividende_annuel_estime_eur": money(operation.dividende),
                "alerte_risque_rg01": state.niveau_alerte == ATTEINT,
                "niveau_alerte": state.niveau_alerte,
                "raisons": raisons,
                "cash_apres_operation": money(
                    state.cash - operation.montant_reel if request.operation == "ACHAT"
                    else state.cash + operation.montant_reel
                ),
                "detenues": state.held.get(ticker, 0),
            }
        )

    total = request.montant_eur * len(request.tickers)
    warning = None
    if request.operation == "ACHAT" and len(request.tickers) > 1 and total > state.cash:
        warning = (
            f"Le total des {len(request.tickers)} opérations ({fmt_eur(total)}) dépasse votre cash "
            f"({fmt_eur(state.cash)}) : chaque opération sera revérifiée au moment de l'enregistrement."
        )
    return {
        "date_conseil": now.isoformat(timespec="seconds"),
        "cash_disponible": money(state.cash),
        "variation_hebdo_pct": round(state.variation_pct, 2),
        "niveau_alerte": state.niveau_alerte,
        "avertissement": warning,
        "resultats": results,
        "mention": MENTION,
        "enregistre": False,
    }


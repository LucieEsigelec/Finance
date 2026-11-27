"""POST /api/simulate — conseil sur une opération, SANS RIEN ENREGISTRER
(EF-02, RG-03, RG-05, ENF-02, SPEC §10, algorigramme §2.3).

En bref, pour chaque titre coché :
1. on relit le dernier conseil du titre (déjà calculé), le cours, le cash et les
   actions détenues ;
2. on calcule le nombre d'actions entier, le reste en cash et le dividende estimé ;
3. on croise l'opération voulue et le conseil pour donner un verdict ; une opération
   impossible donne le verdict REFUSE avec sa raison (affichée comme un conseil) ;
4. on ajoute la prévision en % et en euros, les raisons et le niveau d'alerte.

Chaque action cochée a son propre montant (D-14), en euros ou en nombre d'actions (D-26) ;
pour un achat, le cash est décompté ligne après ligne, et la réponse contient le total.
Un achat qui placerait sur une même action plus que le seuil du profil est signalé par un
avertissement, jamais refusé (D-27).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends

from models.schemas import SimulateRequest
from routers.deps import check_ticker, get_now, get_repo, money
from services.decision_engine import (
    ATTEINT,
    CENT,
    REFUSE,
    Operation,
    RIEN,
    fmt_eur,
    forecast_euros,
    simulate_operation,
)
from services.portfolio_service import MENTION, exposure_check, load_state, with_alert

router = APIRouter(prefix="/api", tags=["simulateur"])


@router.post("/simulate")
def simulate(request: SimulateRequest, repo=Depends(get_repo), now: datetime = Depends(get_now)) -> dict[str, Any]:
    state = load_state(repo)
    for line in request.operations:
        check_ticker(line.ticker, state.actions)

    # Le cash est décompté ligne après ligne : si le total des achats dépasse le cash,
    # les dernières lignes sont refusées avec leur raison (RG-05, D-14).
    available = state.cash
    results = []
    for line in request.operations:
        ticker = line.ticker
        action = state.actions[ticker]
        score = state.scores.get(ticker) or {}
        details = score.get("details_piliers", {})
        conseil = score.get("decision", RIEN)
        price = state.prices[ticker]
        held = state.held.get(ticker, 0)
        # Saisie en nombre d'actions (D-26) : montant exact = quantité × cours, sans reste.
        montant = (price * line.quantite).quantize(CENT) if line.quantite is not None else line.montant_eur
        operation = simulate_operation(
            request.operation,
            montant,
            price,
            available,
            held,
            conseil,
            state.niveau_alerte,
            action.get("dividende_estime"),
        )
        refuse = None
        if line.quantite is not None and request.operation == "VENTE" and 0 < held < line.quantite:
            refuse = f"Vous ne détenez que {held} action{'s' if held > 1 else ''} {action['nom']} : vente impossible."
        exposition = None
        if request.operation == "ACHAT" and operation.verdict != REFUSE:
            exposition = exposure_check(state, ticker, operation.montant_reel)  # avertissement seul (D-27)
        if refuse:
            operation = Operation(0, Decimal("0.00"), Decimal(str(montant)).quantize(CENT), REFUSE, refuse, Decimal("0.00"))
        if operation.verdict != REFUSE:
            available = available - operation.montant_reel if request.operation == "ACHAT" else available + operation.montant_reel
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
                "montant_demande": money(montant),
                "unite": "actions" if line.quantite is not None else "eur",
                "quantite_demandee": line.quantite,
                "exposition": exposition,  # part du capital sur cette action (D-26), achats seulement
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
                # Lecture détaillée du graphique (D-24), calculée à l'actualisation ; None avant
                "analyse_graphique": (details.get("analyse_graphique") or {}).get("lecture"),
                "cash_apres_operation": money(available),
                "detenues": state.held.get(ticker, 0),
            }
        )

    accepted = [r for r in results if r["verdict"] != REFUSE]
    requested = sum((Decimal(r["montant_demande"]) for r in results), Decimal(0))
    refused_for_cash = [r for r in results if r["motif_refus"] and r["motif_refus"].startswith("Vous disposez")]
    warning = None
    if request.operation == "ACHAT" and requested > state.cash:
        warning = (
            f"Le total demandé ({fmt_eur(requested)}) dépasse votre cash ({fmt_eur(state.cash)}) : "
            f"{len(refused_for_cash)} opération(s) refusée(s), dans l'ordre de la liste."
        )
    return {
        "date_conseil": now.isoformat(timespec="seconds"),
        "cash_disponible": money(state.cash),
        "variation_hebdo_pct": round(state.variation_pct, 4),
        "niveau_alerte": state.niveau_alerte,
        "avertissement": warning,
        "resultats": results,
        "total": {
            "montant_demande": money(requested),
            "montant_reel": money(sum((Decimal(str(r["montant_reel_investi"])) for r in accepted), Decimal(0))),
            "reliquat": money(sum((Decimal(str(r["reliquat_cash"])) for r in accepted), Decimal(0))),
            "dividende_annuel": money(sum((Decimal(str(r["dividende_annuel_estime_eur"])) for r in accepted), Decimal(0))),
            "cash_apres": money(available),
            "nb_operations": len(results),
            "nb_refusees": len(results) - len(accepted),
        },
        "mention": MENTION,
        "enregistre": False,
    }

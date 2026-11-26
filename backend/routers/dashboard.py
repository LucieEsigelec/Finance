"""GET /api/dashboard — Accueil, Tableau de bord, en-tête du Simulateur, NavBar,
AlertBanner (EF-01, RG-01, UI §4.2–4.4).

En bref : renvoie en un seul appel la valeur du portefeuille, le cash, la part
investie, la performance de la semaine, le niveau d'alerte, l'horodatage des données
et, pour chacune des 5 actions, le cours, la variation du jour, les actions détenues,
le conseil, la prévision et le dividende estimé.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends

import config
from routers import refresh_control
from routers.deps import get_collector, get_now, get_repo, money
from services.decision_engine import ATTEINT
from services.portfolio_service import MENTION, load_state, week_bounds, with_alert
from services.ratio_scoring import estimated_dividend

router = APIRouter(prefix="/api", tags=["tableau de bord"])


def stock_row(ticker: str, state, include_reasons: bool = True) -> dict[str, Any]:
    action = state.actions[ticker]
    score = state.scores.get(ticker)
    details = (score or {}).get("details_piliers", {})
    held = state.held.get(ticker, 0)
    price = state.prices[ticker]
    dps = action.get("dividende_estime")
    prevision = details.get("prevision")
    row = {
        "ticker": ticker,
        "nom": action["nom"],
        "secteur": action["secteur"],
        "cours": money(price),
        "variation_jour_pct": details.get("variation_jour_pct"),
        "detenues": held,
        "valeur_position": money(Decimal(held) * price),
        "conseil": score["decision"] if score else None,
        "note": details.get("note"),
        "confiance": details.get("confiance"),
        "prevision_semaine_pct": None if not prevision else {
            k: prevision[k] for k in ("defavorable", "central", "favorable")
        },
        "dividende_par_action": money(dps),
        "dividende_estime_eur": money(estimated_dividend(held, dps)) if held else None,
        "date_calcul": score["date_calcul"] if score else None,
    }
    if include_reasons:
        row["raisons"] = with_alert(details.get("raisons", []), state.niveau_alerte, state.variation_pct)
    return row


@router.get("/dashboard")
def dashboard(
    background: BackgroundTasks,
    repo=Depends(get_repo),
    collector=Depends(get_collector),
    now: datetime = Depends(get_now),
) -> dict[str, Any]:
    state = load_state(repo)
    # D-13 : données de plus d'une heure → actualisation lancée en arrière-plan ; la réponse
    # part tout de suite avec les données actuelles, l'interface rechargera à la fin.
    auto = False
    if refresh_control.is_stale(state.date_donnees, now):
        outcome, _ = refresh_control.reserve()
        if outcome == "ok":
            background.add_task(refresh_control.run, repo, collector)
            auto = True
    portfolio = state.portfolio
    capital = portfolio["capital_initial"]
    invested = state.value - state.cash
    monday, friday = week_bounds(now.date())
    dates_calcul = [s["date_calcul"] for s in state.scores.values()]
    return {
        "nom_client": portfolio.get("nom_client"),
        "date_donnees": state.date_donnees,
        "date_conseils": max(dates_calcul) if dates_calcul else None,
        "capital_initial": money(capital),
        "capital_total": money(state.value),
        "cash_disponible": money(state.cash),
        "cash_pct": round(float(state.cash / state.value * 100), 1) if state.value else None,
        "part_investie_pct": round(float(invested / state.value * 100), 1) if state.value else 0.0,
        "variation_depuis_depart_pct": round(float((state.value / capital - 1) * 100), 4),
        "variation_depuis_depart_eur": money(state.value - capital),
        "variation_hebdo_pct": round(state.variation_pct, 4),
        "variation_hebdo_eur": money(state.value - portfolio["val_semaine_prec"]),
        "val_semaine_prec": money(portfolio["val_semaine_prec"]),
        "niveau_alerte": state.niveau_alerte,
        "alerte_perte_10pct": state.niveau_alerte == ATTEINT,
        "seuils_alerte_pct": {"approche": config.ALERTE_APPROCHE_PCT, "atteint": config.ALERTE_ATTEINT_PCT},
        "semaine": {"debut": monday.isoformat(), "fin": friday.isoformat()},
        "nb_titres_detenus": len(state.held),
        "actions": [stock_row(t, state) for t in config.TICKERS if t in state.actions],
        "actualisation": {
            "en_cours": refresh_control.state["en_cours"],
            "lancee_automatiquement": auto,
        },
        "mention": MENTION,
    }

"""POST /api/transactions et GET /api/portfolio/history (EF-02, RG-05, RG-06, SPEC §10.4, §11.3).

En bref :

**Enregistrer une opération** (fenêtre de confirmation). Avant d'écrire, on vérifie que
le conseil a moins de 5 minutes et que le cours n'a pas changé depuis la simulation.
Puis UNE SEULE requête appelle la fonction SQL ``executer_transaction`` : elle revérifie
le cash (ou les actions détenues), enregistre l'opération et met à jour le cash d'un
seul bloc. Si quoi que ce soit échoue : code 400 et rien n'est écrit.

**Historique** : journal paginé des opérations (avec le conseil donné à ce moment et le
gain réalisé sur chaque vente), courbe de la valeur du portefeuille jour par jour et
bilan, sur une période d'une semaine à un an.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

import config
from db.repository import TransactionRefused
from models.schemas import TransactionRequest
from routers.deps import check_ticker, get_now, get_repo, money
from services.decision_engine import ACHAT, alert_level, realized_gains, verdict, weekly_variation_pct
from services.portfolio_service import MENTION, load_state
from services.ratio_scoring import estimated_dividend

router = APIRouter(prefix="/api", tags=["opérations"])

REFUSALS = {
    "RG05_CASH_INSUFFISANT": "Cash insuffisant pour cette opération : rien n'a été enregistré.",
    "VENTE_SUPERIEURE_A_LA_POSITION": "Vous ne détenez pas assez d'actions pour cette vente : rien n'a été enregistré.",
    "QUANTITE_INVALIDE": "Nombre d'actions invalide : rien n'a été enregistré.",
}


@router.post("/transactions")
def record_transaction(
    request: TransactionRequest, repo=Depends(get_repo), now: datetime = Depends(get_now)
) -> dict[str, Any]:
    state = load_state(repo)
    action = check_ticker(request.ticker, state.actions)

    age = now - request.date_conseil
    if age > timedelta(minutes=config.CONSEIL_VALIDITE_MINUTES) or age < timedelta(minutes=-1):
        raise HTTPException(400, "Le conseil a plus de 5 minutes : relancez la simulation.")
    if state.prices[request.ticker] != request.cours_simule.quantize(Decimal("0.01")):
        raise HTTPException(400, "Le cours a changé depuis la simulation : relancez la simulation.")

    score = state.scores.get(request.ticker) or {}
    details = score.get("details_piliers", {})
    conseil_algo = {
        "conseil": score.get("decision"),
        "verdict": verdict(request.operation, score.get("decision", "RIEN"), state.niveau_alerte),
        "note": details.get("note"),
        "raisons": details.get("raisons", []),
        "seed": details.get("hasard", {}).get("seed"),
        "score_id": score.get("id"),
        "date_conseil": request.date_conseil.isoformat(),
        "cours_simule": str(request.cours_simule),
        "niveau_alerte": state.niveau_alerte,
    }
    try:
        tx = repo.execute_transaction(
            state.portfolio["id"], action["id"], request.operation, request.quantite, conseil_algo
        )
    except TransactionRefused as refused:
        message = next((m for code, m in REFUSALS.items() if code in refused.code), None)
        raise HTTPException(400, message or "Opération refusée : rien n'a été enregistré.") from refused

    after = load_state(repo)
    label = "Achat" if request.operation == ACHAT else "Vente"
    return {
        "message": f"{label} enregistré : {request.quantite} actions {action['nom']}.",
        "transaction": tx,
        "cash_disponible": money(after.cash),
        "capital_total": money(after.value),
        "variation_hebdo_pct": round(after.variation_pct, 2),
        "niveau_alerte": after.niveau_alerte,
    }


# ---------------------------------------------------------------------------
# Historique (RG-06)
# ---------------------------------------------------------------------------

PERIODS = {"1s": 7, "1m": 31, "3m": 92, "1a": 365}


def value_curve(state, histories: dict[str, pd.DataFrame], start: date, end: date) -> list[dict[str, Any]]:
    """Valeur du portefeuille chaque jour de bourse : cash du jour + actions détenues ×
    clôture du jour. Le cash d'un jour passé = cash actuel − effet des opérations postérieures."""
    days = sorted({d for h in histories.values() for d in h["date_seance"] if start <= d <= end})
    if not days:
        return []
    closes = {
        t: h.set_index("date_seance")["close"].astype(float).reindex(days).ffill() for t, h in histories.items()
    }
    curve = []
    for day in days:
        cash = state.cash
        held: dict[str, int] = {}
        for tx in state.transactions:
            sign = 1 if tx["type_op"] == ACHAT else -1
            if tx["date_execution"].date() > day:
                cash += sign * tx["montant_total"]
            else:
                held[tx["ticker"]] = held.get(tx["ticker"], 0) + sign * tx["quantite_entiere"]
        value = Decimal(str(cash))
        for ticker, quantity in held.items():
            close = closes.get(ticker, pd.Series(dtype=float)).get(day)
            if quantity > 0 and close is not None and not math.isnan(close):
                value += Decimal(quantity) * Decimal(str(close))
        curve.append({"date": day.isoformat(), "valeur": money(value)})
    return curve


@router.get("/portfolio/history")
def history(
    periode: Literal["1s", "1m", "3m", "1a"] = "1m",
    ticker: str | None = None,
    page: int = Query(1, ge=1),
    taille: int = Query(10, ge=1, le=50),
    repo=Depends(get_repo),
    now: datetime = Depends(get_now),
) -> dict[str, Any]:
    state = load_state(repo)
    if ticker:
        ticker = check_ticker(ticker, state.actions)["ticker"]
    end = now.date()
    start = end - timedelta(days=PERIODS[periode])

    gains = realized_gains(state.transactions)
    in_period = [tx for tx in state.transactions if start <= tx["date_execution"].date() <= end]
    journal = [tx for tx in in_period if ticker is None or tx["ticker"] == ticker]
    journal.sort(key=lambda tx: tx["date_execution"], reverse=True)
    total = len(journal)
    pages = max(1, math.ceil(total / taille))
    rows = [
        {
            "id": tx["id"],
            "date": tx["date_execution"].isoformat(),
            "ticker": tx["ticker"],
            "nom": tx["nom"],
            "operation": tx["type_op"],
            "quantite": tx["quantite_entiere"],
            "prix": money(tx["prix_unitaire"]),
            "montant": money(tx["montant_total"]),
            "conseil_donne": (tx.get("conseil_algo") or {}).get("conseil"),
            "plus_ou_moins_value": money(gains.get(tx["id"])),
        }
        for tx in journal[(page - 1) * taille: page * taille]
    ]

    tickers_seen = {tx["ticker"] for tx in state.transactions}
    histories = {
        t: repo.get_history(state.actions[t]["id"], since=start - timedelta(days=7)) for t in tickers_seen
    }
    if not histories:  # aucune opération : la courbe suit les jours de bourse d'une action
        first = config.TICKERS[0]
        histories = {first: repo.get_history(state.actions[first]["id"], since=start)}
    curve = value_curve(state, histories, start, end)

    sales = [tx for tx in in_period if tx["type_op"] != ACHAT]
    realized = sum((gains.get(tx["id"], Decimal(0)) for tx in sales), Decimal(0))
    dividends = {
        t: estimated_dividend(q, state.actions[t].get("dividende_estime")) for t, q in state.held.items()
    }
    return {
        "periode": {"code": periode, "debut": start.isoformat(), "fin": end.isoformat()},
        "bilan": {
            "valeur": money(state.value),
            "variation_depuis_depart_pct": round(
                weekly_variation_pct(state.value, state.portfolio["capital_initial"]), 2
            ),
            "plus_values_realisees": money(realized),
            "ventes": [{"ticker": tx["ticker"], "nom": tx["nom"]} for tx in sales],
            "dividendes_estimes_an": money(sum(dividends.values(), Decimal(0))),
            "dividendes_par_titre": {t: money(v) for t, v in dividends.items()},
            "nb_operations": len(in_period),
            "nb_achats": len(in_period) - len(sales),
            "nb_ventes": len(sales),
        },
        "courbe": curve,
        "capital_initial": money(state.portfolio["capital_initial"]),
        "marqueurs": [
            {"date": tx["date_execution"].date().isoformat(), "ticker": tx["ticker"], "operation": tx["type_op"]}
            for tx in in_period
        ],
        "transactions": rows,
        "pagination": {"page": page, "taille": taille, "total": total, "pages": pages},
        "niveau_alerte": alert_level(state.variation_pct),
        "mention": MENTION,
    }

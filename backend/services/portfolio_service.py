"""État du portefeuille, lu en une seule fois pour toutes les routes — SPEC §11.1.

En bref : ``load_state`` fait 4 lectures (actions, derniers conseils, portefeuille,
opérations) et en déduit tout ce dont les écrans ont besoin : actions détenues,
valeur du portefeuille, performance de la semaine et niveau d'alerte (RG-01). Rien
n'est recalculé lourdement ici : les notes viennent de ``scores_actions`` (ENF-02).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any

import config
from services.decision_engine import (
    APPROCHE,
    ATTEINT,
    CENT,
    alert_level,
    fmt_eur,
    fmt_pct,
    portfolio_value,
    positions,
    rederive_advice,
    weekly_variation_pct,
)

MENTION = "Les conseils sont une aide à la décision, ils ne garantissent pas le succès : vous restez seul décideur."  # ENF-03, D-25


@dataclass
class PortfolioState:
    portfolio: dict[str, Any]
    actions: dict[str, dict[str, Any]]  # par ticker
    scores: dict[str, dict[str, Any]]  # dernier conseil, par ticker
    transactions: list[dict[str, Any]]
    held: dict[str, int]
    prices: dict[str, Decimal]
    value: Decimal
    variation_pct: float
    niveau_alerte: str
    date_donnees: str | None
    profil: str | None = None
    seuils: tuple[float, float] = (60.0, 40.0)

    @property
    def cash(self) -> Decimal:
        return self.portfolio["cash_disponible"]


def load_state(repo) -> PortfolioState:
    # Les lectures indépendantes partent en même temps (ENF-02).
    with ThreadPoolExecutor(max_workers=3) as pool:
        actions_job = pool.submit(repo.get_actions)
        scores_job = pool.submit(repo.latest_scores)
        portfolio = repo.get_portfolio()
        transactions = repo.get_transactions(portfolio["id"])
        actions = {a["ticker"]: a for a in actions_job.result()}
        latest = scores_job.result()
    by_id = {a["id"]: a["ticker"] for a in actions.values()}
    # Conseil relu avec les seuils du profil du client (D-17) : un changement s'applique tout de suite.
    profile = portfolio.get("profil_risque")
    seuils = config.thresholds_for(profile)
    scores = {by_id[aid]: rederive_advice(s, seuils) for aid, s in latest.items() if aid in by_id}
    held = positions(transactions)
    prices = {t: Decimal(str(a["dernier_cours"])) for t, a in actions.items()}
    value = portfolio_value(portfolio["cash_disponible"], held, prices)
    variation = weekly_variation_pct(value, portfolio["val_semaine_prec"])
    stamps = [str(a.get("maj_le")) for a in actions.values() if a.get("maj_le")]
    return PortfolioState(
        portfolio=portfolio,
        actions=actions,
        scores=scores,
        transactions=transactions,
        held=held,
        prices=prices,
        value=value,
        variation_pct=variation,
        niveau_alerte=alert_level(variation),
        date_donnees=max(stamps) if stamps else None,
        profil=profile if profile in config.PROFILS_RISQUE else None,
        seuils=seuils,
    )


def with_alert(raisons: list[str], niveau: str, variation_pct: float) -> list[str]:
    """Si l'alerte de perte est active, sa phrase passe en premier (SPEC §8.1, 4 phrases au plus)."""
    if niveau == ATTEINT:
        head = (
            f"Limite de perte atteinte : {fmt_pct(variation_pct)} cette semaine. "
            "La vente est conseillée sur les positions en baisse."
        )
    elif niveau == APPROCHE:
        head = f"Perte de la semaine proche de la limite ({fmt_pct(variation_pct)}) : aucun achat n'est conseillé."
    else:
        return list(raisons)
    return [head] + [r for r in raisons if not r.startswith(("Limite de perte", "Perte de la semaine"))][:3]


def week_bounds(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=4)


def exposure_check(state: PortfolioState, ticker: str, montant_achat: Decimal) -> dict[str, Any]:
    """Part du capital total sur ``ticker`` avant et après un achat de ``montant_achat`` (D-26).

    Prudent / Équilibré : ``depasse`` = True si la position dépasserait la limite du profil
    (message clair avec le montant encore possible). Dynamique : jamais bloqué, avertissement
    au-delà de EXPOSITION_AVERTISSEMENT_PCT. Sans profil choisi : pas de limite."""
    total = Decimal(str(state.value))
    price = Decimal(str(state.prices[ticker]))
    held_value = Decimal(state.held.get(ticker, 0)) * price
    montant = Decimal(str(montant_achat))
    if total <= 0:
        return {"actuelle_pct": 0.0, "apres_pct": 0.0, "max_pct": None, "montant_max_eur": None,
                "depasse": False, "message": None, "avertissement": None}
    before = float(held_value / total * 100)
    after = float((held_value + montant) / total * 100)
    limit = config.exposure_limit_for(state.profil)
    name = state.actions[ticker]["nom"]
    result = {"actuelle_pct": round(before, 1), "apres_pct": round(after, 1), "max_pct": limit,
              "montant_max_eur": None, "depasse": False, "message": None, "avertissement": None}
    if limit is not None:
        room = max(Decimal(0), (total * Decimal(str(limit)) / 100 - held_value)).quantize(CENT, rounding=ROUND_DOWN)
        result["montant_max_eur"] = str(room)
        if after > limit + 1e-9:
            nom_profil = config.PROFILS_RISQUE[state.profil]["nom"]
            deja = f"Vous détenez déjà {fmt_eur(held_value)} de {name} : " if held_value > 0 else ""
            result["depasse"] = True
            result["message"] = (
                f"Votre profil {nom_profil} limite chaque action à {limit:.0f} % de votre capital "
                f"({fmt_eur(total * Decimal(str(limit)) / 100)}). {deja}vous pouvez encore en acheter pour "
                f"{fmt_eur(room)} au plus."
            )
    elif after > config.EXPOSITION_AVERTISSEMENT_PCT:
        result["avertissement"] = (
            f"Après cet achat, {name} représentera {fmt_pct(after, False)} de votre capital : "
            "miser beaucoup sur une seule action augmente le risque."
        )
    return result

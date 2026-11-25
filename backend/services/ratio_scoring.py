"""Pilier 3 — Ratios financiers (RatioScoringService) — SPEC §5.

En bref : trois questions sur la « santé de fond » de l'entreprise, à partir des deux
derniers exercices (table ``ratios_financiers``) :

- Chiffre d'affaires : progresse-t-il ? +10 % → +1, +5 % → 0, baisse → −1 (entre les
  deux, le signal varie en ligne droite) ;
- Dividende par action : augmente-t-il ? hausse de plus de 1 % → +1, stable → 0,
  baisse → −1 ;
- Rendement : le dividende est-il généreux par rapport au prix de l'action, comparé à
  la moyenne des 5 titres ? 50 % au-dessus → +1, égal → 0, 50 % en dessous → −1.

Note = 50 + 50 × moyenne des signaux pondérée par 7 / 6 / 6.
Le dividende estimé = nombre d'actions × dividende par action attendu (§5.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import config
from services.common import clip, is_missing, note_from_signal, weighted_mean


def growth_pct(current: float | None, previous: float | None) -> float | None:
    if is_missing(current) or is_missing(previous) or not previous:
        return None
    return (current / previous - 1) * 100


def ca_signal(growth: float | None) -> float | None:
    if is_missing(growth):
        return None
    neutral = config.RATIO_CA_CROISSANCE_NEUTRE_PCT
    span = config.RATIO_CA_CROISSANCE_MAX_PCT - neutral
    return clip((growth - neutral) / span)


def dpa_signal(growth: float | None) -> float | None:
    if is_missing(growth):
        return None
    if growth > config.RATIO_DPA_HAUSSE_PCT:
        return 1.0
    if growth < -config.RATIO_DPA_HAUSSE_PCT:
        return -1.0
    return 0.0


def yield_signal(rendement: float | None, moyenne: float | None) -> float | None:
    if is_missing(rendement) or is_missing(moyenne) or not moyenne:
        return None
    return clip((rendement / moyenne - 1) / config.RATIO_RENDEMENT_ECART_MAX)


def estimated_dividend(quantity: int, dividend_per_share: Decimal | float | None) -> Decimal:
    """dividende estimé (€) = nombre d'actions × dividende par action, au centime."""
    if dividend_per_share is None:
        return Decimal("0.00")
    amount = Decimal(quantity) * Decimal(str(dividend_per_share))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class RatioResult:
    score: float
    criteres: dict[str, float | None]
    croissance_ca_pct: float | None
    croissance_dpa_pct: float | None
    rendement_pct: float | None
    moyenne_rendement_pct: float | None


class RatioScoringService:
    def score(
        self,
        ca: float | None,
        ca_precedent: float | None,
        dpa: float | None,
        dpa_precedent: float | None,
        rendement: float | None,
        moyenne_rendement: float | None,
    ) -> RatioResult:
        g_ca = growth_pct(ca, ca_precedent)
        g_dpa = growth_pct(dpa, dpa_precedent)
        criteres = {
            "ca": ca_signal(g_ca),
            "dpa": dpa_signal(g_dpa),
            "rendement": yield_signal(rendement, moyenne_rendement),
        }
        mean = weighted_mean(criteres, config.IMPORTANCES_RATIOS)
        score = config.NOTE_NEUTRE if mean is None else note_from_signal(mean)
        return RatioResult(score, criteres, g_ca, g_dpa, rendement, moyenne_rendement)

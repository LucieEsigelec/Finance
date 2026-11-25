"""Petites fonctions de calcul partagées par les 4 piliers.

En bref :
- ``clip`` borne un signal entre −1 et +1 ;
- ``note_from_signal`` applique la formule unique de la SPEC §1.2 : note = 50 + 50 × signal ;
- ``weighted_mean`` fait une moyenne pondérée en ignorant les valeurs absentes
  (un indicateur qu'on ne peut pas calculer est simplement laissé de côté, SPEC §3.4) ;
- ``round_half_up`` arrondit « comme à l'école » (59,85 → 59,9), pas comme Python
  (qui arrondit parfois au pair).
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping

import config


def clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def is_missing(value: float | None) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def note_from_signal(signal: float) -> float:
    """Signal entre −1 et +1 → note sur 100 (50 = neutre)."""
    return config.NOTE_NEUTRE + config.NOTE_ECHELLE * clip(signal)


def weighted_mean(values: Mapping[str, float | None], weights: Mapping[str, float]) -> float | None:
    """Moyenne pondérée des valeurs présentes ; None si aucune valeur n'est disponible."""
    total = 0.0
    weight_sum = 0.0
    for name, weight in weights.items():
        value = values.get(name)
        if is_missing(value):
            continue
        total += weight * value
        weight_sum += weight
    if weight_sum == 0:
        return None
    return total / weight_sum


def round_half_up(value: float, digits: int = 1) -> float:
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(repr(float(value))).quantize(quantum, rounding=ROUND_HALF_UP))

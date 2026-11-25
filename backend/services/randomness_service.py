"""Pilier 4 — Hasard contrôlé (RandomnessService) — SPEC §6.

En bref : un nombre entre 0 et 100 tiré « au hasard », mais **le même toute la
semaine** pour un titre donné : la graine du tirage vient du titre et de la semaine
(SHA-256 de « DSY.PA2026-W48 »). On peut donc rejouer et vérifier n'importe quel
conseil (la graine est enregistrée avec lui).

Le hasard pèse 10 % : il ne déplace la note finale que de 5 points au plus, alors qu'il
faut s'éloigner de 10 points du neutre pour conseiller un achat ou une vente.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date


def iso_week_label(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def weekly_seed(ticker: str, day: date) -> int:
    """Graine sur 63 bits (entier positif, rangé tel quel dans le JSON du conseil)."""
    digest = hashlib.sha256(f"{ticker}{iso_week_label(day)}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") >> 1


@dataclass(frozen=True)
class RandomResult:
    score: float
    seed: int
    semaine: str


class RandomnessService:
    def score(self, ticker: str, day: date) -> RandomResult:
        seed = weekly_seed(ticker, day)
        return RandomResult(100 * random.Random(seed).random(), seed, iso_week_label(day))

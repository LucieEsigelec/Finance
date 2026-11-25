"""Pilier 1 — Informations (InfoScoringService) — SPEC §4. Pilier majoritaire (40 %, RG-04).

En bref :
1. chaque article reçoit une **note d'impact** sur 100 à la collecte :
   note = 50 + 50 × sentiment × importance (1 pour une annonce officielle, 0,5 sinon) ;
2. un article **perd la moitié de son poids tous les 2 jours** ; au-delà de 7 jours,
   ou s'il est daté après la date de calcul, il est ignoré ;
3. la note du pilier est la moyenne des notes d'impact, pondérée par ces poids ;
4. les 3 articles qui pèsent le plus deviennent les « faits marquants » (raisons et onglet Infos).

Sans article récent : note 50 (neutre) et message « aucune actualité récente » (V5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

import config
from services.common import clip

NO_RECENT_NEWS = "aucune actualité récente"


def impact_score(sentiment: float, announcement: bool) -> float:
    importance = config.INFO_IMPORTANCE_ANNONCE if announcement else config.INFO_IMPORTANCE_ORDINAIRE
    return 50 + 50 * clip(sentiment) * importance


def article_weight(age_days: float) -> float:
    """Poids = 0,5 ^ (âge / 2 jours) ; 0 au-delà de 7 jours ou dans le futur."""
    if age_days < 0 or age_days > config.INFO_FENETRE_JOURS:
        return 0.0
    return 0.5 ** (age_days / config.INFO_DEMI_VIE_JOURS)


def info_impact_points(note: float) -> float:
    """Points ajoutés (ou retirés) à la note finale par les actualités : 0,40 × (note − 50)."""
    return config.POIDS["infos"] * (note - config.NOTE_NEUTRE)


@dataclass
class InfoResult:
    score: float
    faits_cles: list[dict[str, Any]] = field(default_factory=list)
    nb_articles: int = 0
    message: str | None = None

    @property
    def impact_points(self) -> float:
        return info_impact_points(self.score)


class InfoScoringService:
    """Agrège les actualités récentes d'un titre (table ``actualites``)."""

    def score(self, articles: Iterable[dict[str, Any]], date_calcul: datetime) -> InfoResult:
        weighted: list[tuple[float, dict[str, Any]]] = []
        for article in articles:
            published = article["date_pub"]
            age_days = (date_calcul - published).total_seconds() / 86400
            weight = article_weight(age_days)
            if weight > 0 and article.get("score_impact") is not None:
                weighted.append((weight, article))

        if not weighted:
            return InfoResult(config.NOTE_NEUTRE, [], 0, NO_RECENT_NEWS)

        total_weight = sum(w for w, _ in weighted)
        note = sum(w * float(a["score_impact"]) for w, a in weighted) / total_weight
        weighted.sort(key=lambda item: item[0], reverse=True)
        faits = [
            {
                "titre": a["titre"],
                "score_impact": float(a["score_impact"]),
                "date_pub": a["date_pub"].isoformat(),
                "poids": round(w, 3),
            }
            for w, a in weighted[: config.INFO_NB_FAITS_CLES]
        ]
        return InfoResult(note, faits, len(weighted))

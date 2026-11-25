"""Dépendances partagées par les routes (injection FastAPI).

En bref : chaque route demande « le dépôt de données » ou « l'heure actuelle » à ces
fonctions au lieu de les créer elle-même. Les tests remplacent ces fonctions par une
fausse base et une heure fixe (``app.dependency_overrides``), sans toucher Supabase.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from decimal import Decimal
from typing import Any

from fastapi import HTTPException

import config
from db.cached_repository import CachedRepository
from db.repository import SupabaseRepository
from db.supabase_client import get_client
from services.refresh_service import MarketCollector


@lru_cache(maxsize=1)
def get_repo() -> CachedRepository:
    """Un seul dépôt pour toute l'API, avec sa mémoire courte (ENF-02)."""
    return CachedRepository(SupabaseRepository(get_client()))


def get_collector() -> MarketCollector:
    return MarketCollector()


def get_now() -> datetime:
    return datetime.now(timezone.utc)


def check_ticker(ticker: str, actions: dict[str, Any]) -> dict[str, Any]:
    """404 si le code n'est pas l'une des 5 actions du périmètre (SPEC A.4)."""
    ticker = ticker.strip().upper()
    if ticker not in config.TICKERS or ticker not in actions:
        raise HTTPException(status_code=404, detail=f"Action inconnue : {ticker}")
    return actions[ticker]


def money(value: Decimal | float | int | None) -> float | None:
    """Montant pour le JSON : nombre au centime (calculé en Decimal avant)."""
    return None if value is None else float(Decimal(str(value)).quantize(Decimal("0.01")))

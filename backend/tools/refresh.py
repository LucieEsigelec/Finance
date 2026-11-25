"""Actualise les données de marché et recalcule les conseils, sans passer par l'API.

En bref : fait exactement ce que fait POST /api/market/refresh (collecte yfinance,
Google News, NewsAPI, puis recalcul de scores_actions), et affiche le compte rendu.
ÉCRIT dans la base (cours, ratios, actualités, scores) : c'est son rôle.

Lancement depuis ``backend/`` : ``python -m tools.refresh``
"""

from __future__ import annotations

import json
import sys

from config import load_settings
from db.repository import SupabaseRepository
from db.supabase_client import get_client
from services.refresh_service import MarketCollector, refresh


def main() -> int:
    report = refresh(SupabaseRepository(get_client()), MarketCollector(), news_api_key=load_settings().news_api_key)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

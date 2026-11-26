"""Mémoire courte devant la base, pour répondre en moins de 2 secondes (ENF-02).

En bref : chaque lecture de Supabase coûte entre 0,3 et 1 seconde (aller-retour réseau).
Or les cours, les conseils, les ratios et les actualités ne changent qu'à
l'actualisation. On garde donc le résultat des lectures en mémoire :

- **10 minutes** pour les données de marché (actions, conseils, cours, ratios,
  actualités) ; tout est effacé dès qu'une actualisation passe par l'API ;
- **30 secondes** pour le portefeuille et les opérations ; effacés dès qu'une
  opération est enregistrée.

Les écritures passent toujours directement à la base. Seule limite : une
actualisation lancée hors de l'API (``python -m tools.refresh``) n'apparaît dans l'API
qu'au bout de 10 minutes au plus.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

MARKET_TTL = 600.0
PORTFOLIO_TTL = 30.0

MARKET_READS = {
    "get_actions", "latest_scores", "get_history", "last_history_date", "get_ratios", "get_articles", "get_intraday",
}
PORTFOLIO_READS = {"get_portfolio", "get_transactions"}
MARKET_WRITES = {
    "update_action", "upsert_history", "save_ratios", "insert_missing_articles", "insert_scores",
    "upsert_intraday", "purge_intraday",
}
PORTFOLIO_WRITES = {"execute_transaction", "update_portfolio_week"}


class CachedRepository:
    def __init__(self, repo, clock: Callable[[], float] = time.monotonic):
        self._repo = repo
        self._clock = clock
        self._lock = threading.Lock()
        self._store: dict[tuple, tuple[float, Any]] = {}

    def invalidate(self, group: str | None = None) -> None:
        with self._lock:
            if group is None:
                self._store.clear()
            else:
                self._store = {k: v for k, v in self._store.items() if k[0] != group}

    def __getattr__(self, name: str):
        target = getattr(self._repo, name)
        if name in MARKET_READS or name in PORTFOLIO_READS:
            group = "market" if name in MARKET_READS else "portfolio"
            ttl = MARKET_TTL if group == "market" else PORTFOLIO_TTL

            def cached(*args, **kwargs):
                key = (group, name, args, tuple(sorted(kwargs.items())))
                now = self._clock()
                with self._lock:
                    hit = self._store.get(key)
                    if hit and now - hit[0] < ttl:
                        return _copy(hit[1])
                value = target(*args, **kwargs)
                with self._lock:
                    self._store[key] = (now, value)
                return _copy(value)

            return cached
        if name in MARKET_WRITES or name in PORTFOLIO_WRITES:
            group = "market" if name in MARKET_WRITES else "portfolio"

            def write(*args, **kwargs):
                try:
                    return target(*args, **kwargs)
                finally:
                    self.invalidate(group)
                    if name == "update_portfolio_week":
                        self.invalidate("market")

            return write
        return target


def _copy(value: Any) -> Any:
    """Copie légère : les appelants peuvent modifier ce qu'ils reçoivent sans abîmer la mémoire."""
    if hasattr(value, "copy") and not isinstance(value, (str, bytes)):
        if isinstance(value, list):
            return [dict(v) if isinstance(v, dict) else v for v in value]
        if isinstance(value, dict):
            return {k: (dict(v) if isinstance(v, dict) else v) for k, v in value.items()}
        return value.copy()
    return value

"""Pilotage de l'actualisation : une seule à la fois, au plus toutes les 2 minutes (D-11, D-13).

En bref : ce module garde en mémoire l'état de l'actualisation (en cours, terminée, en
erreur) et sait la lancer en arrière-plan. Il est utilisé par :
- le bouton « Actualiser les données » (POST /api/market/refresh) ;
- le tableau de bord (GET /api/dashboard), qui la lance tout seul quand les données ont
  plus d'une heure : l'application reste à jour dès que quelqu'un la consulte, même si la
  tâche planifiée de GitHub est en retard (D-13).
"""

from __future__ import annotations

import math
import threading
import time
from datetime import datetime, timezone
from typing import Any

import config
from services.refresh_service import refresh

_lock = threading.Lock()
state: dict[str, Any] = {"en_cours": False, "lance_le": None, "termine_le": None, "rapport": None, "erreur": None}
last_refresh = {"at": 0.0}
last_newsapi = {"at": 0.0}


def news_key() -> str:
    """Clé NewsAPI seulement si le dernier appel date de plus de 15 minutes (quota gratuit)."""
    key = config.load_settings().news_api_key
    now = time.monotonic()
    if key and (not last_newsapi["at"] or now - last_newsapi["at"] >= config.NEWSAPI_INTERVALLE_MIN_SECONDES):
        last_newsapi["at"] = now
        return key
    return ""


def run(repo, collector, analyzer=None) -> None:
    """Fait l'actualisation complète et note son résultat (analyzer : modèle de langue, D-16)."""
    try:
        state["rapport"] = refresh(repo, collector, news_api_key=news_key(), analyzer=analyzer)
        state["erreur"] = None
    except Exception as error:  # l'erreur est montrée à l'interface, la clé n'y figure jamais
        state["erreur"] = f"{type(error).__name__}: {error}"
    finally:
        if hasattr(repo, "invalidate"):
            repo.invalidate()  # les écrans relisent les nouvelles données
        state["en_cours"] = False
        state["termine_le"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


def reserve() -> tuple[str, int]:
    """Réserve le droit de lancer une actualisation.
    Renvoie ("ok", 0), ("en_cours", 0) ou ("trop_tot", secondes à attendre)."""
    with _lock:
        if state["en_cours"]:
            return "en_cours", 0
        wait = config.REFRESH_INTERVALLE_MIN_SECONDES - (time.monotonic() - last_refresh["at"])
        if last_refresh["at"] and wait > 0:
            return "trop_tot", math.ceil(wait)
        last_refresh["at"] = time.monotonic()
        state.update(en_cours=True, lance_le=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     termine_le=None, erreur=None)
        return "ok", 0


def is_stale(date_donnees: str | None, now: datetime) -> bool:
    """Les données ont-elles plus d'une heure (ou n'existent-elles pas) ?"""
    if not date_donnees:
        return True
    updated = datetime.fromisoformat(str(date_donnees).replace("Z", "+00:00"))
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (now - updated).total_seconds() > config.DONNEES_AGE_MAX_SECONDES


def reset() -> None:
    """Remise à zéro (tests)."""
    last_refresh["at"] = 0.0
    last_newsapi["at"] = 0.0
    state.update(en_cours=False, lance_le=None, termine_le=None, rapport=None, erreur=None)

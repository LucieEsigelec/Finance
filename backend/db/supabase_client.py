"""Connexion à la base Supabase.

En bref : ``get_client()`` crée la connexion la première fois qu'on en a besoin,
puis réutilise toujours la même. Seul le backend se connecte à la base, avec la clé
secrète ``SUPABASE_KEY`` lue dans ``backend/.env`` (CLAUDE.md §6.2) ; cette clé n'est
jamais affichée, ni dans un message d'erreur, ni dans un log.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from config import ConfigError, load_settings


@lru_cache(maxsize=1)
def get_client() -> Client:
    settings = load_settings()
    missing = [
        name
        for name, value in (("SUPABASE_URL", settings.supabase_url), ("SUPABASE_KEY", settings.supabase_key))
        if not value
    ]
    if missing:
        raise ConfigError(
            f"Variable(s) manquante(s) dans backend/.env : {', '.join(missing)} "
            "(voir backend/.env.example)"
        )
    return create_client(settings.supabase_url, settings.supabase_key)

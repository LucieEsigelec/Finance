"""Connexion à la base Supabase.

En bref : ``get_client()`` crée la connexion la première fois qu'on en a besoin,
puis réutilise toujours la même. Seul le backend se connecte à la base, avec la clé
secrète ``SUPABASE_KEY`` lue dans ``backend/.env`` (CLAUDE.md §6.2) ; cette clé n'est
jamais affichée, ni dans un message d'erreur, ni dans un log.

On peut aussi écrire ``from db.supabase_client import supabase`` (forme du commit de
Lucie) : la connexion est alors créée à ce moment-là. Elle n'est jamais créée au simple
chargement du module, pour que les tests tournent sans fichier ``.env`` (GitHub Actions).
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


def __getattr__(name: str):
    """``supabase`` = la connexion partagée, créée au premier accès."""
    if name == "supabase":
        return get_client()
    raise AttributeError(name)
